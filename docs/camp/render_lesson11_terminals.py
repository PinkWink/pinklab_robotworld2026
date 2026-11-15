"""Terminal figures of the navigation + pick-and-place page from real runs in the booth (artifacts/docs/l11_*.log)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

A, OUT = Path("artifacts/docs"), Path("docs/camp")
P, O = "prompt", "out"
TR = "./scripts/robotworld exec python lessons/07_nav_pick_place/transport.py"


def log(name):
    text = re.sub(r"\x1b\[[0-9;]*m", "", (A / name).read_text())
    return [re.sub(r"\] \[\d+\.\d+\]", "]", l.rstrip())[:165] for l in text.splitlines() if l.strip() and "ROS_LOCALHOST_ONLY" not in l and "localhost_only" not in l]


def out(name, lines, **kw):
    render(lines, str(OUT / name), **kw); print("saved", name)


def thin(lines):
    """Drop the repeated 'visual dock' detail lines (keep the first and the last of each run)."""
    keep = []
    for i, l in enumerate(lines):
        if "visual dock:" in l and keep and "visual dock:" in keep[-1] and i + 1 < len(lines) and "visual dock:" in lines[i + 1]:
            continue
        keep.append(l)
    return keep


def real(name):
    m = re.search(r"([\d:.]+) total", (A / name).read_text())
    return f"real  {m.group(1)}" if m else ""


start = [l for l in log("l11_start.log") if any(k in l for k in ("process started", "Loading yaml file", "Managed nodes are active", "You can start planning now", "PickPlace server ready"))]
out("lesson11_t1.png", [(P, "./scripts/robotworld start viewer:=true rviz:=true")] + [(O, l) for l in start[:18]],
    highlight=("booth.yaml", "PickPlace server ready", "Managed nodes are active", "You can start planning now"), width=16.0)
pink = thin([l for l in log("l11_pink.log") if "total" not in l or l.strip().startswith("total")])
k = next(i for i, l in enumerate(pink) if "] navigate_place" in l)
s = next(i for i, l in enumerate(pink) if l.strip().startswith("phase "))
out("lesson11_cli_pick.png", [(P, f"time {TR} pink")] + [(O, l) for l in pink[:k]], highlight=("] navigate_pick", "] dock", "] locate", "] carry", "holding at", "docked:"), width=17.0)
out("lesson11_cli_place.png", [(O, l) for l in pink[k:s]], highlight=("] navigate_place", "] dock", "] place", "] retreat", "<< SUCCEEDED", "docked:"), width=17.0)
out("lesson11_cli_summary.png", [(O, l) for l in pink[s:]] + [(O, ""), (O, real("l11_pink.log"))], highlight=("navigate_pick", "navigate_place", "total", "real"), width=14.0)
yel = thin([l for l in log("l11_yellow.log") if "total" not in l or l.strip().startswith("total")])
sy = next(i for i, l in enumerate(yel) if l.strip().startswith("phase "))
head = [l for l in yel[:sy] if l.lstrip().startswith("[") or any(k in l for k in ("sits", "arm", "side-step", "docked:", "holding at", "slot at", "<<"))]
out("lesson11_cli_yellow.png", [(P, f"time {TR} yellow --to consult_1")] + [(O, l) for l in head[:26]] + [(O, l) for l in yel[sy + 12:sy + 13]] + [(O, real("l11_yellow.log"))],
    highlight=("arm", "side-step", "<< SUCCEEDED", "total", "real"), width=17.0)
