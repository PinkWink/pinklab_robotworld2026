"""Figures for the PC-spec section of the setup & usage page (booth). Output: docs/camp/setup_lowspec_*.png

setup_lowspec_profile.png      real offscreen renders of the viewer: high / low, with the FPS measured while rendering
setup_lowspec_config.png       real launch output: sim_config.yaml read by the wrapper, command line wins
setup_lowspec_config_file.png  `cat sim_config.yaml` of the repository file
(setup_lowspec_noviewer.png is a screen capture of `start viewer:=false`.)
Run: MUJOCO_GL=egl python docs/camp/draw_setup_lowspec_figures.py
"""
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mujoco  # noqa: E402

HERE = Path(__file__).parent
WS = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WS / "src/mobile_openarm_mujoco"))
from render_terminal import SANS, render  # noqa: E402
from mobile_openarm_mujoco.bridge import show_simple_meshes  # noqa: E402

XML = WS / "artifacts/mobile_generated/warehouse.xml"


def profile():
    m = mujoco.MjModel.from_xml_path(str(XML))
    d = mujoco.MjData(m)
    adr = int(m.joint("floating_base").qposadr[0])
    d.qpos[adr:adr + 2] = [5.3, -3.2]    # the bridge puts the robot at booth.yaml spawn (home); the saved model has it at the origin
    mujoco.mj_forward(m, d)
    r = mujoco.Renderer(m, 720, 1280)
    wide = mujoco.MjvCamera()   # the whole booth
    wide.lookat[:] = [4.5, -3.0, 0.5]
    wide.distance, wide.azimuth, wide.elevation = 11, 120, -45
    close = mujoco.MjvCamera()  # the robot up close (it starts at home, 5.3, -3.2)
    close.lookat[:] = [5.3, -3.2, 0.7]
    close.distance, close.azimuth, close.elevation = 2.6, 200, -20

    def shot(view, option):
        r.update_scene(d, view, option)
        r.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = 0     # both profiles draw the viewer without shadows
        return r.render().copy()

    def fps(option, seconds=4.0):
        n, t0 = 0, time.perf_counter()
        while time.perf_counter() - t0 < seconds:
            shot(wide, option); n += 1
        return n / (time.perf_counter() - t0)

    high = mujoco.MjvOption(); high.geomgroup[1] = 0
    rows = [[shot(v, high) for v in (wide, close)]]
    f_high = fps(high)
    show_simple_meshes(m)       # what --viewer-simple-meshes does in the bridge
    low = mujoco.MjvOption()
    rows.append([shot(v, low) for v in (wide, close)])
    f_low = fps(low)
    r.close()
    print(f"offscreen 1280x720: high {f_high:.0f} FPS, low {f_low:.0f} FPS")
    titles = [f"high (기본)  ·  로봇 실제 메시  ·  {f_high:.0f} FPS", f"low  ·  로봇 단순 형상  ·  {f_low:.0f} FPS"]
    fig, axes = plt.subplots(2, 2, figsize=(13, 7.6), dpi=150)
    for col, (pair, title) in enumerate(zip(rows, titles)):
        for row, img in enumerate(pair):
            axes[row, col].imshow(img)
            axes[row, col].axis("off")
        axes[0, col].set_title(title, fontsize=13, family=SANS, fontweight="bold")
    fig.text(0.5, 0.02, "이 글을 쓴 PC 에서 1280×720 오프스크린 렌더로 잰 값 · 부스는 두 단계에서 같고 로봇만 달라진다 · 카메라 영상은 두 단계 모두 실제 메시",
             ha="center", fontsize=10, family=SANS, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(HERE / "setup_lowspec_profile.png", facecolor="white")
    plt.close(fig)


def config():
    path = f"[sim_config] {WS}/sim_config.yaml".replace(str(Path.home()), "/home/pw")
    cams = "camera_names=base_camera,head_camera camera_size=320x240 camera_fps=2"
    render([("prompt", "sed -i 's/^profile: high/profile: low/' sim_config.yaml     # 편집기로 고쳐도 같음"),
            ("prompt", "./scripts/robotworld start"),
            ("out", path),
            ("out", "[sim_config] profile=low viewer=true rviz=true viewer_shadows=false viewer_meshes=simple camera_shadows=false"),
            ("out", "             " + cams + " rviz_fps=10"),
            ("out", ""),
            ("prompt", "./scripts/robotworld start profile:=high rviz:=false     # 명령줄 인자가 파일보다 우선"),
            ("out", path),
            ("out", "[sim_config] profile=high viewer=true rviz=false viewer_shadows=false viewer_meshes=visual camera_shadows=true"),
            ("out", "             " + cams + " rviz_fps=15")],
           HERE / "setup_lowspec_config.png", highlight=("[sim_config] profile",), width=16.0,
           title="pw@laptop: ~/pinklab_robotworld2026 — bash")


def config_file():
    text = (WS / "sim_config.yaml").read_text().splitlines()
    render([("prompt", "cat sim_config.yaml")] + [("out", line) for line in text],
           HERE / "setup_lowspec_config_file.png", highlight=("profile: high",), width=16.0,
           title="pw@laptop: ~/pinklab_robotworld2026 — bash")


if __name__ == "__main__":
    profile(); config(); config_file()
