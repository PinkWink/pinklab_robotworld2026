"""Terminal figures of the description page from real runs. Logs: artifacts/docs/l02_*.log (see artifacts/docs/l02_cli.sh).
Run: ./scripts/robotworld exec python3 docs/camp/render_lesson02_terminals.py"""
import collections
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

A, OUT = Path("artifacts/docs"), Path("docs/camp")
ENV = [("prompt", "source /opt/ros/jazzy/setup.bash"), ("prompt", "source scripts/env.sh"),
       ("out", "robotworld env: domain 44, rmw rmw_cyclonedds_cpp, venv /home/pw/pinklab_robotworld2026/.venv")]


def log(name, keep=None, drop=("ROS_LOCALHOST_ONLY", "localhost_only")):
    text = re.sub(r"\x1b\[[0-9;]*m", "", (A / name).read_text())
    lines = [l.rstrip() for l in text.splitlines() if l.strip() and not any(d in l for d in drop)]
    lines = [re.sub(r"found below .*?/log/", "found below …/log/", l).replace("/home/pw/mujoco_ros2/", "/home/pw/") for l in lines]
    return [("out", l[:150]) for l in (lines[:keep] if keep else lines)]


def out(name, lines, **kw):
    render(lines, str(OUT / name), **kw); print("saved", name)


def launch(name):
    return [l for l in log(name) if "process started" in l[1] or "Robot initialized" in l[1] or "Got description" in l[1] or "log files" in l[1]]


out("lesson02_t1_vicpinky.png", ENV + [("prompt", "ros2 launch vicpinky_description display.launch.py")] + launch("l02_vicpinky.log"), highlight=("Robot initialized", "Got description"))
out("lesson02_t1_openarm.png", ENV + [("prompt", "ros2 launch openarm_description display.launch.py")] + launch("l02_openarm.log"), highlight=("Robot initialized", "Got description"))
out("lesson02_t1_display.png", ENV + [("prompt", "./scripts/robotworld display")] + launch("l02_display.log"), highlight=("Robot initialized", "Got description"))
out("lesson02_cli_node_list.png", ENV + [("prompt", "ros2 node list")] + log("l02_nodes.log"), highlight=("/robot_state_publisher", "/joint_state_publisher"))
out("lesson02_cli_topic_info.png", [("prompt", "ros2 topic list")] + log("l02_topics.log") + [("prompt", "ros2 topic info /robot_description")] + log("l02_info.log"),
    highlight=("/joint_states", "/robot_description", "/tf"))
js = [l for l in log("l02_js.log")]
names = [l for l in js if l[1].startswith("- ")][:20]
out("lesson02_cli_joint_states.png", [("prompt", "ros2 topic echo --once /joint_states")] + js[:js.index(names[0])] + names + [("out", "position: [...]   # 20 개")],
    highlight=("name:",))
for src, dst, cmd in (("l02_tf_tcp.log", "lesson02_cli_tf_echo.png", "base_footprint openarm_left_hand_tcp"), ("l02_tf_laser.log", "lesson02_cli_tf_laser.png", "base_link laser_link")):
    tf = log(src)
    i = next(k for k, l in enumerate(tf) if l[1].startswith("At time"))
    out(dst, [("prompt", f"ros2 run tf2_ros tf2_echo {cmd}")] + tf[i:i + 9], highlight=("Translation", "Quaternion"))
gen = sorted(p.name for p in Path("artifacts/mobile_generated").iterdir())
listing = subprocess.run("ls artifacts/mobile_generated/ | column -c 140", shell=True, capture_output=True, text=True).stdout.expandtabs(8).splitlines()
head = Path("artifacts/mobile_generated/warehouse.xml").read_text()[:400].split(">")[:3]
out("lesson02_cli_generated.png", [("prompt", "ls artifacts/mobile_generated/")] + [("out", l) for l in listing]
    + [("prompt", "ls artifacts/mobile_generated/ | wc -l"), ("out", str(len(gen)))], highlight=("robot.urdf", "warehouse.xml"), width=16.0)
urdf = ET.parse("artifacts/mobile_generated/robot.urdf").getroot()
m = mujoco.MjModel.from_xml_path("artifacts/mobile_generated/warehouse.xml")
l1 = f"URDF link {len(urdf.findall('link'))} {dict(collections.Counter(j.get('type') for j in urdf.findall('joint')))}"
l2 = f"MJCF body {m.nbody} joint {m.njnt} geom {m.ngeom} camera {m.ncam} actuator {m.nu} exclude {m.nexclude} equality {m.neq}"
print(l1); print(l2)
free = [m.joint(i).name for i in range(m.njnt) if m.jnt_type[i] == 0]
print("free joints", free, "mocap", m.nmocap)
out("lesson02_cli_counts.png", [("prompt", "python - <<'EOF'  ...  EOF"), ("out", l1), ("out", l2)], highlight=("URDF", "MJCF"))
