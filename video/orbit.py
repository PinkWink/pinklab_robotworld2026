"""Clean booth orbit clip (no text): the camera goes once around the booth; nothing in the scene moves.

    MUJOCO_GL=egl ./scripts/robotworld exec python video/orbit.py artifacts/video/pinklab_booth_orbit.mp4 [--seconds 20] [--size 1920x1080]
Uses the recorded run only for the robot's resting pose (first sample), so the scene matches the intro video.
"""
import argparse
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from replay import Replay  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=str(ROOT / "artifacts/video/pinklab_booth_orbit.mp4"))
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()
    w, h = map(int, a.size.split("x"))
    rp = Replay(ROOT / "artifacts/video/run.pkl", size=(w, h))
    t = rp.t_begin + 2.0
    n = round(a.seconds * a.fps)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(a.fps), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out],
                          stdin=subprocess.PIPE)
    for i in range(n):
        u = i / n                                                   # one full turn, seamless loop (last frame != first)
        shot = dict(mode="fixed", lookat=[4.5, -3.0, 1.1], distance=10.8 + 0.6 * math.cos(2 * math.pi * u),
                    azimuth=-60 + 360 * u, elevation=-21 - 6 * math.sin(2 * math.pi * u))
        ff.stdin.write(rp.render(t, shot).convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    print("saved", a.out, f"({n} frames)", flush=True)


if __name__ == "__main__":
    main()
