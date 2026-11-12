"""PinkLAB booth at RoboWorld 2026 (로보월드 2026, KINTEX) -> MuJoCo world (MJCF).

Source data: booth/booth_data.json, taken unchanged from the booth design HTML (window.BOOTH, final floor plan
2026-10-14). Units there: cm in plan, m for heights. Plan axes: x -> main aisle (0..900), z -> main entrance
(0..600), the booth's top-left corner is (0, 0).

MuJoCo frame used here: X = x / 100, Y = -z / 100, Z = height. So the booth spans X 0..9, Y -6..0, the main aisle
is at +X and the entrance at -Y. A plan angle `ang` is clockwise on the drawing (x towards z), i.e. yaw = -ang.

Geom groups: 0 = solid things a lidar / camera sees (walls, furniture, people), 2 = decoration only
(textures, overhead signs above robot height still collide-free). Nothing here moves yet; people are mocap
bodies so the next step can walk them around.
"""

import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from .textures import Textures, hex_rgb

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "booth/booth_data.json"
WHITE, BLACK, DARK, GREY = "#f7f6f7", "#231F20", "#2a2a2e", "#c9c9ce"


def load():
    return json.loads(DATA.read_text())


def P(x, z, y=0.0):
    """Plan cm (x, z) + height m -> MuJoCo metres."""
    return (x / 100.0, -z / 100.0, y)


def fmt(v):
    return " ".join(f"{float(a):.5g}" for a in v)


def rgba(color, a=1.0):
    r, g, b = hex_rgb(color)
    return f"{r / 255:.3f} {g / 255:.3f} {b / 255:.3f} {a:g}"


# Vertical face -> (outward normal in MuJoCo, plane x axis = the viewer's right when facing that face)
FACES = {"+x": ((1, 0, 0), (0, 1, 0)), "-x": ((-1, 0, 0), (0, -1, 0)),
         "+z": ((0, -1, 0), (1, 0, 0)), "-z": ((0, 1, 0), (-1, 0, 0))}


class World:
    def __init__(self, out_dir):
        self.d = load()
        self.out = Path(out_dir)
        self.tex = Textures(self.out / "textures", self.d["color"])
        self.c = self.d["color"]
        self.n = 0
        self.root = ET.Element("mujoco", model="pinklab_robotworld2026_booth")
        ET.SubElement(self.root, "compiler", angle="radian", autolimits="true")
        ET.SubElement(self.root, "option", timestep="0.002")
        vis = ET.SubElement(self.root, "visual")
        ET.SubElement(vis, "headlight", ambient="0.42 0.42 0.42", diffuse="0.35 0.35 0.35", specular="0.05 0.05 0.05")
        ET.SubElement(vis, "quality", shadowsize="8192")
        ET.SubElement(vis, "map", znear="0.01", zfar="200")
        ET.SubElement(vis, "global", offwidth="1920", offheight="1080")
        self.asset = ET.SubElement(self.root, "asset")
        self.world = ET.SubElement(self.root, "worldbody")
        self.mats = {}

    # ------------------------------------------------------------------ primitives
    def name(self, base):
        self.n += 1
        return f"{base}_{self.n}"

    def mat_color(self, color):
        key = ("c", color)
        if key not in self.mats:
            name = f"col_{color.strip('#').lower()}"
            ET.SubElement(self.asset, "material", name=name, rgba=rgba(color), specular="0.15", shininess="0.2")
            self.mats[key] = name
        return self.mats[key]

    def mat_texture(self, path, emission=0.0):
        key = ("t", str(path))
        if key not in self.mats:
            name = Path(path).stem
            ET.SubElement(self.asset, "texture", name=name, type="2d", file=str(Path(path).resolve()))
            ET.SubElement(self.asset, "material", name=name, texture=name, specular="0.1", shininess="0.1", emission=f"{emission:g}")
            self.mats[key] = name
        return self.mats[key]

    def geom(self, parent, base, solid=True, **attrs):
        g = ET.SubElement(parent if parent is not None else self.world, "geom", name=self.name(base), **attrs)
        if solid:
            g.set("group", "0")
            g.set("contype", "1")
            g.set("conaffinity", "1")
        else:
            g.set("group", "2")
            g.set("contype", "0")
            g.set("conaffinity", "0")
        return g

    def box(self, base, x0, z0, x1, z1, y0, y1, color=WHITE, solid=True, parent=None):
        """Axis-aligned box from plan rectangle (cm) and height range (m). Empty boxes are skipped."""
        if abs(x1 - x0) < 1e-6 or abs(z1 - z0) < 1e-6 or y1 - y0 <= 0:
            return None
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        return self.geom(parent, base, solid, type="box", pos=fmt(P(cx, cz, (y0 + y1) / 2)),
                         size=fmt((abs(x1 - x0) / 200, abs(z1 - z0) / 200, (y1 - y0) / 2)), material=self.mat_color(color))

    def box_c(self, base, cx, cz, w, d, ang, y0, y1, color=WHITE, solid=True, parent=None):
        """Box centred at plan (cx, cz), w along the rotated x, d along the rotated z, plan angle ang (deg, cw)."""
        return self.geom(parent, base, solid, type="box", pos=fmt(P(cx, cz, (y0 + y1) / 2)),
                         euler=fmt((0, 0, -math.radians(ang))), size=fmt((w / 200, d / 200, (y1 - y0) / 2)),
                         material=self.mat_color(color))

    def cyl(self, base, cx, cz, r_cm, y0, y1, color=WHITE, solid=True, parent=None):
        return self.geom(parent, base, solid, type="cylinder", pos=fmt(P(cx, cz, (y0 + y1) / 2)),
                         size=fmt((r_cm / 100, (y1 - y0) / 2)), material=self.mat_color(color))

    def panel(self, base, png, face, at, u0, u1, y0, y1, off=0.3, emission=0.0):
        """Textured plane on a vertical face. face: '+x' / '-x' (u = plan z) or '+z' / '-z' (u = plan x), at = the face
        coordinate (cm), off = cm in front of the face."""
        n, xa = FACES[face]
        um = (u0 + u1) / 2
        if face[1] == "x":
            c = P(at + (off if face[0] == "+" else -off), um, (y0 + y1) / 2)
        else:
            c = P(um, at + (off if face[0] == "+" else -off), (y0 + y1) / 2)
        return self.geom(None, base, False, type="plane", pos=fmt(c), xyaxes=fmt(xa + (0, 0, 1)),
                         size=fmt((abs(u1 - u0) / 200, (y1 - y0) / 2, 0.01)), material=self.mat_texture(png, emission))

    def panel_at(self, base, png, center, normal, w_m, h_m, emission=0.0):
        """Textured plane with any horizontal normal (MuJoCo xy)."""
        nx, ny = normal
        xa = (-ny, nx, 0)
        return self.geom(None, base, False, type="plane", pos=fmt(center), xyaxes=fmt(xa + (0, 0, 1)),
                         size=fmt((w_m / 2, h_m / 2, 0.01)), material=self.mat_texture(png, emission))

    def floor_plane(self, base, png, cx, cz, w_cm, h_cm, ang, y=0.0):
        """Horizontal textured plane: text reads along plan angle ang (0 = +x), seen from the entrance side."""
        a = math.radians(ang)
        read = (math.cos(a), -math.sin(a), 0)
        up = (math.sin(a), math.cos(a), 0)
        return self.geom(None, base, False, type="plane", pos=fmt(P(cx, cz, y)), xyaxes=fmt(read + up),
                         size=fmt((w_cm / 200, h_cm / 200, 0.01)), material=self.mat_texture(png))

    def monitor(self, base, face, at, cu, inch, bottom, png, depth=4):
        """Wall monitor (16:9) on a vertical face, centred at u = cu (cm)."""
        w = 0.0254 * inch * 16 / math.hypot(16, 9)
        h = 0.0254 * inch * 9 / math.hypot(16, 9)
        sgn = 1 if face[0] == "+" else -1
        if face[1] == "x":
            self.box(base, at, cu - w * 50 - 1, at + sgn * depth, cu + w * 50 + 1, bottom - 0.01, bottom + h + 0.01, BLACK)
        else:
            self.box(base, cu - w * 50 - 1, at, cu + w * 50 + 1, at + sgn * depth, bottom - 0.01, bottom + h + 0.01, BLACK)
        self.panel(base + "_screen", png, face, at + sgn * depth, cu - w * 50, cu + w * 50, bottom, bottom + h, off=0.2, emission=0.6)

    # ------------------------------------------------------------------ booth parts
    def hall(self):
        nb = self.d["neighbours"]
        ET.SubElement(self.asset, "texture", name="hall_grid", type="2d", builtin="checker", rgb1="0.36 0.36 0.38", rgb2="0.33 0.33 0.35",
                      width="512", height="512")
        ET.SubElement(self.asset, "material", name="hall_floor", texture="hall_grid", texrepeat="40 40", specular="0.05")
        ET.SubElement(self.asset, "texture", name="hall_sky", type="skybox", builtin="gradient", rgb1="0.62 0.62 0.65", rgb2="0.30 0.30 0.33",
                      width="512", height="512")
        z0, z1 = nb["hallZ"]
        self.geom(None, "hall_floor", True, type="plane", pos=fmt(P(1500, (z0 + z1) / 2, 0)), size=fmt((40, 40, 0.1)), material="hall_floor")
        self.box("hall_wall", nb["hallWall"] - 30, z0, nb["hallWall"], z1, 0, 8, "#bdbdc2")
        for x0, z0_, x1, z1_, h, label in nb["boxes"]:
            self.box("neighbour", x0, z0_, x1, z1_, 0, h, "#d9d9dd")
            self.box("neighbour_band", x0 - 1, z0_ - 1, x1 + 1, z1_ + 1, h - 0.5, h, "#a9a9b0", solid=False)

    def floor(self):
        b = self.d["booth"]
        self.box("booth_floor", 0, 0, b["w"], b["d"], 0, 0.02, "#e9e8ea")
        for x0, z0, x1, z1 in self.d["floor"]["pink"]:
            self.box("pink_floor", x0, z0, x1, z1, 0.02, 0.025, self.c["pink"], solid=False)
        for i, t in enumerate(self.d["floor"]["texts"]):
            png = self.tex.floor_text(f"floor_text_{i}", t["text"], t["w"] / 100, "#ffffff")
            self.floor_plane("floor_text", png, t["c"][0], t["c"][1], t["w"], t["w"] * 0.09, t["ang"], 0.027)

    def outer_wall(self):
        d, top, band = self.d, self.d["height"]["top"], self.d["height"]["band"]
        x0, z0, x1, z1 = d["outerWall"]["rect"]
        self.box("outer_wall", x0, z0, x1, z1, 0, top, WHITE)
        self.panel("outer_wall_out", self.tex.outer_wall(d, (z1 - z0) / 100, top), "-x", x0, z0, z1, 0, top)
        # inside over classroom 1: studio wall graphics, pink band, 75" TV
        sw = d["studioWall"]
        self.panel("studio_wall", self.tex.studio_wall(sw, 300, 600, band), "+x", x1, 300, 600, 0, band)
        self.box("studio_band", x1, 300, x1 + 0.6, 600, band, top, self.c["pink"], solid=False)
        self.panel("studio_title", self.tex.studio_band(sw, 300, 600, top - band), "+x", x1 + 0.6, 300, 600, band, top)
        tv = sw["tv"]
        self.monitor("tv", "+x", x1, tv["cz"], tv["inch"], tv["bottom"], self.tex.screen("screen_tv", "tv.jpg"))

    def storage(self):
        d, top, band = self.d, self.d["height"]["top"], self.d["height"]["band"]
        st = d["storage"]
        x0, z0, x1, z1 = st["rect"]
        t = st["t"]
        door = st["door"]
        # back wall (aisle side) with the door opening, right wall (+x, pharmacy side), bottom wall (+z, classroom side)
        self.box("storage_back", x0 + 20, z0, door["x0"], z0 + t, 0, band)
        self.box("storage_back", door["x1"], z0, x1, z0 + t, 0, band)
        self.box("storage_over_door", door["x0"], z0, door["x1"], z0 + t, door["h"], band)
        self.box("storage_door", door["x0"], z0 + 2, door["x1"], z0 + 4, 0, door["h"], "#ececee")
        self.panel("door_face", self.tex.door((door["x1"] - door["x0"]) / 100, door["h"], door["text"]), "-z", z0 + 2, door["x0"], door["x1"], 0, door["h"])
        self.box("storage_right", x1 - t, z0, x1, z1, 0, band)
        self.box("storage_bottom", x0 + 20, z1 - t, x1, z1, 0, band)
        # pink band all round on top (3.7 .. 4.5 m) + the logo on the pharmacy side
        self.box("storage_band", x0 + 20, z0, x1, z0 + t, band, top, self.c["pink"])
        self.box("storage_band", x1 - t, z0, x1, z1, band, top, self.c["pink"])
        self.box("storage_band", x0 + 20, z1 - t, x1, z1, band, top, self.c["pink"])
        bl = st["bandLogo"]
        logo = self.tex.logo_on("logo_storage_band", bl["w"], top - band, self.c["pink"])
        self.panel("storage_band_logo", logo, "+x", x1, bl["cz"] - bl["w"] * 50, bl["cz"] + bl["w"] * 50, band, top)
        self.panel("storage_band_logo_back", self.tex.logo_on("logo_storage_back", 1.45, top - band, self.c["pink"]), "-z", z0, 40, 185, band, top)
        for i, p in enumerate(st["poster"]):
            png = self.tex.lines(f"poster_{i}", p["w"], p["h"], p["lines"], bg="#ffffff", fg="#231F20")
            self.panel("poster", png, "-z", z0, p["cx"] - p["w"] * 50, p["cx"] + p["w"] * 50, p["y"] - p["h"] / 2, p["y"] + p["h"] / 2)
        # inside: camp bed, stacked boxes, a small table
        ins = st["inside"]
        bx0, bz0, bx1, bz1 = ins["bed"]
        self.box("bed", bx0, bz0, bx1, bz1, 0, 0.42, "#5b6b8a")
        ax, az = ins["boxes"]["at"]
        for k in range(ins["boxes"]["n"]):
            self.box("crate", ax - 25, az, ax + 25, az + 36, k * 0.3, k * 0.3 + 0.29, "#7e8fc3")
        tx, tz = ins["table"]["c"]
        self.box("storage_table", tx - 50, tz - 25, tx + 50, tz + 25, 0.70, 0.73, WHITE)
        self.box("storage_table_leg", tx - 3, tz - 3, tx + 3, tz + 3, 0, 0.70, GREY)

    def storage_graphics(self):
        """Prints on the storage outer walls: pharmacy (+x), curriculum, history, monitors, classroom-1 side (+z)."""
        d = self.d
        x1 = d["storage"]["rect"][2]
        z1 = d["storage"]["rect"][3]
        ph = d["pharmacy"]
        self.panel("pharmacy", self.tex.pharmacy(ph, *ph["z"]), "+x", x1, *ph["z"], *ph["y"])
        cu = d["curriculum"]
        head = self.tex.lines("curriculum_head", (cu["z"][1] - cu["z"][0]) / 100, cu["headH"], [cu["title"]], bg=self.c["pink"], fg="#ffffff")
        self.panel("curriculum_head", head, "+x", x1, *cu["z"], cu["y"][1] - cu["headH"], cu["y"][1])
        body = self.tex.image("curriculum", "curriculum.png", (cu["z"][1] - cu["z"][0]) / 100, cu["y"][1] - cu["headH"] - cu["y"][0])
        self.panel("curriculum", body, "+x", x1, *cu["z"], cu["y"][0], cu["y"][1] - cu["headH"])
        wh = d["wallHistory"]
        items = d["pillar"]["history"]["items"]
        self.panel("history", self.tex.history(items, (wh["z"][1] - wh["z"][0]) / 100, wh["y"][1] - wh["y"][0]), "+x", x1, *wh["z"], *wh["y"])
        for m in d["wallMonitors"]:
            self.monitor("wall_monitor", m["face"], m["at"], m["cz"], m["inch"], m["bottom"], self.tex.screen(f"screen_{m['img']}", f"monitor_{m['img']}.jpg"))
        ss = d["storageSide"]
        st = ss["stats"]
        self.panel("stats", self.tex.stats(st), "+z", z1, *st["u"], *st["y"])
        po = ss["poster"]
        self.panel("tracks", self.tex.tracks(po), "+z", z1, po["cx"] - po["w"] * 50, po["cx"] + po["w"] * 50, *po["y"])
        lw = d["lowWall"]
        self.box("low_wall", *lw["rect"], 0, lw["h"])

    def graphics(self):
        for g in self.d["graphics"]:
            if "img" not in g or g["img"] == "g2":
                continue   # g2 sits on the rotated table B (see tables)
            u0, u1 = g["u"]
            y0, y1 = g["y"]
            png = self.tex.image(f"gfx_{g['img']}", f"{g['img']}.jpg", abs(u1 - u0) / 100, y1 - y0)
            self.panel(f"gfx_{g['img']}", png, g["face"], g["at"], u0, u1, y0, y1, off=0.4)

    def fascia_and_pillar(self):
        d, top, band = self.d, self.d["height"]["top"], self.d["height"]["band"]
        f = d["fascia"]
        self.box("fascia", f["x"][0], f["z"][0], f["x"][1], f["z"][1], band, top, self.c["pink"], solid=False)
        cx = sum(f["x"]) / 2
        logo = self.tex.logo_on("logo_fascia", f["logoW"], top - band, self.c["pink"])
        self.panel("fascia_logo_out", logo, "-z", f["z"][0], cx - f["logoW"] * 50, cx + f["logoW"] * 50, band, top)
        self.panel("fascia_logo_in", logo, "+z", f["z"][1], cx - f["logoW"] * 50, cx + f["logoW"] * 50, band, top)
        p = d["pillar"]
        x0, z0, x1, z1 = p["rect"]
        self.box("pillar", x0, z0, x1, z1, 0, top, self.c["pink"])
        m = p["monitor"]
        self.monitor("pillar_monitor", "+x", x1, (z0 + z1) / 2, m["inch"], m["bottom"], self.tex.screen("screen_pl", "monitor_pl.jpg"))
        title = self.tex.lines("pillar_title", 0.8, 0.34, m["title"], bg=self.c["pink"], fg="#ffffff")
        self.panel("pillar_title", title, "+x", x1, z0 + 5, z1 - 5, m["bottom"] + 0.45, m["bottom"] + 0.79)
        qy0, qy1 = p["qr"]["y"]
        self.panel("pillar_qr", self.tex.qr_bubble(p["qr"]["items"], (z1 - z0 - 10) / 100, qy1 - qy0), "+x", x1, z0 + 5, z1 - 5, qy0, qy1)

    def wave_sign(self):
        """Overhead S-curve sign (3.7 .. 4.5 m) on one round pole; Catmull-Rom through the plan points."""
        d, top, band = self.d, self.d["height"]["top"], self.d["height"]["band"]
        w = d["waveSign"]
        pts = w["path"]
        ext = [pts[0]] + pts + [pts[-1]]
        curve = []
        for i in range(1, len(ext) - 2):
            p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
            for k in range(12):
                s = k / 12
                curve.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * s + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * s * s
                                          + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * s ** 3) for j in (0, 1)))
        curve.append(tuple(pts[-1]))
        length = [0.0]
        for a, b in zip(curve, curve[1:]):
            length.append(length[-1] + math.dist(a, b))
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            self.box_c("wave", (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, math.dist(a, b) + 2, w["t"], ang, band, top, self.c["pink"], solid=False)
        # flat logo on the entrance side at curve fraction u
        lg = w["logo"]
        target = lg["u"] * length[-1]
        i = next(k for k in range(len(length)) if length[k] >= target)
        a, b = curve[i - 1], curve[i]
        tx, tz = (b[0] - a[0]) / math.dist(a, b), (b[1] - a[1]) / math.dist(a, b)
        nx, nz = tz, -tx                                     # plan normal
        if nx + nz < 0:                                      # face the entrance / main aisle side (+x, +z)
            nx, nz = -nx, -nz
        off = w["t"] / 2 + lg.get("out", 0) * 100                 # the 3D letters stand `out` m in front of the sign
        c = ((a[0] + b[0]) / 2 + nx * off, (a[1] + b[1]) / 2 + nz * off)
        logo = self.tex.logo_on("logo_wave", 2.4, top - band, self.c["pink"])
        self.panel_at("wave_logo", logo, P(c[0], c[1], (band + top) / 2), (nx, -nz), 2.4, top - band)
        pole = w["pole"]
        self.cyl("wave_pole", *pole["at"], pole["d"] / 2, 0, band, self.c["pink"])          # d in cm: a 6 cm pole, 26 cm round banner
        by0, by1 = pole["banner"]["y"]
        self.cyl("wave_banner", *pole["at"], pole["banner"]["d"] / 2, by0, by1, WHITE, solid=False)

    def tables(self):
        d = self.d
        for t in d["tables"]:
            h = t["h"]
            if "rect" in t:
                x0, z0, x1, z1 = t["rect"]
                cx, cz, w, dd, ang = (x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0, 0
            else:
                cx, cz = t["c"]
                w, dd, ang = t["w"], t["d"], t.get("ang", 0)
            self.box_c("table", cx, cz, w, dd, ang, 0, h - 0.03, WHITE)
            self.box_c("table_top", cx, cz, w + 2, dd + 2, ang, h - 0.03, h, "#ffffff")
            if t.get("laptop") or t.get("laptopImg"):
                self.box_c("laptop", cx, cz, 32, 22, ang, h, h + 0.02, DARK, solid=False)
            if t.get("dice"):
                for k, col in enumerate((self.c["pink"], self.c["navy"], "#f0c43a")):
                    self.box_c("cube", cx - 15 + 15 * k, cz - 10, 5, 5, ang, h, h + 0.05, col)
            fg = t.get("frontGfx")
            if fg:                                            # table B: printed inquiry board on the aisle-facing side
                a = math.radians(ang)
                vx, vz = -math.sin(a), math.cos(a)           # rotated depth axis (plan)
                nx, nz = -vx, -vz                             # front = -depth side (faces the aisle visitors)
                gw, gh = fg["w"], fg["w"] * fg["ar"]
                c = (cx + nx * (dd / 2 + 0.4), cz + nz * (dd / 2 + 0.4))
                png = self.tex.image("gfx_g2", "g2.jpg", gw, gh)
                self.panel_at("gfx_g2", png, P(c[0], c[1], fg["cy"]), (nx, -nz), gw, gh)
        for bt in d["blackTables"]:
            x0, z0, x1, z1 = bt["rect"]
            self.box("black_table", x0, z0, x1, z1, bt["h"] - 0.03, bt["h"], BLACK)
            for cxx, czz in ((x0 + 3, z0 + 3), (x1 - 3, z0 + 3), (x0 + 3, z1 - 3), (x1 - 3, z1 - 3)):
                self.box("black_table_leg", cxx - 2, czz - 2, cxx + 2, czz + 2, 0, bt["h"] - 0.03, BLACK)
            for k in range(bt["medBoxes"]):
                self.box("med_box", x0 + 8 + (k % 4) * 9, z0 + 10 + (k // 4) * 20, x0 + 15 + (k % 4) * 9, z0 + 22 + (k // 4) * 20,
                         bt["h"], bt["h"] + 0.07, "#ffffff" if k % 2 else "#cfe2f6")

    def classroom(self):
        sd = self.d["studentDesks"]
        for desk in sd["desks"]:
            x, z = desk["at"]
            h = sd["h"]
            self.box("desk_top", x - sd["w"] / 2, z - sd["d"] / 2, x + sd["w"] / 2, z + sd["d"] / 2, h - 0.03, h, "#ffffff")
            self.box("desk_post", x - 3, z - 3, x + 3, z + 3, 0.03, h - 0.03, WHITE)
            self.box("desk_base", x - 4, z - sd["d"] / 2 + 4, x + 4, z + sd["d"] / 2 - 4, 0, 0.03, GREY)
            self.cyl("stool", x + sd["w"] / 2 + 20, z, 16, 0, 0.46, "#ffffff")
            # tabletop robot: Pinky Pro / Pinky Zero
            r = 9 if desk["bot"] == "pro" else 6
            self.cyl("pinky", x, z - 8, r, h, h + (0.14 if desk["bot"] == "pro" else 0.08), self.c["pink"])
        # lecturer's desk (closed toward the students) is in tables; leaflet stands and POP boards
        for lf in self.d["leaflets"]:
            x, z = lf["at"]
            self.box_c("leaflet_stand", x, z, 30, 6, lf["ang"], 0, lf.get("h", 1.2), "#ffffff")
        for p in self.d["pops"]:
            x, z = p["at"]
            self.box_c("pop", x, z, 30, 4, p["ang"], 0, 1.2, self.c["pink"])

    def consult(self):
        c = self.d["consult"]
        for tx, tz in c["tables"]:
            self.cyl("consult_table", tx, tz, c["r"], c["h"] - 0.03, c["h"], "#ffffff")
            self.cyl("consult_post", tx, tz, 4, 0, c["h"] - 0.03, GREY)
            for k in range(c["chairs"]):
                a = math.radians(90 + 120 * k)
                x, z = tx + 55 * math.cos(a), tz + 55 * math.sin(a)
                self.cyl("chair_seat", x, z, 22, 0.40, 0.45, "#ffffff")
                self.cyl("chair_post", x, z, 3, 0, 0.40, GREY)
                bx, bz = tx + 72 * math.cos(a), tz + 72 * math.sin(a)
                self.box_c("chair_back", bx, bz, 36, 5, -math.degrees(a) + 90 + 180, 0.45, 0.80, "#ffffff")

    def info_desk(self):
        info = self.d["infoDesk"]
        h = info["h"]
        greens = [tuple(g) for g in info["greens"]]
        for x0, z0, x1, z1 in info["arms"]:
            self.box("info_desk", x0, z0, x1, z1, 0, h, "#ffffff")
        for x0, z0, x1, z1 in greens:
            self.box("flower_bed", x0 + 2, z0 + 2, x1 - 2, z1 - 2, h - 0.03, h + 0.002, "#9ccc65", solid=False)
        for x, z in self.d["pinkyZero"]:
            self.cyl("pinky_zero", x, z, 6, h, h + 0.08, self.c["pink"])
        for x, z, a in info["stools"]:
            self.cyl("bar_stool", x, z, 18, 0, 0.66, "#ffffff")

    def robots(self):
        """PL-2M exhibits (mobile dual-arm robots), simplified: base, column, shoulders, two arms, head camera."""
        for r in self.d["robots"]:
            x, z = r["at"]
            ang = r["ang"] + 180                               # robots store the back direction (see the source notes)
            yaw = math.atan2(-math.cos(math.radians(ang)), math.sin(math.radians(ang)))
            body = ET.SubElement(self.world, "body", name=self.name("pl2m"), pos=fmt(P(x, z, 0)), euler=fmt((0, 0, yaw)))
            self.geom(body, "pl2m_base", True, type="box", pos="0 0 0.17", size="0.30 0.25 0.15", material=self.mat_color(DARK))
            self.geom(body, "pl2m_column", True, type="box", pos="-0.02 0 0.75", size="0.05 0.06 0.45", material=self.mat_color(BLACK))
            self.geom(body, "pl2m_chest", True, type="box", pos="0.02 0 1.15", size="0.07 0.10 0.08", material=self.mat_color(BLACK))
            for side, col in ((1, BLACK), (-1, self.c["navy"])):
                self.geom(body, "pl2m_shoulder", True, type="cylinder", pos=f"0.02 {side * 0.16} 1.15", euler="1.5708 0 0", size="0.055 0.06",
                          material=self.mat_color(GREY))
                self.geom(body, "pl2m_arm", True, type="capsule", fromto=f"0.04 {side * 0.22} 1.12 0.10 {side * 0.24} 0.80", size="0.045",
                          material=self.mat_color(col))
                self.geom(body, "pl2m_forearm", True, type="capsule", fromto=f"0.10 {side * 0.24} 0.80 0.32 {side * 0.20} 0.78", size="0.04",
                          material=self.mat_color(col))
            self.geom(body, "pl2m_head", True, type="box", pos="0.0 0 1.42", size="0.03 0.05 0.03", material=self.mat_color(DARK))

    def people(self):
        """Staff (dusty-pink sweatshirts) and visitors: primitive people, mocap bodies for the next step."""
        st = self.d["staff"]
        for k, p in enumerate(st["people"]):
            self.person(f"staff_{k}", p, st["top"], "#3a3f47")
        for k, p in enumerate(self.d["visitors"]["people"]):
            self.person(f"visitor_{k}", p, p.get("top", "#8a8d93"), p.get("pants", "#2d2d33"))

    def person(self, name, p, top, pants):
        x, z = p["at"]
        h = p.get("h", 170) / 100
        k = p.get("build", 1.0)
        a = math.radians(p.get("ang", 0))
        yaw = math.atan2(-math.cos(a), math.sin(a))
        pose = p.get("pose", "stand")
        y = p.get("y", 0.0)
        body = ET.SubElement(self.world, "body", name=name, mocap="true", pos=fmt(P(x, z, y)), euler=fmt((0, 0, yaw)))
        skin, hair = "#e8c4a8", "#2b2320"
        g = lambda base, color, **kw: self.geom(body, base, True, material=self.mat_color(color), **kw)
        sw = 0.11 * k
        if pose == "lie":                                     # on the camp bed, feet at `at`, head towards +z (plan)
            g("legs", pants, type="capsule", fromto=f"0 0 0.08 0 {-0.85 * h / 1.7} 0.08", size=f"{0.07 * k:g}")
            g("torso", top, type="capsule", fromto=f"0 {-0.85 * h / 1.7} 0.10 0 {-1.40 * h / 1.7} 0.10", size=f"{0.13 * k:g}")
            g("head", skin, type="sphere", pos=f"0 {-1.55 * h / 1.7} 0.12", size="0.10")
            return
        if pose == "sit":
            seat = p.get("seat", 0.46)
            g("thigh", pants, type="capsule", fromto=f"-0.05 0 {seat + 0.06} 0.35 0 {seat + 0.06}", size=f"{0.075 * k:g}")
            g("shin", pants, type="capsule", fromto=f"0.37 0 {seat + 0.04} 0.37 0 0.06", size=f"{0.06 * k:g}")
            hip = seat + 0.08
        else:
            hip = 0.53 * h
            for s in (1, -1):
                g("leg", pants, type="capsule", fromto=f"0 {s * 0.09 * k} 0.08 0 {s * 0.09 * k} {hip}", size=f"{0.065 * k:g}")
        shoulder = hip + 0.30 * h
        g("torso", top, type="capsule", fromto=f"0 0 {hip + 0.08} 0 0 {shoulder - 0.06}", size=f"{0.16 * k:g}")
        for s in (1, -1):
            if p.get("arms") == "desk":
                g("arm", top, type="capsule", fromto=f"0 {s * (sw + 0.08)} {shoulder - 0.04} 0.32 {s * 0.12} {shoulder - 0.30}", size="0.045")
            else:
                g("arm", top, type="capsule", fromto=f"0 {s * (sw + 0.08)} {shoulder - 0.04} 0.02 {s * (sw + 0.10)} {shoulder - 0.52}", size="0.045")
        g("head", skin, type="sphere", pos=f"0 0 {shoulder + 0.13}", size="0.105")
        g("hair", hair, type="sphere", pos=f"-0.02 0 {shoulder + 0.165}", size="0.10")

    def lights(self):
        """Hall lights + booth spots (the source has 19 projecting lamps; MuJoCo's renderer uses a few lights)."""
        ET.SubElement(self.world, "light", name="sun", directional="true", pos="4.5 -3 12", dir="-0.25 0.2 -1", diffuse="0.45 0.45 0.45",
                      specular="0.05 0.05 0.05", castshadow="true")
        for i, (x, z) in enumerate(((220, 300), (600, 300), (820, 400))):
            ET.SubElement(self.world, "light", name=f"booth_spot_{i}", pos=fmt(P(x, z, 6.0)), dir="0 0 -1", diffuse="0.35 0.33 0.34",
                          cutoff="60", exponent="2", castshadow="false")

    def cameras(self):
        """The design file's named views (metres, y up, z towards the entrance) as fixed cameras."""
        for v in self.d["views"]:
            px, py, pz = v["pos"]
            lx, ly, lz = v["look"]
            pos = (px, -pz, py)
            look = (lx, -lz, ly)
            fwd = [look[i] - pos[i] for i in range(3)]
            n = math.sqrt(sum(f * f for f in fwd))
            fwd = [f / n for f in fwd]
            up0 = (0, 1, 0) if abs(fwd[2]) > 0.99 else (0, 0, 1)
            right = (fwd[1] * up0[2] - fwd[2] * up0[1], fwd[2] * up0[0] - fwd[0] * up0[2], fwd[0] * up0[1] - fwd[1] * up0[0])
            rn = math.sqrt(sum(r * r for r in right))
            right = [r / rn for r in right]
            up = (right[1] * fwd[2] - right[2] * fwd[1], right[2] * fwd[0] - right[0] * fwd[2], right[0] * fwd[1] - right[1] * fwd[0])
            ET.SubElement(self.world, "camera", name=v["key"], pos=fmt(pos), xyaxes=fmt(list(right) + list(up)), fovy="45")

    def build(self):
        for part in (self.hall, self.floor, self.outer_wall, self.storage, self.storage_graphics, self.graphics, self.fascia_and_pillar,
                     self.wave_sign, self.tables, self.classroom, self.consult, self.info_desk, self.robots, self.people, self.lights, self.cameras):
            part()
        ET.indent(self.root)
        path = self.out / "booth.xml"
        ET.ElementTree(self.root).write(path, encoding="unicode")
        return path


def build(out_dir=ROOT / "build"):
    return World(out_dir).build()
