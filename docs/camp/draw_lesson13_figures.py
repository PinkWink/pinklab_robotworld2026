"""Figures for the lesson-13 Confluence page (LLM -> ROS 2 Task Pipeline). Output: docs/camp/lesson13_*.png

    python3 docs/camp/draw_lesson13_figures.py
Data (2026-11-15, gpt-4.1-mini, booth, `./scripts/robotworld start`):
  artifacts/docs/l13_mission.log   08_text_mission.py --lines "손님께 음료 가져다 드려" "2번 테이블" "응"
  artifacts/docs/l13_fail.log      08_text_mission.py --lines "분홍 컵을 음료대에서 1번 테이블로 옮겨" "응"  (the cup was already on consult_2)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

OUT = Path("docs/camp")
RED, BLUE, GREEN, GREY, ORANGE = "#C62828", "#1f4e79", "#2e7d32", "#9e9e9e", "#E65100"
LOG = [l.rstrip("\n") for l in open("artifacts/docs/l13_mission.log") if "WARN" not in l]


# ================================================================ 1. 개념
def why():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.15, "앞 글은 문장 하나 = 명령 하나. 이번 글은 문장 하나 = 단계 목록, Task Manager 가 차례로 실행한다.", bold=True, fs=12)
    tiles(ax, [("앞 글: RobotCommand", ["\"분홍 컵 2번 테이블로\" → move_object 하나", "실행기가 안에서 알아서 처리", "중간 단계는 안 보인다"], C["grey"]),
               ("이번 글: RobotPlan", ["→ navigate · pick · navigate · place", "단계마다 번호 · 피드백 · 결과", "확인 문장에 단계 목록을 보여 준다"], C["blue"]),
               ("Task Manager", ["ExecutePlan 액션 서버", "Nav2 · PickPlace(MoveIt) · 카메라 · LLM 보고", "실패하면 몇 단계까지 했는지 말한다"], C["green"])],
          cols=3, y_top=3.7, gap=0.3, h=2.2, tfs=11, fs=9)
    note(ax, 0.3, 1.05, "예제: lessons/08_lmm/  05_plan · 06_plan_accuracy · 07_run_plan · 08_text_mission   (Task Manager 는 ./scripts/robotworld start 에 포함)", fs=9.8)
    save(fig, "lesson13_why.png")


def plan_schema():
    fig, ax = fig_ax(14, 5.2)
    note(ax, 0.3, 4.95, "RobotPlan = summary + steps[PlanStep] + reply   (warehouse_lecture/commands/plan.py)", bold=True, fs=12)
    rows = [("navigate", "location 으로 Nav2 (든 것이 없으면 팔 transport)", C["blue"]), ("detect", "target 이 카메라에 보일 때까지 최대 10 s (부스 계획기는 쓰지 않음)", C["yellow"]),
            ("pick", "PickPlace phase=pick: 도킹 · 파지 · hands_up · 후진", C["green"]), ("place", "PickPlace phase=place: 도킹 · 놓기 · transport · 후진", C["green"]),
            ("arm_pose · gripper", "MoveIt 이름 자세 · 그리퍼 (든 채로는 금지)", C["purple"]), ("report · answer", "카메라 세계 상태 → LLM 문장 · reply 그대로", C["grey"])]
    for i, (k, v, fc) in enumerate(rows):
        y = 4.1 - i * 0.68
        rbox(ax, 0.3, y, 2.8, 0.55, k, fc=fc, tfs=10.5)
        ax.text(3.35, y + 0.27, v, va="center", fontsize=9.8, color=INK)
    rbox(ax, 9.6, 0.4, 4.1, 4.2, "PlanStep 필드", ["action: 위 8 가지", "target: cup_pink · person ·", "        ready · open ...", "location: 장소 enum (13 개)",
                                               "note: 한국어 한 구절", "", "steps 가 비면 = 되묻기 · 거부 ·", "답변 (reply 만)"], fc=C["teal"], align="left", fs=9.2, dy=0.42)
    save(fig, "lesson13_plan_schema.png")


def pipeline():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.35, "누가 무엇을 하나", bold=True, fs=12)
    chain(ax, [("사용자", ["텍스트 한 줄"]), ("PlanDialogManager", ["되묻기 · 확인", "문맥 6 턴"]), ("PlanParser (LLM)", ["문장 → RobotPlan", "~1.5 s"]),
               ("validate_world()", ["빠진 navigate 추가", "든 것 · 장소 검사"]), ("Task Manager", ["/execute_plan", "단계 순차 실행"]),
               ("Nav2 · PickPlace", ["MoveIt · 도킹", "카메라 · MuJoCo"])],
          y=1.7, h=1.9, tfs=10, fs=8.6, gap=0.25, colors=[C["grey"], C["purple"], C["yellow"], C["green"], C["blue"], C["teal"]])
    arrow(ax, (12.0, 1.6), (12.0, 1.05))
    arrow(ax, (12.0, 1.05), (1.4, 1.05))
    arrow(ax, (1.4, 1.05), (1.4, 1.6))
    label(ax, 6.7, 1.05, "결과 문장 (spoken): \"분홍 컵을 2번 상담 테이블에 놓았습니다.\" / 실패면 몇 단계까지 했는지", fs=9.4)
    note(ax, 0.3, 0.45, "LLM 은 단계만 정한다. 관절 · 속도 · 경로 · 도킹 거리는 아래 층이 정한다.", fs=9.6)
    save(fig, "lesson13_pipeline.png")


def validate_rules():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.55, "RobotPlan.validate_world(): 단계를 따라가며 '지금 어디 있나 (here)' 와 '무엇을 들었나 (held)' 를 센다", bold=True, fs=12)
    tiles(ax, [("고쳐 주는 것", ["pick / place 앞에 navigate 가 없으면 끼워 넣음", "pick 의 장소가 비면 지금 있는 스테이션 (없으면 음료대)", "place 의 target 은 든 컵"], C["green"]),
               ("거부하는 것", ["든 것 없이 place", "들고 있는데 또 pick (한 번에 하나)", "컵을 든 채로 끝나는 계획", "든 채 arm_pose · gripper open"], C["red"]),
               ("확인을 묻는 것", ["pick 이나 place 가 있는 계획", "단계 목록을 보여 주고 \"진행할까요?\"", "이동 + 보고는 바로 실행"], C["yellow"])],
          cols=3, y_top=4.1, gap=0.3, h=2.6, tfs=11, fs=9)
    note(ax, 0.3, 1.0, "05_plan.py 실측: [pick cup_pink, place @consult_2] → navigate 두 개가 '(자동 추가)' 되어 4 단계.", fs=9.6)
    note(ax, 0.3, 0.55, "[navigate consult_1, place] → \"든 것이 없는데 놓으려 한다 (pick 단계가 먼저 필요)\"", fs=9.6)
    save(fig, "lesson13_validate.png")


def dialog_states():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.35, "PlanDialogManager.handle(text): 한 턴에 하는 일", bold=True, fs=12)
    rbox(ax, 0.3, 1.9, 2.4, 1.6, "문장", ["(되묻는 중이면", "앞 문장 / 답)"], fc=C["grey"], tfs=10.5, fs=8.8)
    rbox(ax, 3.2, 1.9, 2.6, 1.6, "LLM 계획", ["+ validate_world()"], fc=C["yellow"], tfs=10.5, fs=8.8)
    arrow(ax, (2.7, 2.7), (3.2, 2.7))
    outs = [(3.6, "steps 없음 / 문제 있음", "reply 를 말함. 질문이면 문장을 기억 (clarify)", C["purple"]),
            (2.5, "pick · place 있음", "단계 목록 + \"진행할까요?\" (confirm)", C["yellow"]),
            (1.4, "그 밖 (이동 · 보고)", "바로 실행 → 결과 문장 (result)", C["green"])]
    for y, a, b, fc in outs:
        rbox(ax, 6.6, y - 0.05, 2.9, 0.8, a, fc=fc, tfs=9.6)
        ax.text(9.7, y + 0.35, b, va="center", fontsize=9.6)
        arrow(ax, (5.8, 2.7), (6.6, y + 0.35))
    rbox(ax, 0.3, 0.2, 13.4, 0.85, "확인 대기 중의 다음 문장:  응 · 네 · 좋아 … → 실행   |   아니 · 취소 … → 취소   |   그 밖 → 새 문장으로 처리 (고쳐 말하기)", fc=C["teal"], tfs=9.8)
    save(fig, "lesson13_dialog.png")


def failure():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.95, "실패하면: 거기서 멈추고, 무엇을 했고 무엇을 들고 있는지 말한다", bold=True, fs=12)
    tiles(ax, [("Task Manager", ["실패한 단계에서 멈춤", "result: steps_done · failed_step", "spoken: \"N단계까지 마쳤지만 실패했습니다: …\"", "들고 있으면 \"… 아직 들고 있습니다\""], C["blue"]),
               ("PickPlace 서버 (recover)", ["컵을 든 채 실패하면", "그리퍼 열기 → detach → 손 후퇴", "→ transport 자세", "(MoveIt 이 막히지 않게)"], C["green"]),
               ("이번 실측 (08)", ["분홍 컵은 이미 2번 테이블에 있음", "LLM 은 모름 → 음료대로 가는 계획", "2 단계 pick: 팔이 닿지 않음 (No IK solution)", "1/4 단계 · 84 s 에 멈춤"], C["red"])],
          cols=3, y_top=3.5, gap=0.3, h=2.6, tfs=11, fs=9)
    note(ax, 0.3, 0.55, "LLM 이 컵의 현재 위치를 모르는 한 이런 계획은 다시 나온다. 컵 위치를 기억해 프롬프트에 넣는 일은 Final Mission 글에서 다룬다.", fs=9.6)
    save(fig, "lesson13_failure.png")


# ================================================================ 2. 실행
def start_screen():
    Image.open(OUT / "lesson11_run_result.png").save(OUT / "lesson13_run_result.png")      # same `start` screen as the previous page
    print("saved lesson13_run_result.png")


def timeline():
    """Blue mission from 08.log: dialog turns, Task Manager steps and PickPlace phases on one wall-clock axis."""
    turns, steps, phases = [], [], []
    base = None
    for line in LOG:
        m = re.match(r"\[\s*([\d.]+)s (user |robot)\] (.*)", line)
        if m:
            turns.append((float(m.group(1)), m.group(2).strip(), m.group(3)))
            continue
        if line.startswith(">> plan:") and base is None:
            base = turns[-1][0]
        m = re.match(r"\s+\[\s*([\d.]+)s (\d)/(\d) (\w+)/(\w+)\] (.*)", line)
        if m and base is not None and len(steps) < 99:
            t = base + float(m.group(1))
            if m.group(5) == "start":
                steps.append((t, int(m.group(2)), m.group(4), m.group(6)))
            elif m.group(5) == "pick_place":
                ph = m.group(6).split(":")[0]
                if not phases or phases[-1][1] != ph:
                    phases.append((t, ph))
        if line.startswith("<< ") and base is not None:
            end = base + float(re.search(r"\((\d+) s\)", line).group(1))
            break
    fig, ax = plt.subplots(figsize=(14, 4.4), dpi=150)
    cols = {"navigate": C["blue"], "detect": C["yellow"], "pick": C["green"], "place": C["green"]}
    talk = max(t for t, who, _ in turns if t <= base + 0.01)
    for i, (t, k, action, text) in enumerate(steps):
        t1 = steps[i + 1][0] if i + 1 < len(steps) else end
        ax.barh(1, t1 - t, left=t, color=cols.get(action, C["grey"]), ec=INK, lw=0.8, height=0.55)
        ax.text((t + t1) / 2, 1 if t1 - t > 12 else 1.42, f"{k}. {action}\n{t1 - t:.0f} s", ha="center", va="center", fontsize=8.8)
    pcol = {"navigate_pick": C["blue"], "navigate_place": C["blue"], "dock": C["teal"], "locate": C["yellow"], "pre_grasp": "#C8E6C9", "grasp": "#A5D6A7",
            "lift": "#81C784", "carry": C["purple"], "place": "#C8E6C9", "retreat": C["purple"], "start": "#ffffff"}
    nexts = [p[0] for p in phases[1:]]
    stops = []
    for i, (t, ph) in enumerate(phases):
        stop = nexts[i] if i < len(nexts) else end
        owner = max((s for s in steps if s[0] <= t), key=lambda s: s[0])
        owner_end = next((s[0] for s in steps if s[0] > owner[0]), end)
        stop = min(stop, owner_end)
        ax.barh(0, stop - t, left=t, color=pcol.get(ph, C["grey"]), ec=INK, lw=0.5, height=0.55)
        if stop - t > 14:
            ax.text((t + stop) / 2, 0, ph, ha="center", va="center", fontsize=7.8, rotation=0)
    for t, who, text in turns:
        if t <= base + 0.01:
            ax.plot(t, 2, "o" if who == "user" else "s", color=GREY if who == "user" else ORANGE, ms=7)
    ax.text(base + 3, 2, f"대화: 손님께 음료 가져다 드려 → (되묻기) → 2번 테이블 → (단계 확인) → 응   [LLM 2 번, {talk:.1f} s]", va="center", fontsize=9)
    ax.set_yticks([2, 1, 0], ["대화 (LLM)", "Task Manager 단계", "PickPlace 단계"])
    ax.set_xlim(-2, end + 4)
    ax.set_ylim(-0.6, 2.5)
    ax.set_xlabel("s (벽시계, 08_text_mission.py 출력)")
    ax.set_title(f"분홍 컵 미션: 대화 {talk:.0f} s + 실행 {end - base:.0f} s (실측)", fontsize=12)
    ax.grid(axis="x", alpha=0.3)
    save(fig, "lesson13_timeline.png")


if __name__ == "__main__":
    for f in (why, plan_schema, pipeline, validate_rules, dialog_states, failure, start_screen, timeline):
        f()
