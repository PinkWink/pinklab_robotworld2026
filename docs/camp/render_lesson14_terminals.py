"""Terminal capture for the web FMS page (artifacts/docs/l18_fms.log from the 2026-11-16 session)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

lines = [l for l in re.sub(r"\x1b\[[0-9;]*m", "", Path("artifacts/docs/l18_fms.log").read_text()).splitlines() if l.strip() and "WARN" not in l]
head = [l for l in lines if "GET" not in l and "POST" not in l][:6]
reqs = [re.sub(r"^127.0.0.1 - - ", "", l)[:120] for l in lines if '"GET / ' in l or "api/stream" in l or "api/goal" in l or "api/chat" in l or "api/stop" in l]
seen, pick = set(), []
for l in reqs:
    key = re.search(r'"(GET|POST) (\S+)', l).group(2)
    if key not in seen:
        seen.add(key); pick.append(l)
render([("prompt", "./scripts/robotworld fms")] + [("out", l) for l in head + pick], "docs/camp/lesson14_t2.png", highlight=("FMS:", "POST"), width=14.0)
print("saved lesson14_t2.png")
