"""Terminal figures and the start screen of the avoidance page from real runs in the booth (artifacts/docs/l06_*)."""
import re
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

A, OUT = Path("artifacts/docs"), Path("docs/camp")
P, O = "prompt", "out"


def log(name):
    text = re.sub(r"\x1b\[[0-9;]*m", "", (A / name).read_text())
    lines = [l.rstrip() for l in text.splitlines() if l.strip() and "ROS_LOCALHOST_ONLY" not in l and "localhost_only" not in l]
    return [(O, re.sub(r"\] \[\d+\.\d+\]", "]", l)[:160]) for l in lines]


def out(name, lines, **kw):
    render(lines, str(OUT / name), **kw); print("saved", name)


out("lesson06_cli_crossing.png", [(P, "python docs/camp/avoid_scenario.py")] + log("l06_standing.log"), highlight=("SUCCEEDED", "closest"))
nav = [l for l in log("l06_nav.log") if "Failed to make progress" in l[1] or ("bt_navigator]" in l[1] and ("cancel" in l[1].lower() or "Begin navigating from current location (5.3" in l[1] or "Begin navigating from current location (5.1" in l[1]))]
out("lesson06_cli_headon.png", [(P, "python docs/camp/avoid_scenario.py --mode blocked --timeout 90")] + log("l06_blocked.log")
    + [(P, "python docs/camp/avoid_scenario.py --mode clear")] + log("l06_clear.log") + [(O, ""), (O, "# 터미널 1 (nav) 에 찍힌 줄")] + nav[:6],
    highlight=("CANCELED", "SUCCEEDED", "Failed to make progress"), width=16.0)
cv2.imwrite(str(OUT / "lesson06_run_result.png"), cv2.imread(str(A / "l06_rviz0.png"))); print("saved lesson06_run_result.png")
