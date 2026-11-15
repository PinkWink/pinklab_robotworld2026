"""Terminal figures and screen composites of the navigation page from real runs in the booth (artifacts/docs/l05_*)."""
import re
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

A, OUT = Path("artifacts/docs"), Path("docs/camp")
P, O = "prompt", "out"
ENV = [(P, "source /opt/ros/jazzy/setup.bash"), (P, "source scripts/env.sh"),
       (O, "robotworld env: domain 44, rmw rmw_cyclonedds_cpp, venv /home/pw/pinklab_robotworld2026/.venv")]


def log(name):
    text = re.sub(r"\x1b\[[0-9;]*m", "", (A / name).read_text())
    lines = [l.rstrip() for l in text.splitlines() if l.strip() and "ROS_LOCALHOST_ONLY" not in l and "localhost_only" not in l]
    return [(O, re.sub(r"\] \[\d+\.\d+\]", "]", l).replace("/home/pw/mujoco_ros2/", "/home/pw/")[:150]) for l in lines]


def out(name, lines, **kw):
    render(lines, str(OUT / name), **kw); print("saved", name)


def side(a, b, name):
    a, b = cv2.imread(str(A / a)), cv2.imread(str(A / b))
    cv2.imwrite(str(OUT / name), np.hstack([a, np.full((a.shape[0], 16, 3), 255, np.uint8), b])); print("saved", name)


nav = log("l05_nav.log")
start = [l for l in nav if "process started" in l[1]] + [l for l in nav if any(k in l[1] for k in ("Loading map", "initialPoseReceived", "Setting pose", "Managed nodes are active"))][:5]
out("lesson05_t1_nav.png", ENV + [(P, "./scripts/robotworld nav moveit:=false")] + start, highlight=("Managed nodes are active", "map_server", "amcl"), width=16.0)
out("lesson05_cli_nodes.png", ENV + [(P, "ros2 node list")] + log("l05_nodes.log"),
    highlight=("/amcl", "/bt_navigator", "/controller_server", "/planner_server", "/map_server", "/behavior_server", "/smoother_server"))
out("lesson05_cli_actions.png", [(P, "ros2 action list")] + log("l05_actions.log")
    + [(P, "for n in map_server amcl controller_server planner_server smoother_server behavior_server bt_navigator; do \\"),
       (O, '  echo "/$n: $(ros2 lifecycle get /$n)"; done')] + log("l05_lifecycle.log"), highlight=("/navigate_to_pose", "active [3]"))
goal = [l for l in log("l05_goal.log")]
goal = [(k, l) for k, l in goal if "total" not in l] + [(O, ""), (O, "real  " + re.search(r"([\d.]+) total", (A / "l05_goal.log").read_text()).group(1) + " s")]
out("lesson05_cli_goal.png", ENV + [(P, "time ./scripts/robotworld goal 7.43 -3.77 -1.15")] + goal, highlight=("SUCCEEDED", "real"))
bt = [l for l in nav if ("bt_navigator]" in l[1] and ("Begin navigating" in l[1] or "Goal succeeded" in l[1])) or ("controller_server]" in l[1] and ("Received a goal" in l[1] or "Reached the goal" in l[1] or "Passing" in l[1]))]
out("lesson05_t1_goal_log.png", [(O, "# 터미널 1 (nav) 에 이어서 찍히는 줄")] + bt[:8], highlight=("Begin navigating", "Reached the goal", "Goal succeeded"), width=16.0)
ip = [l for l in log("l05_initialpose.log")][:2]
ip = [(k, l[:120] + " ...") for k, l in ip]
g2 = [(k, l) for k, l in log("l05_goal2.log") if "total" not in l]
out("lesson05_cli_initialpose.png", [(P, "ros2 topic pub -1 /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \\"),
                                     (O, '  "{header: {frame_id: map}, pose: {pose: {position: {x: 5.9, y: -2.8}, orientation: {z: 0.1987, w: 0.9801}}, ...}}"')]
    + ip + [(P, "./scripts/robotworld goal 4.88 -3.02 2.77")] + g2, highlight=("SUCCEEDED", "publishing"), width=16.0)
side("l05_mj0.png", "l05_rviz0.png", "lesson05_run_result.png")
side("l05_mj_mid.png", "l05_rviz_mid.png", "lesson05_goal_mid.png")
side("l05_mj_after.png", "l05_rviz_after.png", "lesson05_goal_after.png")
for src, dst in (("l05_rviz_drag.png", "lesson05_rviz_goal_drag.png"), ("l05_rviz_goal_mid.png", "lesson05_rviz_goal_mid.png")):
    cv2.imwrite(str(OUT / dst), cv2.imread(str(A / src))); print("saved", dst)
