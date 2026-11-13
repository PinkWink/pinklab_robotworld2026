"""Screenshot the FMS page every `every` seconds with headless Chrome (DevTools protocol), wall time per frame.

    python3 video/browser_capture.py http://localhost:8080 artifacts/video/browser --every 0.5 --size 1600x1000
Writes f00000.png ... and times.json ([[index, wall_time], ...]) until SIGTERM / Ctrl+C.
"""
import argparse
import base64
import json
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, "/home/pw/mujoco_ros2/mobile_openarm_ws/docs/camp")      # tiny WebSocket client (read only)
from cdp_capture import WebSocket  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--every", type=float, default=0.5)
    ap.add_argument("--size", default="1600x1000")
    ap.add_argument("--port", type=int, default=9361)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    w, h = a.size.split("x")
    chrome = subprocess.Popen(["google-chrome", "--headless=new", f"--remote-debugging-port={a.port}", f"--user-data-dir={tempfile.mkdtemp(prefix='cdp_')}",
                               f"--window-size={w},{h}", "--hide-scrollbars", "--no-first-run", "--force-device-scale-factor=1", a.url],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    stop = []
    signal.signal(signal.SIGTERM, lambda *_: stop.append(1))
    signal.signal(signal.SIGINT, lambda *_: stop.append(1))
    times = []
    try:
        for _ in range(60):
            try:
                page = next(p for p in json.load(urllib.request.urlopen(f"http://127.0.0.1:{a.port}/json")) if p["type"] == "page")
                break
            except Exception:
                time.sleep(0.3)
        ws = WebSocket(page["webSocketDebuggerUrl"])
        mid = 0
        time.sleep(4)
        i = 0
        while not stop:
            t0 = time.time()
            mid += 1
            ws.send(json.dumps({"id": mid, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
            while True:
                m = json.loads(ws.recv())
                if m.get("id") == mid:
                    break
            (out / f"f{i:05d}.png").write_bytes(base64.b64decode(m["result"]["data"]))
            times.append([i, t0])
            i += 1
            time.sleep(max(0.0, a.every - (time.time() - t0)))
    finally:
        (out / "times.json").write_text(json.dumps(times))
        chrome.terminate()
        chrome.wait(timeout=5)
        print("frames", len(times), flush=True)


if __name__ == "__main__":
    main()
