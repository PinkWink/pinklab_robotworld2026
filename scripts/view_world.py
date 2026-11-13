#!/usr/bin/env python3
"""Open the booth in the MuJoCo viewer (builds it first).

    python3 scripts/view_world.py
Camera views from the design file: in the viewer, Rendering -> Camera (bird1, main1, main2, north, west, studio, top).
"""
import sys
from pathlib import Path

import mujoco
import mujoco.viewer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/robotworld"))
from robotworld.world import build  # noqa: E402

if __name__ == "__main__":
    model = mujoco.MjModel.from_xml_path(str(build()))
    mujoco.viewer.launch(model)
