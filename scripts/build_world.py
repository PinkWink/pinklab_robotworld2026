#!/usr/bin/env python3
"""Build the booth world: artifacts/world/booth.xml + artifacts/world/textures/*.png

    python3 scripts/build_world.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/robotworld"))
from robotworld.world import build  # noqa: E402

if __name__ == "__main__":
    print("saved", build())
