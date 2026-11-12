#!/usr/bin/env python3
"""Render the design file's named views offscreen: build/views/<key>.png

    MUJOCO_GL=egl python3 scripts/render_views.py            # all views
    MUJOCO_GL=egl python3 scripts/render_views.py bird1 top
"""
import sys
from pathlib import Path

import mujoco
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from robotworld.world import build, load  # noqa: E402

if __name__ == "__main__":
    model = mujoco.MjModel.from_xml_path(str(build()))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    out = ROOT / "build/views"
    out.mkdir(parents=True, exist_ok=True)
    keys = sys.argv[1:] or [v["key"] for v in load()["views"]]
    renderer = mujoco.Renderer(model, 1080, 1920)
    for key in keys:
        renderer.update_scene(data, camera=key)
        Image.fromarray(renderer.render()).save(out / f"{key}.png")
        print("saved", out / f"{key}.png")
    renderer.close()
