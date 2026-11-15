"""Terminal figures of the SLAM page from real runs in the booth (artifacts/docs/l04_*.log, artifacts/dev/slam_tour.log)."""
import re
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

A, OUT = Path("artifacts/docs"), Path("docs/camp")
P, O = "prompt", "out"


def log(name, keep=None):
    text = re.sub(r"\x1b\[[0-9;]*m", "", (A / name).read_text())
    lines = [l.rstrip() for l in text.splitlines() if l.strip() and "ROS_LOCALHOST_ONLY" not in l and "localhost_only" not in l]
    lines = [re.sub(r"\] \[\d+\.\d+\]", "]", l).replace("/home/pw/mujoco_ros2/", "/home/pw/") for l in lines]
    return [(O, l[:150]) for l in (lines[:keep] if keep else lines)]


def out(name, lines, **kw):
    render(lines, str(OUT / name), **kw); print("saved", name)


slam = [l for l in log("l04_slam.log") if any(k in l[1] for k in ("process started", "slam_toolbox]: Configuring", "solver plugin", "is activating", "]: Activating",
                                                                   "Vic Pinky", "Registering sensor", "create a map"))]
out("lesson04_t1_slam.png", [(P, "source /opt/ros/jazzy/setup.bash"), (P, "source scripts/env.sh"),
                             (O, "robotworld env: domain 44, rmw rmw_cyclonedds_cpp, venv /home/pw/pinklab_robotworld2026/.venv"),
                             (P, "./scripts/robotworld slam")] + slam, highlight=("async_slam_toolbox_node-3]: process", "Registering sensor", "create a map"), width=16.0)
topics = [l for l in log("l04_topics.log") if re.search("map|slam|pose", l[1])]
out("lesson04_cli_nodes.png", [(P, "ros2 node list")] + log("l04_nodes.log") + [(P, "ros2 topic list | grep -E 'map|slam|pose'")] + topics, highlight=("/slam_toolbox", "/map"))
tf = log("l04_tf_map_odom.log")
i = next(k for k, l in enumerate(tf) if l[1].startswith("At time"))
out("lesson04_cli_tf_map_odom.png", [(P, "ros2 run tf2_ros tf2_echo map odom")] + tf[i:i + 5] + [(O, "^C")], highlight=("Translation", "degree"))
hz = [l for l in log("l04_map_hz.log") if "average rate" in l[1] or "min:" in l[1]][-4:]
out("lesson04_cli_map_info.png", [(P, "ros2 topic echo --once /map --field info")] + log("l04_map_info.log") + [(P, "ros2 topic hz /map")] + hz + [(O, "^C")],
    highlight=("resolution", "width", "height", "average rate"))
out("lesson04_t3_teleop.png", [(P, "./scripts/robotworld teleop"),
                               (O, "This node takes keypresses from the keyboard and publishes them"),
                               (O, "as Twist/TwistStamped messages. It works best with a US keyboard layout."),
                               (O, "---------------------------"), (O, "Moving around:"),
                               (O, "   u    i    o"), (O, "   j    k    l"), (O, "   m    ,    ."), (O, ""),
                               (O, "q/z : increase/decrease max speeds by 10%"),
                               (O, "w/x : increase/decrease only linear speed by 10%"),
                               (O, "e/c : increase/decrease only angular speed by 10%"), (O, ""),
                               (O, "CTRL-C to quit"), (O, ""), (O, "currently:\tspeed 0.25\tturn 0.50")],
    highlight=("u    i    o", "j    k    l", "m    ,    .", "currently"))
saver = [l for l in log("l04_map_saver.log") if any(k in l[1] for k in ("Saving map", "threshold", "Image format", "Received", "Writing", "saved successfully"))]
out("lesson04_cli_map_saver.png", [(P, "ros2 run nav2_map_server map_saver_cli -f artifacts/maps/my_booth")] + saver
    + [(P, "ls artifacts/maps"), (O, "  ".join(sorted(p.name for p in Path("artifacts/maps").iterdir()))), (P, "cat artifacts/maps/my_booth.yaml")]
    + [(O, l) for l in Path("artifacts/maps/my_booth.yaml").read_text().replace("free_thresh", "\nfree_thresh").splitlines() if l.strip()],
    highlight=("Received", "saved successfully", "origin", "resolution: 0.050"))
tour = [l for l in Path("artifacts/dev/slam_tour.log").read_text().splitlines() if l.startswith("waypoint") or "blocked" in l]
out("lesson04_cli_tour.png", [(P, "python docs/camp/slam_tour.py")] + [(O, l) for l in tour], highlight=("17/17",))
a, b = cv2.imread(str(A / "l04_mj0.png")), cv2.imread(str(A / "l04_rviz0.png"))
cv2.imwrite(str(OUT / "lesson04_run_result.png"), np.hstack([a, np.full((a.shape[0], 16, 3), 255, np.uint8), b])); print("saved lesson04_run_result.png")
cv2.imwrite(str(OUT / "lesson04_final_screen.png"), cv2.imread(str(A / "l04_rviz_final.png"))); print("saved lesson04_final_screen.png")
