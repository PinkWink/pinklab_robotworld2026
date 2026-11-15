"""Terminal figures of the end-effector page from real runs in the booth (artifacts/docs/l09_*.log, made by l09_cli.sh)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

A, OUT = Path("artifacts/docs"), Path("docs/camp")
P, O = "prompt", "out"
EE = "./scripts/robotworld exec python lessons/05_moveit/ee_control.py"


def log(name, timed=False):
    text = re.sub(r"\x1b\[[0-9;]*m", "", (A / name).read_text())
    lines = [l.rstrip() for l in text.splitlines() if l.strip() and "ROS_LOCALHOST_ONLY" not in l and "localhost_only" not in l]
    body = [(O, l[:160]) for l in lines if not l.startswith(("real", "user", "sys"))]
    if timed:
        body += [(O, ""), (O, next(l for l in lines if l.startswith("real")).replace("\t", "  "))]
    return body


def out(name, lines, **kw):
    render(lines, str(OUT / name), **kw); print("saved", name)


mv = [(O, re.sub(r"\] \[\d+\.\d+\]", "]", l)[:160]) for l in re.sub(r"\x1b\[[0-9;]*m", "", (A / "l09_moveit.log").read_text()).splitlines()
      if any(k in l for k in ("process started", "You can start planning now", "Vic Pinky + OpenArm ready"))]
out("lesson09_t1_moveit.png", [(P, "./scripts/robotworld moveit viewer:=true rviz:=true")] + mv[:8], highlight=("You can start planning now",), width=16.0)
out("lesson09_cli_where.png", [(P, f"{EE} where")] + log("l09_where.log") + [(P, f"{EE} named both ready")] + log("l09_named.log"), highlight=("TCP",), width=16.0)
out("lesson09_cli_ik.png", [(P, f"{EE} ik left 0.45 0.20 0.95")] + log("l09_ik.log"), highlight=("IK for",), width=16.0)
out("lesson09_cli_pose.png", [(P, f"time {EE} pose left 0.45 0.20 0.95")] + log("l09_pose.log", True), highlight=("reached", "real"), width=16.0)
out("lesson09_cli_cart.png", [(P, f"time {EE} cartesian left 0 0 -0.05")] + log("l09_cart.log", True), highlight=("followed", "real"), width=16.0)
out("lesson09_cli_gripper.png", [(P, f"{EE} gripper left close")] + log("l09_grip_close.log") + [(P, f"{EE} gripper left open")] + log("l09_grip_open.log"), highlight=("finger at",), width=16.0)
out("lesson09_cli_fail.png", [(P, f"{EE} pose left 0.65 0.20 0.95")] + log("l09_fail_pose.log") + [(P, f"{EE} cartesian left 0.3 0 0")] + log("l09_fail_cart.log"), highlight=("error:",), width=16.0)
out("lesson09_cli_demo.png", [(P, f"time {EE} demo")] + log("l09_demo.log", True), highlight=("reached", "followed", "real"), width=16.0)
