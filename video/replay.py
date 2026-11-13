"""Offline re-render of a recorded run (video/record.py pickle) in the booth, at any frame rate and camera.

    from replay import Replay
    rp = Replay("artifacts/video/run.pkl", size=(1920, 1080))
    img = rp.render(t, dict(mode="track", offset_body=[0.4, 0, 0.8], distance=2.4, azimuth=150, elevation=-18, follow_heading=True))
    img = rp.render(t, dict(mode="fixed", lookat=[4.5, -3, 1.2], distance=12, azimuth=-60, elevation=-22))
Joints, base pose and cups are interpolated between samples. The scene is the same generated model the simulator ran
(artifacts/mobile_generated/warehouse.xml = robot + booth), rendered with shadows and 8x multisampling.
"""
import pickle
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image

WS = Path(__file__).resolve().parents[1]


def series(rows, key):
    t = np.array([r["t"] for r in rows])
    v = np.array([r[key] for r in rows], float)
    o = np.argsort(t, kind="stable")
    return t[o], v[o]


def lerp(ts, vs, t):
    i = int(np.clip(np.searchsorted(ts, t), 1, len(ts) - 1))
    t0, t1 = ts[i - 1], ts[i]
    a = 0.0 if t1 <= t0 else float(np.clip((t - t0) / (t1 - t0), 0, 1))
    return vs[i - 1] * (1 - a) + vs[i] * a


def wxyz(row):
    """pose rows are (x y z qx qy qz qw); MuJoCo wants w first."""
    q = np.array([row[6], row[3], row[4], row[5]])
    return q / np.linalg.norm(q)


class Replay:
    def __init__(self, pkl, size=(1920, 1080), model=WS / "artifacts/mobile_generated/warehouse.xml"):
        self.run = pickle.load(open(pkl, "rb"))
        w, h = size
        spec = mujoco.MjSpec.from_file(str(model))
        spec.visual.global_.offwidth = max(w, 1000)
        spec.visual.global_.offheight = max(h, 1000)
        spec.visual.quality.offsamples = 8
        spec.visual.quality.shadowsize = 8192
        self.m = spec.compile()
        self.d = mujoco.MjData(self.m)
        self.r = mujoco.Renderer(self.m, h, w)
        self.opt = mujoco.MjvOption()
        self.opt.geomgroup[1] = 0                          # hide collision shapes
        self.cam = mujoco.MjvCamera()
        self.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        run = self.run
        names = run["states"][0]["names"]
        rows = [r for r in run["states"] if r["names"] == names]
        self.jt = np.array([r["t"] for r in rows])
        self.jq = np.array([r["positions"] for r in rows])
        self.jadr = []
        for k, n in enumerate(names):
            try:
                self.jadr.append((k, self.m.joint(n).qposadr[0]))
            except KeyError:
                pass
        self.bt, self.bv = series(run["base"], "pose")
        q = self.bv
        self.yaw = np.unwrap(np.arctan2(2 * (q[:, 6] * q[:, 5] + q[:, 3] * q[:, 4]), 1 - 2 * (q[:, 4] ** 2 + q[:, 5] ** 2)))
        self.ot = np.array([r["t"] for r in run["objects"]])
        self.ov = np.array([r["poses"] for r in run["objects"]], float)
        self.cups = ["cup_pink", "cup_blue", "cup_yellow"]
        self.t_begin, self.t_end = self.bt[0], self.bt[-1]

    def smooth_yaw(self, t, tau=1.2):
        ts = np.linspace(t - tau, t, 13)
        w = np.exp(np.linspace(-2, 0, 13))
        return float(np.sum(w * np.interp(ts, self.bt, self.yaw)) / w.sum())

    def set(self, t):
        m, d = self.m, self.d
        q = lerp(self.jt, self.jq, t)
        for k, adr in self.jadr:
            d.qpos[adr] = q[k]
        p = lerp(self.bt, self.bv, t)
        a = m.joint("floating_base").qposadr[0]
        yaw = float(np.interp(t, self.bt, self.yaw))
        d.qpos[a:a + 3] = [p[0], p[1], p[2]]
        d.qpos[a + 3:a + 7] = [np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]
        if len(self.ot):
            o = lerp(self.ot, self.ov, t)
            for name, row in zip(self.cups, o):
                b = m.joint(name + "_free").qposadr[0]
                d.qpos[b:b + 3] = row[:3]
                d.qpos[b + 3:b + 7] = wxyz(row)
        mujoco.mj_forward(m, d)
        self.base_xy, self.base_yaw = p[:2], yaw

    def render(self, t, shot):
        self.set(t)
        cam = self.cam
        yaw_s = self.smooth_yaw(t, shot.get("tau", 1.2))
        if shot.get("mode", "track") == "track":
            if "offset_body" in shot:
                fx, fy, z = shot["offset_body"]
                c, s = np.cos(yaw_s), np.sin(yaw_s)
                cam.lookat[:] = [self.base_xy[0] + c * fx - s * fy, self.base_xy[1] + s * fx + c * fy, z]
            else:
                ox, oy, z = shot.get("offset", [0, 0, 0.6])
                cam.lookat[:] = [self.base_xy[0] + ox, self.base_xy[1] + oy, z]
        else:
            cam.lookat[:] = shot["lookat"]
        cam.distance = shot.get("distance", 2.5)
        cam.azimuth = shot.get("azimuth", 135) + (np.degrees(yaw_s) if shot.get("follow_heading") else 0.0)
        cam.elevation = shot.get("elevation", -25)
        self.r.update_scene(self.d, camera=cam, scene_option=self.opt)
        return Image.fromarray(self.r.render())
