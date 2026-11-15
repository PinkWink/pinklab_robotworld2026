"""Terminal figures of the patrol page from real runs in the booth (artifacts/docs/l07_*)."""
import json
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
    return [(O, re.sub(r"\] \[\d+\.\d+\]", "]", l).replace("/home/pw/mujoco_ros2/", "/home/pw/")[:160]) for l in lines]


def out(name, lines, **kw):
    render(lines, str(OUT / name), **kw); print("saved", name)


def pick(lines, *keys, n=None):
    sel = [l for l in lines if any(k in l[1] for k in keys)]
    return sel[:n] if n else sel


nav = log("l07_nav.log")
out("lesson07_t1_nav.png", ENV + [(P, "./scripts/robotworld nav moveit:=false")]
    + pick(nav, "process started", n=6) + pick(nav, "Loading yaml file", "RotationShimController", "Managed nodes are active", n=4),
    highlight=("booth.yaml", "RotationShimController", "Managed nodes are active"), width=16.0)
out("lesson07_cli_patrol.png", [(P, "python lessons/04_navigation/patrol.py")] + log("l07_patrol.log"), highlight=("patrol: done",))
out("lesson07_t1_goal_log.png", pick(nav, "Begin navigating", "Reached the goal", "Goal succeeded", n=12), title="터미널 1 (nav) — 순찰 중 로그", highlight=("Begin navigating",), width=16.0)
line = [l for l in (A / "l07_status.log").read_text().splitlines() if l.startswith("data:")][0]
out("lesson07_cli_status.png", [(P, "ros2 topic echo --once /patrol/status")] + [(O, line[i:i + 130]) for i in range(0, len(line), 130)] + [(O, "---")],
    highlight=("running",), width=16.0)
stuck = log("l07_nav_stuck.log")
i = next(k for k, l in enumerate(stuck) if "to (5.98, -5.53)" in l[1])
out("lesson07_t1_stuck.png", [l for l in stuck[i:i + 60] if any(k in l[1] for k in ("Begin navigating", "Failed to make progress", "Aborting handle", "Running", "Turning", "completed"))][:12],
    title="터미널 1 (nav) — 인포 → 입구 에서 멈출 때", highlight=("Failed to make progress", "Running"), width=16.0)
server = [l for l in log("l07_server.log") if "dashboard:" in l[1] or "Running on" in l[1] or "GET / " in l[1] or "api/command" in l[1] or "api/map.png" in l[1] or "mjpg" in l[1]]
out("lesson07_t2_server.png", [(P, "python lessons/04_navigation/dashboard/server.py")] + server[:9], title="터미널 2 — 대시보드 서버", highlight=("dashboard: http", "POST /api/command"), width=16.0)
out("lesson07_t3_patrol_wait.png", [(P, "python lessons/04_navigation/patrol.py --wait")] + log("l07_patrol_wait.log"), title="터미널 3 — 순찰 (시작 버튼 대기)", highlight=("patrol: done",))
stream = (A / "l07_api_stream.log").read_text()[:600].replace("\n", " ")
out("lesson07_cli_curl.png", [(P, "curl -s localhost:8080/api/cameras"), (O, (A / "l07_api_cameras.log").read_text().strip()[:150]),
                              (P, "curl -s -X POST -H \"Content-Type: application/json\" -d '{\"cmd\":\"start\"}' localhost:8080/api/command"),
                              (O, (A / "l07_api_start.log").read_text().strip()),
                              (P, "curl -s -N localhost:8080/api/stream | head -c 600")] + [(O, stream[i:i + 150]) for i in range(0, len(stream), 150)],
    title="터미널 4 — 브라우저 없이 API 보기", highlight=("\"ok\":true", "data: {"), width=16.0)
