"""Terminal figures of the pick-and-place page from real runs in the booth (artifacts/docs/l10_*.log)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

A, OUT = Path("artifacts/docs"), Path("docs/camp")
P, O = "prompt", "out"
PY = "./scripts/robotworld exec python lessons/06_pick_place/pick_then_place.py"


def log(name):
    text = re.sub(r"\x1b\[[0-9;]*m", "", (A / name).read_text())
    lines = [l.rstrip() for l in text.splitlines() if l.strip() and "ROS_LOCALHOST_ONLY" not in l and "localhost_only" not in l]
    return [re.sub(r"\] \[\d+\.\d+\]", "]", l)[:165] for l in lines]


def out(name, lines, **kw):
    render(lines, str(OUT / name), **kw); print("saved", name)


def dedupe(lines):
    """Keep the first and last of the repeated 'visual dock' feedback lines."""
    keep = []
    for i, l in enumerate(lines):
        if "visual dock:" in l and i + 1 < len(lines) and "visual dock:" in lines[i + 1] and keep and "visual dock:" in keep[-1]:
            continue
        keep.append(l)
    return keep


start = [l for l in log("l10_start.log") if any(k in l for k in ("process started", "Managed nodes are active", "You can start planning now", "PickPlace server ready", "Vic Pinky"))]
out("lesson10_t1.png", [(P, "./scripts/robotworld start spawn:=drinks viewer:=true rviz:=false")] + [(O, l) for l in start[:16]],
    highlight=("Managed nodes are active", "You can start planning now", "PickPlace server ready"), width=16.0)
run = dedupe([l for l in log("l10_pick.log") if "total" not in l])
k = next(i for i, l in enumerate(run) if l.startswith(">> PickPlace phase=place"))
out("lesson10_cli_pick.png", [(P, f"time {PY} pink")] + [(O, l) for l in run[:k]], highlight=("<< SUCCEEDED", "holding at", "docked:"), width=17.0)
total = re.search(r"([\d:.]+) total", (A / "l10_pick.log").read_text()).group(1)
out("lesson10_cli_place.png", [(O, l) for l in run[k:]] + [(O, ""), (O, f"real  {total}")], highlight=("<< SUCCEEDED", "released", "docked:"), width=17.0)
out("lesson10_cli_fail.png", [(P, f"{PY} pink --only place")] + [(O, l) for l in log("l10_fail.log")], highlight=("nothing is held",), width=16.0)
cli = [l for l in log("l10_cli_pick.log")][-4:] 
cli2 = [l for l in log("l10_cli_place.log")][-4:]
out("lesson10_cli_cli.png", [(P, "./scripts/robotworld pick pink --phase pick")] + [(O, "...")] + [(O, l) for l in cli]
    + [(P, "./scripts/robotworld pick pink drinks drinks --phase place")] + [(O, "...")] + [(O, l) for l in cli2], highlight=("success=True",), width=17.0)
