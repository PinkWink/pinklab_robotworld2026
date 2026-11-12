#!/usr/bin/env python3
"""Refresh booth/ from the booth design HTML (the single-file 3D page built by build_fp.py).

    python3 tools/extract_booth_html.py "<핑크랩_로보월드2026_부스_3D_최종.html>"

Writes booth/booth_data.json (window.BOOTH, evaluated with node), booth/images/* (embedded graphics, logos,
monitor screens, QR codes) and booth/floorplan.png. Needs node (only to read the JS object literal).
"""
import base64
import io
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
NAMES = {  # (variable, key) in the HTML -> file name here
    ("GFX", f"g{i}"): f"g{i}.jpg" for i in range(1, 7)
} | {("MON_IMG", "c2"): "monitor_c2.jpg", ("MON_IMG", "ph"): "monitor_ph.jpg", ("MON_IMG", "pl"): "monitor_pl.jpg",
     ("TV_IMG", "src"): "tv.jpg", ("QR_IMG", "home"): "qr_home.png", ("QR_IMG", "yt"): "qr_yt.png",
     ("PINKLAB_LOGO", "h"): "logo_h.png", ("PINKLAB_LOGO", "v"): "logo_v.png", ("CURR_IMG", "src"): "curriculum.png"}


def main():
    html = Path(sys.argv[1]).read_text(encoding="utf-8")
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    data = next(s for s in scripts if s.startswith("/* booth_fp_data.js */"))
    js = "const window={};" + data + ";process.stdout.write(JSON.stringify(window.BOOTH,null,1))"
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout
    (ROOT / "booth/booth_data.json").write_text(out + "\n")
    images = ROOT / "booth/images"
    images.mkdir(parents=True, exist_ok=True)
    found = {}
    for s in scripts:
        for m in re.finditer(r"window\.(\w+)(?:\.(\w+))?\s*=\s*(\{.*?\}|'[^']*'|\"[^\"]*\")\s*;", s, re.S):
            var, sub, body = m.groups()
            if sub:                                             # window.GFX.g5 = '...'  (a later override wins)
                pairs = [(sub, body)]
            else:
                pairs = re.findall(r"(\w+)\s*:\s*(?:\{[^{}]*?src:\s*)?['\"](data:image[^'\"]+)['\"]", body)
                if not pairs and "data:image" in body:
                    pairs = [("src", re.search(r"(data:image[^'\"]+)", body).group(1))]
            for key, uri in pairs:
                uri = uri.strip("'\"")
                if (var, key) in NAMES and uri.startswith("data:image"):
                    found[(var, key)] = uri
    for (var, key), uri in found.items():
        raw = base64.b64decode(uri.split(",", 1)[1])
        name = NAMES[(var, key)]
        if name.endswith(".png"):
            Image.open(io.BytesIO(raw)).save(images / name)
        else:
            (images / name).write_bytes(raw)
    plan = re.search(r"getElementById\('imgPlan'\)\.src\s*=\s*'(data:image[^']+)'", html)
    if plan:
        (ROOT / "booth/floorplan.png").write_bytes(base64.b64decode(plan.group(1).split(",", 1)[1]))
    print(f"booth_data.json + {len(found)} images", sorted(NAMES[k] for k in found))


if __name__ == "__main__":
    main()
