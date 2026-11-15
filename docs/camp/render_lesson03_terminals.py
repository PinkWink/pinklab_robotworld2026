"""Terminal figures of the sensors / TF / odom page from real runs (artifacts/docs/l03_*.log, made by l03_cli.sh · l03_hz.sh)."""
import glob
import re
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

A, OUT = Path("artifacts/docs"), Path("docs/camp")
ENV = [("prompt", "source /opt/ros/jazzy/setup.bash"), ("prompt", "source scripts/env.sh"),
       ("out", "robotworld env: domain 44, rmw rmw_cyclonedds_cpp, venv /home/pw/pinklab_robotworld2026/.venv")]


def log(name, keep=None):
    text = re.sub(r"\x1b\[[0-9;]*m", "", (A / name).read_text())
    lines = [l.rstrip() for l in text.splitlines() if l.strip() and "ROS_LOCALHOST_ONLY" not in l and "localhost_only" not in l]
    lines = [re.sub(r"found below .*?/log/", "found below …/log/", l).replace("/home/pw/mujoco_ros2/", "/home/pw/") for l in lines]
    return [("out", l[:150]) for l in (lines[:keep] if keep else lines)]


def out(name, lines, **kw):
    render(lines, str(OUT / name), **kw); print("saved", name)


drive = [l for l in log("l03_drive.log") if "Stereo" not in l[1] and "OpenGl" not in l[1] and "verbosity" not in l[1]]
out("lesson03_t1_drive.png", ENV + [("prompt", "./scripts/robotworld drive")] + drive[:9], highlight=("Vic Pinky + OpenArm ready", "[sim_config] profile"), width=16.0)
out("lesson03_cli_nodes_topics.png", ENV + [("prompt", "ros2 node list")] + log("l03_nodes.log") + [("prompt", "ros2 topic list")] + log("l03_topics.log"),
    highlight=("/scan", "/odom", "/joint_states", "/clock", "/tf", "/cmd_vel", "/mobile_openarm_mujoco"))
scan = log("l03_scan.log")
i = next(k for k, l in enumerate(scan) if l[1].startswith("ranges:"))
out("lesson03_cli_scan.png", [("prompt", "ros2 topic echo --once /scan")] + scan[:i + 6] + [("out", "...")], highlight=("frame_id", "angle_increment", "range_max"))
out("lesson03_cli_scan_probe.png", [("prompt", "python docs/camp/scan_probe.py")] + log("l03_probe.log"), highlight=("ranges:",), width=16.0)
hz = []
for t in ("scan", "odom", "joint_states", "clock"):
    hz += [("prompt", f"ros2 topic hz /{t}")] + [l for l in log(f"l03_hz_{t}.log") if "average rate" in l[1]][-1:]
for t in ("scan", "odom", "joint_states"):
    hz += [("prompt", f"ros2 topic hz --use-sim-time /{t}")] + [l for l in log(f"l03_hzsim_{t}.log") if "average rate" in l[1]][-1:]
out("lesson03_cli_hz.png", hz, highlight=("average rate",))
odom = log("l03_odom.log")
i = next(k for k, l in enumerate(odom) if l[1].strip().startswith("covariance"))
out("lesson03_cli_odom.png", [("prompt", "ros2 topic echo --once /odom")] + odom[:i] + [("out", "  covariance: ...")], highlight=("frame_id", "child_frame_id"))
tf = log("l03_tf_odom.log")
i = next(k for k, l in enumerate(tf) if l[1].startswith("At time"))
out("lesson03_cli_tf_odom.png", [("prompt", "ros2 run tf2_ros tf2_echo odom base_footprint")] + tf[i:i + 9], highlight=("Translation", "Quaternion"))
out("lesson03_cli_truth.png", [("prompt", "ros2 topic echo --once /ground_truth")] + log("l03_truth.log"), highlight=("frame_id", "x:", "y:"))
# TF tree: the top of the view_frames PDF (pdftoppm -r 150), centred on the root
img = cv2.imread(glob.glob(str(A / "l03_frames*.png"))[0])
gray = cv2.cvtColor(img[:300], cv2.COLOR_BGR2GRAY)
xs = (gray < 200).any(axis=0).nonzero()[0]
cx = int((xs.min() + xs.max()) / 2)
crop = img[0:1650, max(0, cx - 2900):cx + 2900]
cv2.imwrite(str(OUT / "lesson03_tf_tree_top.png"), cv2.resize(crop, None, fx=0.36, fy=0.36, interpolation=cv2.INTER_AREA)); print("saved lesson03_tf_tree_top.png")
rv = cv2.imread(str(A / "l03_rviz.png"))
cv2.imwrite(str(OUT / "lesson03_rviz_scan.png"), rv); print("saved lesson03_rviz_scan.png")

exp = log("l03_exp1.log") + [("prompt", "python docs/camp/odom_experiment.py --side 1.0 --laps 3 --out artifacts/dev/odom_square3")] + log("l03_exp3.log")
exp = [(k, l.replace("  final", "\n  final").replace("  truth", "\n  truth").replace("  pos error", "\n  pos error")) for k, l in exp]
flat = []
for k, l in exp:
    flat += [(k, part) for part in l.split("\n")]
out("lesson03_cli_experiment.png", [("prompt", "./scripts/robotworld drive spawn:=5.0,-3.7,0        # 터미널 1"),
                                     ("prompt", "python docs/camp/odom_experiment.py --side 1.0 --laps 1 --out artifacts/dev/odom_square1")] + flat, highlight=("pos error",))
tr = [l for l in log("l03_spawn_truth.log") if l[1].strip().startswith(("frame_id", "x:", "y:"))][:3]
od = [l for l in log("l03_spawn_odom.log") if l[1].strip().startswith(("frame_id", "child_frame_id", "x:", "y:"))][:4]
out("lesson03_cli_spawn.png", [("prompt", "ros2 topic echo --once /ground_truth")] + tr + [("prompt", "ros2 topic echo --once /odom")] + od, highlight=("x:", "y:"))
a = cv2.imread(str(A / "l03_sq_before.png"))[:, 270:1130]; b = cv2.imread(str(A / "l03_sq_after.png"))[:, 270:1130]
import numpy as np
cv2.imwrite(str(OUT / "lesson03_square1_motion.png"), np.hstack([a, np.full((a.shape[0], 16, 3), 255, np.uint8), b])); print("saved lesson03_square1_motion.png")
