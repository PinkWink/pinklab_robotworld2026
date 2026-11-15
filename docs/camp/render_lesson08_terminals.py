"""Terminal figures of the MoveIt page from real runs in the booth (artifacts/docs/l08_*)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

A, OUT = Path("artifacts/docs"), Path("docs/camp")
P, O = "prompt", "out"
ENV = [(P, "source /opt/ros/jazzy/setup.bash"), (P, "source scripts/env.sh")]


def log(name):
    text = re.sub(r"\x1b\[[0-9;]*m", "", (A / name).read_text())
    lines = [l.rstrip() for l in text.splitlines() if l.strip() and "ROS_LOCALHOST_ONLY" not in l and "localhost_only" not in l]
    return [(O, re.sub(r"\] \[\d+\.\d+\]", "]", l).replace("/home/pw/mujoco_ros2/", "/home/pw/")[:165]) for l in lines]


def out(name, lines, **kw):
    render(lines, str(OUT / name), **kw); print("saved", name)


def pick(lines, *keys, n=None):
    sel = [l for l in lines if any(k in l[1] for k in keys)]
    return sel[:n] if n else sel


mv = log("l08_moveit.log")
out("lesson08_t1_moveit.png", ENV + [(P, "./scripts/robotworld moveit viewer:=true rviz:=true")] + pick(mv, "process started", n=6)
    + pick(mv, "Loading robot model", "Using planning interface", "Returned 4 controllers", "You can start planning now", "Vic Pinky + OpenArm ready", n=5),
    highlight=("You can start planning now", "move_group"), width=16.0)
out("lesson08_cli_nodes.png", ENV + [(P, "ros2 node list")] + log("l08_nodes.log") + [(P, "ros2 action list")] + log("l08_actions.log"),
    highlight=("/move_group", "/move_action", "follow_joint_trajectory", "gripper_cmd"))
out("lesson08_cli_actions.png", [(P, "ros2 action info /left_joint_trajectory_controller/follow_joint_trajectory")] + log("l08_action_info.log")
    + [(P, "ros2 service list | grep -E 'ik|cartesian|plan|scene' | grep -v warehouse_planning_scene/")] + log("l08_services.log"),
    highlight=("Action servers", "Action clients", "/compute_ik", "/compute_cartesian_path"))
ready = [(k, l) for k, l in log("l08_arm_ready.log") if "total" not in l]
total = re.search(r"([\d.]+) total", (A / "l08_arm_ready.log").read_text()).group(1)
out("lesson08_cli_arm.png", ENV + [(P, "time ./scripts/robotworld arm both ready")] + ready + [(O, f"real  {total} s"),
                                  (P, "./scripts/robotworld arm both hands_up")] + log("l08_arm_hands_up.log") + [(P, "./scripts/robotworld arm both transport")] + log("l08_arm_transport.log"),
    highlight=("error_code=1", "real"))
i = next(k for k, l in enumerate(mv) if "Received request" in l[1])
arm = [l for l in mv[i:i + 60] if any(k in l[1] for k in ("Received request", "Planning request received", "Combined planning", "Motion plan was computed", "sending trajectory", "started execution",
                                                           "Goal request accepted", "completed", "Completed trajectory execution", "Solution was found"))]
out("lesson08_t1_arm_log.png", [(O, "# 터미널 1 (moveit) 에 이어서 찍히는 줄: arm both ready")] + arm[:12], highlight=("Received request", "Completed trajectory execution", "sending trajectory"), width=17.0)
j = max(k for k, l in enumerate(mv) if "Received request" in l[1])
home = [l for l in mv[j:] if any(k in l[1] for k in ("sending trajectory", "Goal request accepted", "GOAL_TOLERANCE", "reports status ABORTED", "Completed trajectory execution", "CONTROL_FAILED"))]
out("lesson08_cli_home.png", [(P, "./scripts/robotworld arm both home")] + log("l08_arm_home.log") + [(O, ""), (O, "# 터미널 1 (moveit) 에 찍힌 줄")] + home[:9],
    highlight=("error_code=-4", "GOAL_TOLERANCE", "CONTROL_FAILED"), width=17.0)
