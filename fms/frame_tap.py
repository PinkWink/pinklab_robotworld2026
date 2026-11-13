"""Camera handler for the FMS: the usual pipeline (ArUco for docking + truth labels) and, only while the browser asks
for it, the newest JPEG per camera in shared memory.

The FMS server switches streaming on and off by creating / removing FRAMES/enabled. Off (the default) costs nothing
extra: the cameras are rendered anyway for docking, but nothing is encoded or written.
Loaded by the launch file as camera_handler:=fms/frame_tap.py:FmsPipeline (the default in this repository).
"""
import json
import os
from pathlib import Path

import cv2

from warehouse_lecture.vision.pipeline import LecturePipeline

FRAMES = Path(os.environ.get("ROBOTWORLD_FRAMES", "/dev/shm/robotworld_fms"))


class FmsPipeline(LecturePipeline):
    def setup(self, context):
        super().setup(context)
        FRAMES.mkdir(parents=True, exist_ok=True)

    def __call__(self, frames):
        super().__call__(frames)                         # docking markers and labels first
        if not (FRAMES / "enabled").exists():
            return
        meta = {}
        for name, frame in frames.items():
            ok, jpg = cv2.imencode(".jpg", cv2.cvtColor(frame.rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                continue
            tmp = FRAMES / f".{name}.jpg.tmp"
            tmp.write_bytes(jpg.tobytes())
            os.replace(tmp, FRAMES / f"{name}.jpg")       # atomic: the server never reads half a file
            meta[name] = dict(sim_time=frame.sim_time, width=frame.rgb.shape[1], height=frame.rgb.shape[0])
        tmp = FRAMES / ".meta.json.tmp"
        tmp.write_text(json.dumps(meta))
        os.replace(tmp, FRAMES / "meta.json")
