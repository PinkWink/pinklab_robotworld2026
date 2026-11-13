#!/usr/bin/env python3
"""Nav2 map of the booth, straight from the MuJoCo model (stands in for a finished SLAM map).

    ./scripts/robotworld exec python scripts/generate_booth_map.py      # -> src/mobile_openarm_navigation/maps/booth.{pgm,yaml}

Occupied = static solid geoms (group 0, colliding) between 0.03 and 1.6 m: walls, furniture with their full table
tops, the round pole, neighbour booths. Left out: people (they move, the costmap sees them), cups, the robot.
"""
import argparse
from pathlib import Path

import mujoco
import numpy as np

from mobile_openarm_mujoco.model import build_model

RES = 0.05
X0, Y0, X1, Y1 = -1.5, -7.5, 10.5, 1.5           # booth X 0..9, Y -6..0 plus the aisles around it
OUT = Path(__file__).resolve().parents[1] / "src/mobile_openarm_navigation/maps"


def occupancy(model, data):
    W, H = round((X1 - X0) / RES), round((Y1 - Y0) / RES)
    gx, gy = np.meshgrid(X0 + (np.arange(W) + 0.5) * RES, Y0 + (np.arange(H) + 0.5) * RES)
    occ = np.zeros((H, W), bool)
    robot_root = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "base_footprint")
    for g in range(model.ngeom):
        b = model.geom_bodyid[g]
        if model.geom_group[g] != 0 or model.geom_contype[g] == 0 or model.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE:
            continue
        if model.body_mocapid[b] >= 0 or model.body_rootid[b] == robot_root or model.body_jntnum[b] > 0:
            continue                                   # people, the robot, free objects (cups)
        R = data.geom_xmat[g].reshape(3, 3)
        c = data.geom_xpos[g] + R @ model.geom_aabb[g][:3]
        ext = np.abs(R) @ model.geom_aabb[g][3:]
        if c[2] + ext[2] < 0.03 or c[2] - ext[2] > 1.6:
            continue
        t, size = model.geom_type[g], model.geom_size[g]
        if t == mujoco.mjtGeom.mjGEOM_BOX:
            dx, dy = gx - data.geom_xpos[g][0], gy - data.geom_xpos[g][1]
            lx, ly = dx * R[0, 0] + dy * R[1, 0], dx * R[0, 1] + dy * R[1, 1]
            occ |= (np.abs(lx) <= size[0] + RES / 2) & (np.abs(ly) <= size[1] + RES / 2)
        elif t == mujoco.mjtGeom.mjGEOM_CYLINDER:
            occ |= np.hypot(gx - data.geom_xpos[g][0], gy - data.geom_xpos[g][1]) <= size[0] + RES / 2
        else:
            occ |= (np.abs(gx - c[0]) <= ext[0] + RES / 2) & (np.abs(gy - c[1]) <= ext[1] + RES / 2)
    return occ


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT / "booth"))
    a = ap.parse_args()
    model = mujoco.MjModel.from_xml_path(str(build_model("artifacts/map_model")))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    occ = occupancy(model, data)
    img = np.where(occ, 0, 254).astype(np.uint8)[::-1]          # PGM row 0 = top = max y
    out = Path(a.out)
    with open(out.with_suffix(".pgm"), "wb") as f:
        f.write(f"P5\n{img.shape[1]} {img.shape[0]}\n255\n".encode())
        f.write(img.tobytes())
    out.with_suffix(".yaml").write_text(
        f"image: {out.with_suffix('.pgm').name}\nmode: trinary\nresolution: {RES}\norigin: [{X0}, {Y0}, 0.0]\n"
        "negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n")
    print(f"saved {out.with_suffix('.pgm')} ({img.shape[1]} x {img.shape[0]}, {occ.mean() * 100:.1f} % occupied)")


if __name__ == "__main__":
    main()
