"""Terminal captures for the lesson-13 (LLM -> ROS 2 Task Pipeline) page, rendered from the logs of real runs on 2026-11-15
(gpt-4.1-mini, lessons/08_lmm 05-08, booth): artifacts/docs/l13_{plan,acc1,mission,fail,start}.log.
"남은 거리" / "visual dock" feedback lines are left out. Output: docs/camp/lesson13_cli_*.png
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

OUT = "docs/camp/"
P, O = "prompt", "out"
EX = "./scripts/robotworld exec python lessons/08_lmm/"


def log(name):
    return [t for t in Path(f"artifacts/docs/l13_{name}.log").read_text().splitlines()
            if "WARN" not in t and "남은 거리" not in t and not re.match(r"^(real|user|sys)\t", t)]


tm = [re.sub(r"^\[task_manager-\d+\] ", "", t) for t in Path("artifacts/docs/l13_start.log").read_text().splitlines() if "server ready" in t]
render([(P, "./scripts/robotworld start")] + [(O, "... (시뮬레이터 · Nav2 · MoveIt 로그 생략)")] + [(O, re.sub(r"\[\d+\.\d+\] ", "", t)) for t in tm],
       OUT + "lesson13_t2.png", highlight=("ExecutePlan server ready",))
render([(P, EX + "05_plan.py")] + [(O, t) for t in log("plan")], OUT + "lesson13_cli_plan.png", width=15.0, highlight=("validate_world", "(자동 추가)"))
render([(P, EX + "06_plan_accuracy.py")] + [(O, t) for t in log("acc1")], OUT + "lesson13_cli_plan_acc.png", width=15.0, highlight=("accuracy", " XX "))
m = [t for t in log("mission") if t.strip()]
k = m.index(">> plan:")
render([(P, EX + "08_text_mission.py \\"), (O, '  --lines "손님께 음료 가져다 드려" "2번 테이블" "응"')] + [(O, t) for t in m[:k]],
       OUT + "lesson13_cli_dialog.png", width=15.0, highlight=("robot]",))
render([(O, t) for t in m[k:] if not t.startswith("LLM cost")], OUT + "lesson13_cli_run.png", width=15.0, highlight=("/start]", "<< SUCCEEDED", "spoken", "robot]"))
render([(P, EX + "08_text_mission.py --lines \"분홍 컵을 음료대에서 1번 테이블로 옮겨\" \"응\"")] + [(O, t) for t in log("fail") if t.strip()],
       OUT + "lesson13_cli_fail.png", width=15.0, highlight=("<< ABORTED", "spoken", "robot]"))
