"""Figures for the setup & usage page (booth): install flow, run structure, booth map."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle, Circle

for name in ("NanumGothic", "Noto Sans CJK KR", "NanumBarunGothic"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False
OUT = Path("docs/camp")
INK = "#2b2b2b"


def rbox(ax, x0, y0, w, h, title, lines=(), fc="#EEF3FA", ec=INK, tfs=11.5, fs=9.2, lw=1.2, title_dy=0.22):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=0.12", fc=fc, ec=ec, lw=lw, zorder=2))
    ax.text(x0 + w / 2, y0 + h - title_dy, title, ha="center", va="top", fontsize=tfs, fontweight="bold", color=INK, zorder=3)
    for i, t in enumerate(lines):
        ax.text(x0 + 0.18, y0 + h - title_dy - 0.42 - 0.3 * i, t, ha="left", va="top", fontsize=fs, color="#333333", zorder=3)


def arrow(ax, p, q, color=INK, lw=1.6, style="-|>"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=15, lw=lw, color=color, zorder=4, shrinkA=0, shrinkB=0))


# ---------------------------------------------------------------- 1. install flow
def install_flow():
    fig, ax = plt.subplots(figsize=(14, 4.2), dpi=150)
    ax.set_xlim(0, 14); ax.set_ylim(0, 4.2); ax.axis("off")
    steps = [
        ("1  ROS 2 Jazzy", ["ros-jazzy-desktop", "(공식 안내 · 직접)", "sudo apt install git", "  fonts-nanum"], "#E3EEFF"),
        ("2  저장소 받기", ["git clone <GitHub 저장소>", "cd pinklab_robotworld2026"], "#FFF3D6"),
        ("3  install.sh", ["apt 추가 패키지 · rosdep", "venv · pip · 충돌 검사", ".env · colcon build", "→ doctor 로 점검"], "#E6F7E6"),
        ("4  .env", ["OPENAI_API_KEY=…", "LLM 모듈 · FMS 의", "LLM 지령에만 필요"], "#FFE0E0"),
        ("5  확인", ["doctor 실패 0건", "start → MuJoCo + RViz", "fms → 웹 FMS", "pick pink drinks consult_2"], "#EDE7F6"),
    ]
    w, gap, x = 2.45, 0.35, 0.3
    for i, (title, lines, fc) in enumerate(steps):
        rbox(ax, x, 0.8, w, 2.7, title, lines, fc=fc, tfs=12, fs=9.4)
        if i < len(steps) - 1:
            arrow(ax, (x + w, 2.15), (x + w + gap, 2.15))
        x += w + gap
    ax.text(0.3, 4.0, "설치 흐름 (처음 한 번, 10~20분)", fontsize=12, fontweight="bold", color=INK, va="top")
    ax.text(0.3, 0.45, "새 터미널에서 source 불필요: ./scripts/robotworld 이 ROS 2 Jazzy 와 venv 를 스스로 켠다", fontsize=10, color="#444444", va="top")
    fig.savefig(OUT / "setup_flow.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- 2. run structure
def run_structure():
    fig, ax = plt.subplots(figsize=(14, 6.4), dpi=150)
    ax.set_xlim(0, 14); ax.set_ylim(0, 6.4); ax.axis("off")
    # terminal 1
    ax.add_patch(Rectangle((0.3, 0.4), 8.2, 5.6, fc="#F7F8FA", ec="#B0B7C3", lw=1.2, zorder=1))
    ax.text(0.55, 5.75, "터미널 1   ./scripts/robotworld start", fontsize=12.5, fontweight="bold", color=INK, va="top")
    ax.text(0.55, 5.35, "launch 하나가 아래 프로세스를 모두 띄운다  (한 번에 하나만)", fontsize=9.5, color="#555555", va="top")
    rbox(ax, 0.55, 3.3, 3.7, 1.7, "MuJoCo 브리지 (Python)", ["MuJoCo 물리 + 부스 + 사람", "/clock /joint_states TF /odom /scan", "카메라 핸들러 (도킹 마커)"], fc="#EDE7F6")
    rbox(ax, 4.5, 3.3, 3.8, 1.7, "Nav2 + AMCL", ["map_server · amcl · planner", "controller · bt_navigator", "/navigate_to_pose"], fc="#E3EEFF")
    rbox(ax, 0.55, 1.2, 3.7, 1.7, "MoveIt 2 (move_group)", ["planning scene · IK", "/move_action · /compute_ik", "RViz (rviz:=false 로 끌 수 있음)"], fc="#E3EEFF")
    rbox(ax, 4.5, 1.2, 3.8, 1.7, "PickPlace 스킬 + Task Manager", ["/pick_place 액션: 도킹 → 파지 → 놓기", "/execute_plan: 단계 목록 실행", "phase = all | pick | place"], fc="#E6F7E6")
    ax.text(0.55, 0.85, "준비 완료 신호:  Managed nodes are active  ·  You can start planning now!  ·  PickPlace server ready",
            fontsize=9, color="#2e7d32", va="top")
    # terminal 2
    ax.add_patch(Rectangle((9.0, 0.4), 4.7, 5.6, fc="#FFFBF0", ec="#D9C48A", lw=1.2, zorder=1))
    ax.text(9.25, 5.75, "터미널 2   명령 · 예제", fontsize=12.5, fontweight="bold", color=INK, va="top")
    ax.text(9.25, 5.35, "./scripts/robotworld <명령>", fontsize=9.5, color="#555555", va="top")
    rows = [("fms", "웹 FMS :8080"), ("goal 7.4 -3.8 -1.15", "Nav2 목표 (인포)"), ("arm both ready", "MoveIt 이름 자세"),
            ("pick pink drinks consult_2", "컵 배달 (약 4분)"), ("pick pink --phase pick", "집기까지만"), ("exec ros2 topic list", "ROS 2 CLI"),
            ("exec python lessons/…", "모듈 실습"), ("stop", "스택 전체 종료")]
    for i, (cmd, what) in enumerate(rows):
        y = 4.75 - i * 0.5
        ax.add_patch(FancyBboxPatch((9.25, y - 0.18), 4.2, 0.4, boxstyle="round,pad=0,rounding_size=0.06", fc="white", ec="#D9C48A", lw=0.8, zorder=2))
        ax.text(9.35, y + 0.02, cmd, fontsize=8.6, family="monospace", color=INK, va="center", zorder=3)
        ax.text(13.35, y + 0.02, what, fontsize=8.2, color="#666666", va="center", ha="right", zorder=3)
    arrow(ax, (9.0, 3.1), (8.5, 3.1), color="#7a4b00", style="<|-|>")
    ax.text(8.75, 3.22, "ROS 2", fontsize=8, color="#7a4b00", ha="center", va="bottom")
    ax.text(9.25, 0.95, "통신은 이 PC 안 (localhost, ROS_DOMAIN_ID 44)", fontsize=8.2, color="#7a4b00", va="top")
    ax.text(9.25, 0.68, "강좌 저장소(43)와 같이 켜도 섞이지 않음", fontsize=8.2, color="#7a4b00", va="top")
    fig.savefig(OUT / "run_structure.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- 3. booth map
def booth_map():
    import math
    import numpy as np
    from PIL import Image
    maps = Path("src/mobile_openarm_navigation/maps")
    meta = yaml.safe_load((maps / "booth.yaml").read_text())
    img = np.array(Image.open(maps / meta["image"]).convert("L"))
    res, (ox, oy, _) = meta["resolution"], meta["origin"]
    extent = (ox, ox + img.shape[1] * res, oy, oy + img.shape[0] * res)
    w = yaml.safe_load(Path("src/mobile_openarm_mujoco/worlds/booth.yaml").read_text())
    loc = yaml.safe_load(Path("src/warehouse_lecture/worlds/locations.yaml").read_text())["locations"]
    fig, ax = plt.subplots(figsize=(13, 9.6), dpi=150)
    ax.set_aspect("equal")
    ax.imshow(img, cmap="gray", extent=extent, origin="upper", vmin=0, vmax=255, zorder=1, alpha=0.9)
    ax.set_xlim(-1.2, 10.2); ax.set_ylim(-7.4, 1.2)
    ax.set_xlabel("x [m]  (map / world)"); ax.set_ylabel("y [m]")
    ax.add_patch(Rectangle((0, -6), 9, 6, fc="none", ec="#D81B60", lw=1.6, ls="--", zorder=3))
    for o in w["objects"]:
        cx, cy, _ = o["center"]
        ax.add_patch(Circle((cx, cy), 0.07, fc=o["rgba"][:3], ec="black", lw=0.6, zorder=6))
    for m in w["markers"]:
        cx, cy, _ = m["center"]
        ax.add_patch(Rectangle((cx - 0.06, cy - 0.06), 0.12, 0.12, fc="white", ec="black", lw=1.0, zorder=6))
    for name, s in w["stations"].items():
        ex, ey = s["edge"]
        ax.plot(ex, ey, marker="s", ms=8, color="#2E7D32", mec="black", mew=0.5, linestyle="none", zorder=6)
    below = {"consult_1", "table_a", "home", "classroom_2"}
    for name, d in loc.items():
        x, y, yaw = d["base_goal"]
        ax.plot(x, y, marker=(3, 0, math.degrees(yaw) - 90), ms=13, color="#1565C0", zorder=7, linestyle="none")
        up = name not in below
        ax.text(x, y + (0.2 if up else -0.2), f"{name}\n{d['aliases'][0]}", fontsize=7.6, ha="center", va="bottom" if up else "top", color="#0D47A1", zorder=8,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    sx, sy, _ = w["spawn"]
    ax.plot(sx, sy, marker="*", ms=16, color="#00897B", mec="black", mew=0.5, linestyle="none", zorder=8)
    handles = [
        plt.Line2D([], [], color="#D81B60", ls="--", lw=1.6, label="부스 9 × 6 m (X 0~9, Y -6~0)"),
        plt.Line2D([], [], marker="^", color="#1565C0", ms=10, ls="none", label="이름 있는 장소 base_goal (방향 = 로봇이 보는 쪽)"),
        plt.Line2D([], [], marker="s", color="#2E7D32", mec="black", ms=8, ls="none", label="스테이션 가장자리 (음료대 · 상담 테이블 1 · 2)"),
        plt.Line2D([], [], marker="s", color="white", mec="black", ms=8, ls="none", label="ArUco 마커 id 0~5 (스테이션마다 2개)"),
        plt.Line2D([], [], marker="o", color="#DE6BA6", mec="black", ms=8, ls="none", label="컵 3개 (분홍 · 파랑 · 노랑, 음료대 위)"),
        plt.Line2D([], [], marker="*", color="#00897B", mec="black", ms=12, ls="none", label="spawn (기본 시작 = home)"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=3, fontsize=8, frameon=False)
    ax.set_title("부스 배치도 9 × 6 m  (Nav2 지도 booth.pgm · booth.yaml · locations.yaml)", fontsize=12, fontweight="bold")
    fig.savefig(OUT / "booth_map.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    install_flow(); run_structure(); booth_map()
