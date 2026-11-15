"""Figures for the Final Mission page (booth version of lesson 15). Output: docs/camp/lesson15_*.png

    MUJOCO_GL=egl ./scripts/robotworld exec python docs/camp/draw_lesson15_figures.py
Data (2026-11-16, gpt-4.1-mini, `./scripts/robotworld start`, artifacts/docs/l15_run.sh):
  artifacts/docs/l15_final.log            02_final_mission.py, scenarios 1-3 (wall-clock step times)
  artifacts/dev/final_mission.pkl         docs/camp/pick_record.py during that run (sim time)
  artifacts/docs/l15_world_plan*.log      01_world_plan.py: _before = cup table with its first rules, the others = final rules
Robot views are offscreen MuJoCo renders of the recorded state (base pose, cups, joints).
"""
import math
import pickle
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
from draw_lesson08_figures import caption, hstack  # noqa: E402
from draw_lesson11_figures import show_map  # noqa: E402
from make_task_gifs import Replay  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Patch  # noqa: E402
from PIL import Image  # noqa: E402
import yaml  # noqa: E402

A = Path("artifacts/docs")
OUT = Path("docs/camp")
PINK, BLUE, GREEN, GREY, ORANGE, PURPLE, YELLOW, RED = "#D81B60", "#1f4e79", "#2e7d32", "#9e9e9e", "#E65100", "#6A1B9A", "#F9A825", "#C62828"
RUN = pickle.load(open("artifacts/dev/final_mission.pkl", "rb"))
FB = RUN["feedback"]
LOG = [l.rstrip("\n") for l in open(A / "l15_final.log") if "WARN" not in l]


def events(prefix):
    return [f["t"] for f in FB if f["detail"].startswith(prefix)]


PICK_T = [f["t"] for f in FB if f["phase"] == "start" and " sits " in f["detail"]]     # PickPlace pick start, one per scenario
HOLD_T, RELEASE_T, END_T = events("holding at"), events("released"), events("back to transport")
assert len(PICK_T) == len(HOLD_T) == len(RELEASE_T) == len(END_T) == 3, (PICK_T, HOLD_T, RELEASE_T, END_T)
T0 = RUN["base"][0]["t"]
SCEN_T = [(T0, END_T[0] + 1.0), (END_T[0] + 1.0, END_T[1] + 1.0), (END_T[1] + 1.0, END_T[2] + 1.0)]


def run_log():
    """Per scenario: steps [(n, action, start_s, text)], total_s, the world line after it (wall clock, from the log)."""
    out, cur = [], None
    for line in LOG:
        if line.startswith("===== 시나리오"):
            cur = {"steps": [], "total": None, "world": ""}
            out.append(cur)
        m = re.search(r"\[\s*([\d.]+)s (\d)/\d (\w+)/start\] (.*)", line)
        if m and cur is not None:
            cur["steps"].append((int(m.group(2)), m.group(3), float(m.group(1)), m.group(4).strip()))
        m = re.search(r"<< SUCCEEDED .*\((\d+) s\)", line)
        if m and cur is not None:
            cur["total"] = float(m.group(1))
        if line.startswith("[world]") and cur is not None:
            cur["world"] = line[8:].strip()
    return out


RUNS = run_log()
CUP2 = next(s[3] for s in RUNS[1]["steps"] if s[1] == "pick").replace(" 집기", "")          # the cup the planner chose in scenario 2
SCEN = [("① 분홍 컵: 음료대 → 2번 테이블", PINK), (f"② {CUP2}: 음료대 → 1번 테이블", BLUE), ("③ 분홍 컵: 2번 테이블 → 음료대", ORANGE)]


def plan_runs(path):
    res, mode = {}, None
    for line in open(path):
        m = re.match(r"== (none|world)", line)
        if m:
            mode = m.group(1)
            res[mode] = []
        m = re.match(r"^(\d) (ok|XX) ", line)
        if m and mode:
            res[mode].append(m.group(2) == "ok")
    return res


# ================================================================ 1. 개념
def pipeline():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.75, "Final Mission: 문장 하나 → LLM 계획 → Task Manager → Nav2 · MoveIt → MuJoCo, 결과가 다음 계획의 입력이 된다", bold=True, fs=12)
    chain(ax, [("사용자", ["한국어 한 줄", "되묻기 · 확인 답"]), ("PlanParser (LLM)", ["문장 + 컵 위치표", "→ 단계 목록"]),
               ("검증 (코드)", ["validate_world()", "world.check()"]), ("Task Manager", ["/execute_plan", "단계 순차 실행"]),
               ("Nav2 · PickPlace", ["주행 · 도킹", "MoveIt 집기 · 놓기"]), ("MuJoCo", ["물리 · 카메라", "컵이 실제로 움직임"])],
          y=2.3, h=1.8, tfs=10, fs=8.6, gap=0.25, colors=[C["grey"], C["yellow"], C["green"], C["blue"], C["teal"], C["purple"]])
    arrow(ax, (12.6, 2.2), (12.6, 1.45))
    arrow(ax, (12.6, 1.45), (3.4, 1.45))
    arrow(ax, (3.4, 1.45), (3.4, 2.2))
    label(ax, 8.0, 1.45, "결과 (steps_done, success) → world.apply() → 컵 위치표 갱신", fs=9.6)
    note(ax, 0.3, 0.6, "Task Pipeline 글과 같은 파이프라인 + 컵 위치표(WorldState) 하나. 코드: lessons/10_final_project/, commands/world.py", fs=9.6)
    save(fig, "lesson15_pipeline.png")


def why_table():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.65, "LLM 은 부스를 못 본다: 이미 옮긴 컵도 '음료대에서 집기' 로 계획한다", bold=True, fs=12)
    rbox(ax, 0.3, 0.5, 6.5, 3.7, "표 없음 (Task Pipeline 글의 실측)", ["분홍 컵은 이미 2번 상담 테이블에 있다", "", "\"분홍 컵을 음료대에서 1번 테이블로 옮겨\"",
                                                             "→ navigate(drinks) → pick @drinks ...", "",
                                                             "2 단계 pick 실패: 팔이 닿지 않음 (No IK solution)", "84 s 동안 음료대까지 갔다가 끝"], fc=C["red"], fs=9.8, dy=0.38)
    rbox(ax, 7.2, 0.5, 6.5, 3.7, "표를 프롬프트에 (이번 글)", ["cup_pink: consult_2 (2번 상담 테이블)", "",
                                                       "\"분홍 컵 다시 음료대로 가져와\"", "→ navigate(consult_2) → pick @consult_2", "→ navigate(drinks) → place @drinks", "",
                                                       f"4/4 단계, {RUNS[2]['total']:.0f} s (실측)"], fc=C["green"], fs=9.8, dy=0.38)
    arrow(ax, (6.8, 2.35), (7.2, 2.35))
    save(fig, "lesson15_why.png")


def world_state():
    fig, ax = fig_ax(14, 4.7)
    ax.set_ylim(0.7, 4.7)
    note(ax, 0.3, 4.45, "WorldState (commands/world.py): 컵마다 한 줄 — drinks · consult_1 · consult_2 · held · unknown", bold=True, fs=12)
    tiles(ax, [("① prompt(): 계획 전", ["컵 3 줄 + 손님 2 줄 + 규칙", "system 프롬프트 끝에 붙인다", "출발지 = 표에 적힌 곳"], C["yellow"]),
               ("② check(plan): 실행 전", ["집으려는 컵이 다른 곳에 있다", "컵이 이미 도착지에 있다", "→ 실행하지 않고 다시 묻는다"], C["green"]),
               ("③ apply(): 실행 뒤", ["끝난 단계(steps_done)만 반영", "pick 끝 → held, place 끝 → 그 테이블", "실패한 pick · place → unknown"], C["blue"])],
          cols=3, y_top=4.0, gap=0.3, h=1.9, tfs=11, fs=9.4)
    note(ax, 0.3, 1.5, "처음 값: 세 컵 모두 drinks (음료대). 시뮬레이터를 다시 띄우면 컵도 처음 자리로 돌아가므로 표도 처음부터.", fs=9.6)
    note(ax, 0.3, 1.05, "표는 '로봇이 마지막으로 확인한 것' 이다. 사람이 컵을 치우면 표와 실제가 달라진다 → 그때는 pick 이 실패하고 unknown 이 된다.", fs=9.6)
    save(fig, "lesson15_world.png")


def roles():
    final = [plan_runs(A / f)for f in ("l15_world_plan.log", "l15_world_plan_run2.log", "l15_world_plan_run3.log")]
    before = plan_runs(A / "l15_world_plan_before.log")
    runs = {"표 없음": [before["none"]] + [r["none"] for r in final],
            "표 (처음 규칙)": [before["world"]],
            "표 + '되돌리기 · 되묻기'\n규칙 (최종)": [r["world"] for r in final]}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.0), dpi=150, gridspec_kw={"width_ratios": [1.15, 1]})
    a1.set_xlim(0, 7)
    a1.set_ylim(0, 5)
    a1.axis("off")
    a1.text(0.1, 4.75, "누가 무엇을 정하나", fontsize=12, fontweight="bold", color=INK)
    rbox(a1, 0.1, 2.35, 3.25, 2.1, "LLM: 의도", ["무엇을 · 어디로", "\"다시\", \"원래 자리\", \"흰 옷 손님\" 해석", "되묻기 · 거부 문장"], fc=C["yellow"], fs=9.4, dy=0.38)
    rbox(a1, 3.6, 2.35, 3.25, 2.1, "코드: 사실", ["컵이 지금 어디 있나", "이미 도착지에 있나", "든 것 · 장소 (validate_world)"], fc=C["green"], fs=9.4, dy=0.38)
    a1.text(0.1, 1.75, "표만 넣었을 때: '원래 자리로 돌려놔' · '음료대로 치워 줘' 를", fontsize=9.6, color="#444")
    a1.text(0.1, 1.35, "\"음료대에는 그 컵이 없다\" 며 거절했다 (도착지를 출발지로 읽음).", fontsize=9.6, color="#444")
    a1.text(0.1, 0.85, "표의 규칙에 '~로 는 도착지 · 원래 자리 = 음료대' 를 넣은 뒤", fontsize=9.6, color="#444")
    a1.text(0.1, 0.45, "8/8 (3 회 연속). '이미 있다' 판정은 처음부터 코드 (check) 가 한다.", fontsize=9.6, color="#444")
    names = list(runs)
    for i, n in enumerate(names):
        vals = [sum(r) for r in runs[n]]
        a2.bar(i, sum(vals) / len(vals), color=[GREY, YELLOW, GREEN][i], alpha=0.85, width=0.62)
        for j, v in enumerate(vals):
            a2.plot(i - 0.18 + 0.36 * j / max(1, len(vals) - 1) if len(vals) > 1 else i, v, "o", color="k", ms=5, zorder=4)
        a2.text(i, max(vals) + 0.35, " · ".join(str(v) for v in vals), ha="center", fontsize=9.2)
    a2.set_xticks(range(len(names)))
    a2.set_xticklabels(names, fontsize=8.8)
    a2.set_ylim(0, 9)
    a2.set_ylabel("맞은 문장 수 / 8")
    a2.set_title("01_world_plan.py 8 문장 (점 = 1 회 실행)", fontsize=10.5)
    a2.grid(axis="y", alpha=0.3)
    save(fig, "lesson15_roles.png")


def scenarios():
    fig, ax = fig_ax(14, 5.0)
    ax.set_ylim(1.3, 5.0)
    note(ax, 0.3, 4.75, "시나리오 3 개 (02_final_mission.py, 이어서 실행 — 표가 다음 시나리오로 넘어간다)", bold=True, fs=12)
    items = [("① 분홍 컵", ["\"음료대로 가서 분홍 컵을 집고", " 2번 상담 테이블에 가져다 드려\" → \"응\"", "", "표 뒤: 분홍 = 2번 상담 테이블"], C["red"]),
             ("② 음료 한 잔 (되묻기)", ["\"손님께 음료 한 잔 가져다 드려\"", "→ 어느 테이블? → \"안쪽 테이블\" → \"응\"", "", f"표 뒤: {CUP2} = 1번 상담 테이블"], C["blue"]),
             ("③ 분홍 컵 되돌리기", ["\"분홍 컵 다시 음료대로 가져와\"", "→ 표를 보고 pick @consult_2", "", "표 뒤: 분홍 = 음료대"], C["yellow"])]
    tiles(ax, items, cols=3, y_top=4.3, gap=0.3, h=2.0, tfs=11, fs=9.4)
    note(ax, 0.3, 1.75, "모두 4 단계: navigate(출발) → pick → navigate(도착) → place. 확인 \"진행할까요?\" 에 \"응\" 이면 실행. ② 의 컵은 음료대에 남은 것 중에서 플래너가 골랐다.", fs=9.4)
    save(fig, "lesson15_scenarios.png")


# ================================================================ 2. 실행
def still(t, distance, **view):
    rp = Replay(RUN, 560, 420)
    return rp.image(t, distance, **view)


def start_screen():
    img = Replay(RUN, 1000, 560).image(T0 + 1.0, 5.5, offset=20.0, elevation=-40.0)
    img.save(OUT / "lesson15_start.png")
    print("saved lesson15_start.png")


def routes():
    fig, ax = plt.subplots(figsize=(13, 9.0), dpi=150)
    show_map(ax)
    for (lab, col), (a, z), off in zip(SCEN, SCEN_T, (0.0, 0.04, -0.04)):
        seg = [r["pose"] for r in RUN["base"] if a <= r["t"] <= z]
        ax.plot([q[0] + off for q in seg], [q[1] + off for q in seg], color=col, lw=2.4, label=f"{lab}  (sim {z - a:.0f} s)", zorder=4)
    loc = yaml.safe_load(open("src/warehouse_lecture/worlds/locations.yaml"))["locations"]
    for key, name in (("drinks", "음료대"), ("consult_1", "1번 상담 테이블"), ("consult_2", "2번 상담 테이블")):
        x, y, yaw = loc[key]["base_goal"]
        ax.add_patch(FancyArrowPatch((x, y), (x + 0.5 * math.cos(yaw), y + 0.5 * math.sin(yaw)), arrowstyle="-|>", mutation_scale=16, color="k", lw=2, zorder=6))
        ax.text(x - 0.15, y - 0.3, name, ha="right", fontsize=10, bbox=dict(fc="white", ec="none", alpha=0.85), zorder=7)
    p0 = RUN["base"][0]["pose"]
    ax.plot(p0[0], p0[1], "*", color="k", ms=14, zorder=6)
    ax.text(p0[0] + 0.15, p0[1] + 0.15, "출발", fontsize=10, bbox=dict(fc="white", ec="none", alpha=0.85))
    ax.legend(loc="upper left", fontsize=10, framealpha=0.95)
    ax.set_title("세 시나리오의 실제 경로 (/ground_truth, 겹치지 않게 4 cm 씩 비켜 그림). 화살표 = 사전 도킹 지점과 방향", fontsize=12)
    ax.set_xlabel("map x (m)")
    ax.set_ylabel("map y (m)")
    save(fig, "lesson15_routes.png")


def scenes():
    view = dict(offset=0.0, elevation=-38.0)
    items = [(HOLD_T[0] + 0.5, "① 분홍 집기", "음료대"), (RELEASE_T[0], "① 분홍 놓기", "2번 상담 테이블"),
             (HOLD_T[1] + 0.5, f"② {CUP2} 집기", "음료대"), (RELEASE_T[1], f"② {CUP2} 놓기", "1번 상담 테이블"),
             (HOLD_T[2] + 0.5, "③ 분홍 다시 집기", "2번 상담 테이블"), (RELEASE_T[2], "③ 분홍 되돌림", "음료대")]
    imgs = [caption(still(t, 2.3, **view), a, s) for t, a, s in items]
    rows = [hstack(imgs[:3]), hstack(imgs[3:])]
    out = Image.new("RGB", (rows[0].width, rows[0].height * 2 + 16), "white")
    out.paste(rows[0], (0, 0))
    out.paste(rows[1], (0, rows[0].height + 16))
    out.save(OUT / "lesson15_scenes.png")
    print("saved lesson15_scenes.png")


def timeline():
    cols = {"navigate": BLUE, "pick": GREEN, "place": PURPLE}
    fig, ax = plt.subplots(figsize=(14, 4.8), dpi=150)
    longest = max(sc["total"] for sc in RUNS)
    for i, sc in enumerate(RUNS):
        y = 2 - i
        bounds = [s[2] for s in sc["steps"]] + [sc["total"]]
        for (n, act, t0, txt), t1 in zip(sc["steps"], bounds[1:]):
            ax.barh(y, t1 - t0, left=t0, color=cols.get(act, GREY), alpha=0.85, edgecolor="white", height=0.55)
            if t1 - t0 > 9:
                ax.text((t0 + t1) / 2, y, f"{n} {act}\n{t1 - t0:.0f} s", ha="center", va="center", fontsize=8.4, color="white", fontweight="bold")
        ax.text(sc["total"] + 3, y, f"{sc['total']:.0f} s", va="center", fontsize=10, fontweight="bold")
        ax.text(-4, y, SCEN[i][0], ha="right", va="center", fontsize=9.4, color=SCEN[i][1], fontweight="bold")
        ax.text(2, y - 0.42, f"표 → {sc['world']}", va="center", fontsize=8.6, color="#444")
    ax.set_xlim(0, longest * 1.1)
    ax.set_ylim(-0.75, 2.7)
    ax.set_yticks([])
    ax.set_xlabel("실행 시작부터 (s, 벽시계)")
    ax.set_title("단계별 시간과 실행 뒤의 컵 위치표 (실측, 처음 표: 세 컵 모두 음료대)", fontsize=11)
    ax.legend(handles=[Patch(color=c, alpha=0.85, label=k) for k, c in cols.items()], loc="upper right", ncol=3, fontsize=9)
    ax.grid(axis="x", alpha=0.3)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    fig.subplots_adjust(left=0.24)
    save(fig, "lesson15_timeline.png")


if __name__ == "__main__":
    for f in (pipeline, why_table, world_state, roles, scenarios, start_screen, routes, scenes, timeline):
        f()
