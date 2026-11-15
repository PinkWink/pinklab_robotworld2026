"""Terminal captures for the lesson-12 (LLM + OpenAI API) page, rendered from the logs of real runs on 2026-11-15
(gpt-4.1-mini, lessons/08_lmm): artifacts/docs/l12_{hello,struct,acc1,cost}.log. Output: docs/camp/lesson12_cli_*.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

OUT = "docs/camp/"
P, O = "prompt", "out"
EX = "./scripts/robotworld exec python lessons/08_lmm/"


def log(name):
    lines = [t for t in Path(f"artifacts/docs/l12_{name}.log").read_text().splitlines() if "WARN" not in t]
    return [t.replace("9.400000000000001e-05", "9.4e-05") for t in lines]


render([(P, EX + "01_hello.py")] + [(O, t) for t in log("hello")], OUT + "lesson12_cli_hello.png", width=16.2, highlight=("robot:", "tokens:"))
render([(P, EX + "02_structured_command.py")] + [(O, t) for t in log("struct")], OUT + "lesson12_cli_struct.png", width=16.2,
       highlight=("rejected:", "world check", "answer (no robot action)"))
acc = log("acc1")
rows = [t for t in acc if " ok " in t[:8] or " XX " in t[:8]]
tail = acc[acc.index(next(t for t in acc if t.startswith("accuracy"))):]
render([(P, EX + "03_accuracy.py")] + [(O, t) for t in rows[:10]] + [(O, "   ... (ok 줄 생략)")] + [(O, t) for t in rows if " XX " in t[:8]] + [(O, "")]
       + [(O, t) for t in tail], OUT + "lesson12_cli_accuracy.png", highlight=(" XX ", "accuracy"))
render([(P, EX + "04_cost_log.py")] + [(O, t) for t in log("cost")], OUT + "lesson12_cli_cost.png", highlight=("command_parse", "total"))
