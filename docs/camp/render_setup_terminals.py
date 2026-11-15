"""Terminal figures of the setup page from real logs in artifacts/docs (install.log, doctor.log, env.log)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

A, OUT = Path("artifacts/docs"), Path("docs/camp")


def lines(name):
    text = re.sub(r"\x1b\[[0-9;]*m", "", (A / name).read_text())
    text = text.replace("✅", "[OK]").replace("⚠️", "[!]").replace("❌", "[X]")
    return [l.rstrip() for l in text.splitlines() if not l.startswith("exit ")]


ins = lines("install.log")
start = max(i for i, l in enumerate(ins) if l.startswith("== build"))
tail = [l for l in ins[start:] if not l.startswith("Starting >>>")]
render([("prompt", "./scripts/install.sh"), ("out", "...")] + [("out", l) for l in tail], str(OUT / "setup_install_result.png"),
       highlight=("설치 완료", "Summary"))
doc = lines("doctor.log")
start = next(i for i, l in enumerate(doc) if l.startswith("== 빌드"))
render([("prompt", "./scripts/robotworld doctor"), ("out", "...")] + [("out", l) for l in doc[start:]], str(OUT / "setup_doctor_result.png"),
       highlight=("준비 완료",))
render([("prompt", "source scripts/env.sh")] + [("out", l.replace("/home/pw/mujoco_ros2/", "/home/pw/")) for l in lines("env.log")],
       str(OUT / "setup_env_sh_result.png"), highlight=("robotworld env",))
