"""Captioned GIFs for the lesson 07 - 15 pages, from runs recorded earlier (no simulator needed).

  MUJOCO_GL=egl python docs/camp/make_task_gifs.py [name ...]      # workspace root, venv python; no name = all
Robot scenes are offscreen MuJoCo renders of the recorded state (pick_record.py / arm_record.py pickles: joint states,
base pose, parcel poses) with a chase camera; the subtitle is the PickPlace feedback phase at that moment.
Screen GIFs (patrol, dashboards) are the screenshots saved while those pages were written.
"""
import math
import pickle
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from make_nav_gifs import captioned, write  # noqa: E402

DEV = Path("artifacts/dev")
SPAWN = (5.3, -3.2)
CUPS = ("cup_pink", "cup_blue", "cup_yellow")
BOLD = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
PHASE = {"start": "시작: 컵 위치를 보고 집을 팔을 고른다", "navigate_pick": "음료대 앞으로 이동", "dock": "도킹: ArUco 마커를 보며 스테이션에 맞춘다",
         "locate": "컵 위치를 확인한다", "pre_grasp": "집기 직전 자세로 팔을 뻗는다", "grasp": "그리퍼를 닫아 컵을 집는다",
         "lift": "들어 올린다", "carry": "운반 자세로 팔을 든다", "navigate_place": "놓을 스테이션 앞으로 이동",
         "place": "내려놓고 그리퍼를 연다", "retreat": "팔을 거두고 물러난다"}
CLOSE = {"dock", "locate", "pre_grasp", "grasp", "lift", "carry", "place", "retreat"}


def near(rows, t):
    lo, hi = 0, len(rows) - 1
    while lo < hi:                                       # rows are sorted by time
        mid = (lo + hi) // 2
        if rows[mid]["t"] < t:
            lo = mid + 1
        else:
            hi = mid
    return rows[lo]


class Replay:
    def __init__(self, run, w=720, h=405):
        import mujoco
        self.mj, self.run = mujoco, run
        self.m = mujoco.MjModel.from_xml_path("artifacts/mobile_generated/warehouse.xml")
        self.d = mujoco.MjData(self.m)
        self.r = mujoco.Renderer(self.m, h, w)
        self.opt = mujoco.MjvOption()
        self.opt.geomgroup[1] = 0                         # hide collision geoms
        self.cam = mujoco.MjvCamera()
        self.az = None
        self.base = self.m.joint("floating_base").qposadr[0]
        self.d.qpos[self.base:self.base + 2] = SPAWN       # the saved model has the robot at the origin; the bridge starts it at home

    def set(self, t):
        m, d, run = self.m, self.d, self.run
        s = near(run["states"], t)
        for n, q in zip(s["names"], s["positions"]):
            try:
                d.qpos[m.joint(n).qposadr[0]] = q
            except KeyError:
                pass
        a = self.base
        if "base" in run:
            p = near(run["base"], t)["pose"]
            d.qpos[a:a + 2] = p[:2]
            d.qpos[a + 3:a + 7] = [p[6], p[3], p[4], p[5]]
            for name, q in zip(CUPS, near(run["objects"], t)["poses"]):
                b = m.joint(f"{name}_free").qposadr[0]
                d.qpos[b:b + 3] = q[:3]
                d.qpos[b + 3:b + 7] = [q[6], q[3], q[4], q[5]]
        self.mj.mj_forward(m, d)
        w, x, y, z = d.qpos[a + 3:a + 7]
        return d.qpos[a], d.qpos[a + 1], math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))

    def image(self, t, distance, offset=35.0, elevation=-28.0, height=0.75, ahead=0.35):
        x, y, yaw = self.set(t)
        target = yaw + offset
        if self.az is None:
            self.az = target
        self.az += ((target - self.az + 180) % 360 - 180) * 0.25      # the camera swings round slowly
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        self.cam.lookat[:] = [x + ahead * c, y + ahead * s, height]
        self.cam.distance, self.cam.azimuth, self.cam.elevation = distance, self.az, elevation
        self.r.update_scene(self.d, self.cam, self.opt)
        return Image.fromarray(self.r.render())


def hud(img, text):
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(BOLD, 18)
    d.rounded_rectangle((img.width - 22 - d.textlength(text, font=font), 8, img.width - 8, 36), 6, fill="#111111")
    d.text((img.width - 15 - d.textlength(text, font=font), 12), text, fill="#FFD75F", font=font)
    return img


def task(pkl, name, t0, t1, dt, labels=None, lead=None, tail_text="끝: 컵이 옮겨졌다", scenario=None, view=None):
    """Replay [t0, t1] of a PickPlace recording, one frame per dt sim seconds."""
    run = pickle.load(open(DEV / pkl, "rb"))
    labels = {**PHASE, **(labels or {})}
    fb, rp = run["feedback"], Replay(run)
    frames, durs = [], []
    for t in np.arange(t0, t1, dt):
        past = [f for f in fb if f["t"] <= t]
        phase = past[-1]["phase"] if past else None
        done = bool(past) and t > fb[-1]["t"] + 3
        text = tail_text if done else labels.get(phase, lead or "명령을 기다린다")
        img = rp.image(t, 2.3 if phase in CLOSE and not done else 3.6, **(view or {}))
        tag = f"시뮬레이션 {t - t0:4.0f} s"
        if scenario:
            tag = scenario(t) + "  ·  " + tag
        frames.append(captioned(hud(img, tag), text)); durs.append(110)
    durs[0], durs[-1] = 1200, 3000
    write(frames, durs, name, colors=128)


def arm(pkl, name, t0, t1, dt, stages, distance=1.75):
    """Replay of an arm-only recording (arm_record.py): the base stays where the model puts it."""
    run = pickle.load(open(DEV / pkl, "rb"))
    rp = Replay(run)
    frames, durs = [], []
    for t in np.arange(t0, t1, dt):
        text = next(s for a, s in reversed(stages) if t >= a)
        img = rp.image(t, distance, offset=150.0, elevation=-12.0, height=1.0, ahead=0.25)
        frames.append(captioned(hud(img, f"시뮬레이션 {t - t0:4.1f} s"), text)); durs.append(110)
    durs[0], durs[-1] = 1200, 2500
    write(frames, durs, name, colors=96)


def moveit_ready():      # lesson 08: `arm both ready` executed by the MuJoCo trajectory action
    run = pickle.load(open(DEV / "arm_ready.pkl", "rb"))
    t_plan = run["plans"][0]["t"]
    t_end = t_plan + run["plans"][0]["times"][-1]
    arm("arm_ready.pkl", "lesson08_ready.gif", t_plan - 1.0, t_end + 2.0, 0.12,
        [(0, "운반 자세에서 시작"), (t_plan, "MoveIt 이 계획한 궤적을 MuJoCo 의 양팔이 따라간다"), (t_end, "ready 자세 도착")])


def ee_demo():           # lesson 09: ready -> IK pose -> straight down -> grip -> straight up  (times from draw_lesson09_figures.py)
    arm("ee_demo.pkl", "lesson09_ee_demo.gif", 64.5, 84.0, 0.16,
        [(0, "운반 자세에서 시작"), (65.6, "ready 자세로 (관절 목표)"), (69.6, "IK: 손끝을 목표 위치 · 자세로"),
         (74.96, "Cartesian: 손끝을 똑바로 아래로"), (76.05, "그리퍼 닫기 · 열기"), (76.2, "Cartesian: 똑바로 위로"), (77.4, "운반 자세로 돌아간다"), (83.0, "끝")])


def pick_place():        # lesson 10: the robot starts in front of the drinks stand, so no Nav2 travel
    run = pickle.load(open(DEV / "pick_pink.pkl", "rb"))
    fb = run["feedback"]
    second = next(f["t"] for f in fb[5:] if f["detail"].startswith("cup_pink sits"))      # the CLI run after it is not shown
    run["feedback"] = [f for f in fb if f["t"] < second]
    pickle.dump(run, open(DEV / "pick_pink_first.pkl", "wb"))
    task("pick_pink_first.pkl", "lesson10_pick_place.gif", fb[0]["t"] - 1.0, run["feedback"][-1]["t"] + 6.0, 1.0,
         tail_text="끝: 분홍 컵이 음료대의 빈 자리에 다시 놓였다", view=dict(offset=0.0, elevation=-40.0))


def transport():         # lesson 11: the pink cup from the drinks stand to consult table 2
    run = pickle.load(open(DEV / "transport_pink.pkl", "rb"))
    fb = run["feedback"]
    starts = [f["t"] for f in fb if f["phase"] == "start"]
    end = starts[1] if len(starts) > 1 else fb[-1]["t"] + 8.0         # the blue cup run follows in the same recording
    run["feedback"] = [f for f in fb if f["t"] < end]
    pickle.dump(run, open(DEV / "transport_pink_first.pkl", "wb"))
    task("transport_pink_first.pkl", "lesson11_transport.gif", starts[0] - 1.0, run["feedback"][-1]["t"] + 6.0, 1.6,
         labels={"navigate_place": "컵을 든 채 상담 테이블 2 앞으로 이동"}, tail_text="끝: 분홍 컵이 상담 테이블 2 에 놓였다", view=dict(offset=0.0, elevation=-38.0))


def mission():           # lesson 13: "손님께 음료 가져다 드려" -> Task Manager runs navigate / pick / navigate / place
    run = pickle.load(open(DEV / "mission_text.pkl", "rb"))
    fb = run["feedback"]
    task("mission_text.pkl", "lesson13_mission.gif", fb[0]["t"] - 18.0, fb[-1]["t"] + 6.0, 1.6, lead="1 단계 navigate: 음료대로 이동",
         labels={"navigate_place": "3 단계 navigate → 4 단계 place: 상담 테이블 2 앞으로"}, tail_text="끝: 분홍 컵을 2번 상담 테이블에 놓았습니다",
         view=dict(offset=0.0, elevation=-38.0))


def final():             # lesson 15: three scenarios in one run; the tag says which one
    run = pickle.load(open(DEV / "final_mission.pkl", "rb"))
    fb = run["feedback"]
    ends = [f["t"] for f in fb if f["detail"].startswith("back to transport")]
    names = ["① 분홍 컵 → 2번 테이블", "② 음료 한 잔 → 1번 테이블", "③ 분홍 컵 → 음료대"]
    task("final_mission.pkl", "lesson15_final.gif", fb[0]["t"] - 18.0, ends[-1] + 8.0, 5.0, lead="navigate: 컵이 있는 곳으로 이동",
         labels={"navigate_place": "컵을 든 채 놓을 곳 앞으로 이동", "start": "다음 단계 시작"}, tail_text="끝: 컵 위치표 = 분홍 음료대 · 파랑 1번 테이블 · 노랑 음료대",
         scenario=lambda t: names[sum(t > e + 1.0 for e in ends[:2])], view=dict(offset=0.0, elevation=-38.0))


if __name__ == "__main__":
    for name in (sys.argv[1:] or ["moveit_ready"]):
        globals()[name]()
