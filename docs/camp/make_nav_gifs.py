"""Animated GIFs for the booth pages, built from data recorded during real runs (no simulator needed).

  python3 docs/camp/make_nav_gifs.py [name ...]        # run from the workspace root; no name = all
Sources (artifacts/dev): odom_square1.csv, slam_maps/wp*.npz
Outputs (docs/camp): lesson03_square.gif, lesson04_map_growth.gif
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

if any(f.name == "NanumGothic" for f in font_manager.fontManager.ttflist):
    plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False
OUT, DEV = Path("docs/camp"), Path("artifacts/dev")
BOLD = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
RED, BLUE, GREEN = "#C62828", "#1565C0", "#1B5E20"


def grab(fig):
    fig.canvas.draw()
    return Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy())


def write(frames, durations, name, colors=96):
    pal = frames[len(frames) // 2].quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    out = OUT / name
    q[0].save(out, save_all=True, append_images=q[1:], duration=durations, loop=0, optimize=False)
    print("saved", out, len(frames), "frames", f"{sum(durations) / 1000:.1f} s", f"{out.stat().st_size / 1e6:.1f} MB", frames[0].size)


def captioned(img, text, badge=None, bar=50, size=22):
    """Paste img on a dark canvas with a subtitle bar under it."""
    font = ImageFont.truetype(BOLD, size)
    canvas = Image.new("RGB", (img.width, img.height + bar), "#111111")
    canvas.paste(img, (0, 0))
    d = ImageDraw.Draw(canvas)
    if badge:
        d.rounded_rectangle((10, img.height + 10, 22 + d.textlength(badge, font=font), img.height + bar - 8), 7, fill="#FFD400")
        d.text((16, img.height + 13), badge, fill="#111111", font=font)
    d.text(((img.width - d.textlength(text, font=font)) / 2, img.height + 13), text, fill="white", font=font)
    return canvas


# ---------------------------------------------------------------- lesson 03: odom vs ground truth on a square
def square():
    a = np.genfromtxt(DEV / "odom_square1.csv", delimiter=",", names=True)
    t = a["t"] - a["t"][0]
    err = np.hypot(a["odom_x"] - a["true_x"], a["odom_y"] - a["true_y"]) * 100
    yaw = np.degrees(np.abs((a["odom_yaw"] - a["true_yaw"] + np.pi) % (2 * np.pi) - np.pi))
    frames = []
    idx = list(range(0, len(t), 30)) + [len(t) - 1]
    for i in idx:
        fig, (ax, bx) = plt.subplots(1, 2, figsize=(10, 4.6), dpi=100, gridspec_kw={"width_ratios": [1, 1.15]})
        ax.plot(a["true_x"][: i + 1], a["true_y"][: i + 1], color=BLUE, lw=2.4, label="/ground_truth (실제)")
        ax.plot(a["odom_x"][: i + 1], a["odom_y"][: i + 1], color=RED, lw=1.4, ls="--", label="/odom (바퀴로 계산)")
        ax.add_patch(Circle((a["true_x"][i], a["true_y"][i]), 0.05, fc=BLUE, ec="white", zorder=5))
        ax.set_xlim(-0.35, 1.35); ax.set_ylim(-0.35, 1.45); ax.set_aspect("equal"); ax.grid(alpha=0.3)
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.legend(loc="upper center", fontsize=8.5, ncol=1)
        ax.set_title(f"한 변 1 m 사각형 · t = {t[i]:4.1f} s", fontsize=11)
        bx.plot(t[: i + 1], err[: i + 1], color=RED, lw=1.8)
        bx.set_xlim(0, t[-1]); bx.set_ylim(0, max(err) * 1.25); bx.grid(alpha=0.3)
        bx.set_xlabel("시간 [s]"); bx.set_ylabel("위치 오차 [cm]")
        bx.set_title(f"/odom 과 /ground_truth 의 차이: {err[i]:.2f} cm · yaw {yaw[i]:.2f}°", fontsize=11)
        fig.tight_layout()
        frames.append(grab(fig)); plt.close(fig)
    dur = [120] * len(frames); dur[0], dur[-1] = 1200, 3000
    cap = ["두 경로가 거의 겹친다 · 오차는 회전할 때 올라간다"] * len(frames)
    cap[-1] = f"한 바퀴 뒤 위치 오차 {err[-1]:.1f} cm · yaw {yaw[-1]:.1f}° → 줄지 않고 쌓인다"
    write([captioned(f, c) for f, c in zip(frames, cap)], dur, "lesson03_square.gif", colors=64)


# ---------------------------------------------------------------- lesson 04: the map growing during the booth tour
def map_growth():
    from draw_lesson04_figures import SPAWN, booth_view, show_grid, tour_route
    route = tour_route()
    shots = [np.load(DEV / f"slam_maps/wp{i}.npz") for i in range(len(route))]
    t0, frames, caps = float(shots[0]["stamp"]), [], []
    for i, s in enumerate(shots):
        fig, ax = plt.subplots(figsize=(9.0, 6.6), dpi=100)
        show_grid(ax, s["data"], float(s["resolution"]), np.array(s["origin"]) + SPAWN); booth_view(ax)
        path = np.array(route[: i + 1])
        ax.plot(path[:, 0], path[:, 1], color="#1976D2", lw=2.2, alpha=0.85)
        x, y, yaw = s["pose"]; x, y = x + SPAWN[0], y + SPAWN[1]
        ax.add_patch(Circle((x, y), 0.2, fc=RED, ec="white", lw=1.2, zorder=5))
        ax.plot([x, x + 0.4 * np.cos(yaw)], [y, y + 0.4 * np.sin(yaw)], color="white", lw=2.0, zorder=6)
        known = int((s["data"] >= 0).sum()) * 0.0025
        ax.set_title(f"시뮬레이션 {float(s['stamp']) - t0:3.0f} s  ·  아는 칸 {known:3.0f} m²   (회색 = 모름 · 흰색 = 비어 있음 · 검정 = 막힘)", fontsize=11)
        fig.tight_layout()
        frames.append(grab(fig)); plt.close(fig)
        caps.append("출발: 제자리에서 라이다 한 바퀴로 보이는 만큼만" if i == 0 else f"웨이포인트 {i}/{len(shots) - 1}: 지나간 곳 주변이 채워진다")
    caps[-1] = "한 바퀴 뒤: 부스 안쪽이 모두 채워졌다"
    dur = [900] * len(frames); dur[0], dur[-1] = 1800, 3000
    write([captioned(f, c, badge=f"{i}/{len(frames) - 1}") for i, (f, c) in enumerate(zip(frames, caps))], dur, "lesson04_map_growth.gif", colors=32)


# ---------------------------------------------------------------- lesson 05: two goals on the global costmap
def goal_run():
    import pickle
    from draw_lesson05_figures import footprint, show_cost
    d = pickle.load(open(DEV / "nav_run.pkl", "rb"))
    tr, od, plans = np.array(d["truth"]), np.array(d["odom"]), d["plans"]
    ends = [p["xy"][-1] for p in plans]
    second = next(i for i in range(1, len(plans)) if np.hypot(*(ends[i] - ends[i - 1])) > 0.3)
    t_start, t_second = plans[0]["t"] - 1.5, plans[second]["t"]
    third = next((i for i in range(second + 1, len(plans)) if np.hypot(*(ends[i] - ends[i - 1])) > 0.3), None)
    if third is not None:                                         # the recording ran on into the AMCL experiment: keep two goals
        cut = plans[third]["t"] - 1.0
        tr, od, plans = tr[tr[:, 0] < cut], od[od[:, 0] < cut], plans[:third]
    moving = np.where(np.abs(od[:, 4]) + np.abs(od[:, 5]) > 0.01)[0]
    t_end = od[moving[-1], 0] + 2.0
    frames, caps = [], []
    for t in np.arange(t_start, t_end, 0.8):
        i = int(np.argmin(np.abs(tr[:, 0] - t))); j = int(np.argmin(np.abs(od[:, 0] - t)))
        fig, ax = plt.subplots(figsize=(7.4, 6.9), dpi=100)
        show_cost(ax, d["global_costmap"])
        for k, p in enumerate(plans):
            if p["t"] <= t:
                ax.plot(p["xy"][:, 0], p["xy"][:, 1], color=GREEN, lw=2.2, alpha=1.0 if (k >= second) == (t >= t_second) else 0.25)
        m = (tr[:, 0] >= t_start) & (tr[:, 0] <= t)
        ax.plot(tr[m, 1], tr[m, 2], color=BLUE, lw=2.0, ls="--")
        footprint(ax, tr[i, 1], tr[i, 2], tr[i, 3], fc="none", ec=RED, lw=2.0)
        ax.set_xlim(3.4, 9.2); ax.set_ylim(-6.1, -0.9)
        ax.set_title(f"t = {t - plans[0]['t']:5.1f} s   v = {od[j, 4]:5.2f} m/s   w = {od[j, 5]:5.2f} rad/s\n"
                     "초록 = /plan · 파랑 점선 = 실제로 간 길 · 빨강 = 로봇", fontsize=10.5)
        fig.tight_layout()
        frames.append(grab(fig)); plt.close(fig)
        v, w = od[j, 4], od[j, 5]
        turning = abs(v) < 0.03 and abs(w) > 0.1
        if t < plans[0]["t"]:
            caps.append("goal 7.43 -3.77 -1.15 를 보내기 직전")
        elif t < t_second:
            caps.append("제자리에서 방향을 맞춘다" if turning else "첫 목표: 인포 앞 (7.43, -3.77) · /plan 을 따라간다")
        else:
            caps.append("제자리에서 방향을 맞춘다" if turning else "둘째 목표: RViz 2D Goal Pose 로 준 home (5.3, -3.2)")
    dur = [130] * len(frames); dur[0], dur[-1] = 1200, 3000
    write([captioned(f, c) for f, c in zip(frames, caps)], dur, "lesson05_goal_run.gif", colors=64)


# ---------------------------------------------------------------- lesson 05: AMCL particles converging
def amcl():
    import pickle
    from draw_lesson05_figures import show_cost
    d = pickle.load(open(DEV / "nav_amcl.pkl", "rb"))
    tr, P = np.array(d["truth"]), d["particles"]
    first = next(i for i, p in enumerate(P) if p["xyt"][:, 0].std() > 0.3)      # the wrong /initialpose arrives here
    P = P[first:]
    frames, caps = [], []
    for n, p in enumerate(P):
        xyt = p["xyt"]
        i = int(np.argmin(np.abs(tr[:, 0] - p["t"])))
        e = np.hypot(*(xyt[:, :2].mean(0) - tr[i, 1:3])) * 100
        fig, ax = plt.subplots(figsize=(8.6, 6.3), dpi=100)
        show_cost(ax, d["global_costmap"])
        ax.quiver(xyt[:, 0], xyt[:, 1], np.cos(xyt[:, 2]), np.sin(xyt[:, 2]), color="#E53935", scale=34, width=0.004, alpha=0.5)
        ax.add_patch(Circle((tr[i, 1], tr[i, 2]), 0.11, fc=BLUE, ec="white", zorder=6))
        ax.add_patch(Circle((5.9, -2.8), 0.1, fc="none", ec="#7a4b00", lw=1.8, zorder=6))
        ax.set_xlim(3.6, 7.4); ax.set_ylim(-4.4, -1.7)
        ax.set_title(f"{p['t'] - P[0]['t']:4.1f} s · 파티클 {len(xyt):4d} 개 · 퍼짐 {xyt[:, 0].std():.2f} m · 평균과 실제의 차이 {e:3.0f} cm\n"
                     "빨강 화살표 = 파티클 · 파랑 = 실제 위치 · 갈색 원 = 틀리게 알려 준 위치", fontsize=10.5)
        fig.tight_layout()
        frames.append(grab(fig)); plt.close(fig)
        caps.append("틀린 초기 위치 (5.9, -2.8, 23°) 주변에 파티클이 퍼져 있다" if n == 0 else
                    "라이다와 지도가 맞는 파티클만 남아 실제 위치로 모였다" if n == len(P) - 1 else
                    "달리면서 라이다와 맞지 않는 파티클이 사라진다")
    dur = [550] * len(frames); dur[0], dur[-1] = 2200, 3500
    write([captioned(f, c) for f, c in zip(frames, caps)], dur, "lesson05_amcl.gif", colors=64)
    print("amcl:", [(round(p["t"] - P[0]["t"], 1), len(p["xyt"]), round(float(p["xyt"][:, 0].std()), 2)) for p in P])


# ---------------------------------------------------------------- lesson 06: screen frames of the avoidance runs (MuJoCo | RViz)
def _screen(mode, step, caps, name):
    import glob
    MJ, RV = (300, 90, 1180, 860), (700, 300, 1264, 760)
    files = sorted(glob.glob(str(DEV / f"avoid_frames/{mode}_*_mj.png")))[::step]
    frames = []
    for i, f in enumerate(files):
        a = Image.open(f).convert("RGB").crop(MJ); b = Image.open(f.replace("_mj.png", "_rviz.png")).convert("RGB").crop(RV)
        h = 430
        a = a.resize((int(a.width * h / a.height), h)); b = b.resize((int(b.width * h / b.height), h))
        img = Image.new("RGB", (a.width + b.width + 8, h), "white"); img.paste(a, (0, 0)); img.paste(b, (a.width + 8, 0))
        k = int(Path(f).name.split("_")[1])
        frames.append(captioned(img, next(c for lim, c in caps if k <= lim)))
    dur = [350] * len(frames); dur[0], dur[-1] = 1200, 3000
    write(frames, dur, name, colors=96)


def standing():
    _screen("standing", 1, [(5, "관람객이 아직 없다 (로봇은 home)"), (8, "관람객이 길 옆에 선다 → costmap 에 칠해진다"), (12, "/plan 이 관람객 북쪽으로 돌아간다"),
                            (16, "관람객 옆을 지나간다 (가장 가까울 때 0.54 m)"), (99, "인포 앞 도착 · 14 초")], "lesson06_crossing.gif")


def blocked():
    _screen("blocked", 4, [(4, "관람객이 하나뿐인 통로 가운데에 선다"), (12, "다가가다가 멈춘다"), (100, "길이 열리지 않아 그 자리에서 기다린다 (90 초)"),
                           (108, "관람객이 비킨다 → costmap 에서 지워진다"), (999, "같은 목표를 다시 받아 입구로 간다")], "lesson06_headon.gif")


# ---------------------------------------------------------------- lesson 07: the patrol (MuJoCo | RViz) and the dashboard
def patrol():
    import glob
    files = sorted(glob.glob(str(DEV / "patrol_frames/patrol_*_mj.png")))[::4]
    frames = []
    names = ["입구", "교실1", "약국", "인포", "대기 위치"]
    for f in files:
        a = Image.open(f).convert("RGB").crop((300, 90, 1180, 860)); b = Image.open(f.replace("_mj.png", "_rviz.png")).convert("RGB").crop((364, 62, 1264, 868))
        h = 430
        a = a.resize((int(a.width * h / a.height), h)); b = b.resize((int(b.width * h / b.height), h))
        img = Image.new("RGB", (a.width + b.width + 8, h), "white"); img.paste(a, (0, 0)); img.paste(b, (a.width + 8, 0))
        k = int(Path(f).name.split("_")[1])
        leg = min(4, max(0, int((k - 6) / 26)))                    # about 26 frames per leg (0.85 s each)
        frames.append(captioned(img, "순찰 시작 전 (home)" if k < 6 else f"순찰 {leg + 1}/5: {names[leg]} 로"))
    frames[-1] = captioned(frames[-1].crop((0, 0, frames[-1].width, 430)), "순찰 완료: 5 곳 · 88 초")
    dur = [300] * len(frames); dur[0], dur[-1] = 1200, 3000
    write(frames, dur, "lesson07_patrol.gif", colors=96)


def patrol_dash():
    import glob
    files = sorted(glob.glob(str(DEV / "dash_frames/f*.png")))[::2]
    frames = [Image.open(f).convert("RGB").resize((1000, 570)) for f in files]
    caps = ["대시보드: 지도 · 미션 · 로봇 · 카메라가 한 화면에"] * len(frames)
    caps[0] = "시작 대기: [순찰 시작] 버튼 (여기서는 API 로 시작)"; caps[-1] = "순찰 완료: 정지마다의 시간과 오차가 표에 남는다"
    dur = [450] * len(frames); dur[0], dur[-1] = 1500, 3000
    write([captioned(f, c) for f, c in zip(frames, caps)], dur, "lesson07_dashboard.gif", colors=64)


if __name__ == "__main__":
    todo = sys.argv[1:] or ["square", "map_growth", "goal_run", "amcl"]
    for name in todo:
        globals()[name]()
