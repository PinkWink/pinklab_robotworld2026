"""Intro video (YouTube 16:9, 1920x1080, 30 fps): PinkLAB booth at RoboWorld 2026 in MuJoCo, the robot taking orders
in Korean through the web FMS, and the Physical AI robot course behind it.

Everything shown is real: artifacts/video/run.pkl (recorded run, re-rendered offline by replay.py), the FMS browser
captures of the same run (artifacts/video/browser) and its chat log (artifacts/video/chat.json).

    MUJOCO_GL=egl ./scripts/robotworld exec python video/compose.py artifacts/video/pinklab_robotworld2026_intro.mp4
    MUJOCO_GL=egl ./scripts/robotworld exec python video/compose.py --still 5 40 60        # single frames -> artifacts/video/still_*.png
"""
import argparse
import datetime
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from replay import Replay  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
V = ROOT / "artifacts/video"
LOGO = ROOT / "src/robotworld/booth/images/logo_h.png"
W, H, FPS = 1920, 1080, 30
PANEL_W = 640                                     # right panel (FMS) in split layouts
PINK, NAVY, INK, WHITE, SOFT = (222, 107, 167), (72, 99, 174), (35, 31, 32), (255, 255, 255), (248, 213, 228)
FONT_B = "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf"
FONT_R = "/usr/share/fonts/truetype/nanum/NanumSquareR.ttf"
_fonts = {}


def font(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_B if bold else FONT_R, size)
    return _fonts[key]


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def fade(u, a, b):
    """0 before a, 1 after b (smooth)."""
    return ease((u - a) / max(1e-6, b - a))


def wrap(text, f, maxw):
    lines = []
    for para in text.split("\n"):
        line = ""
        for ch in para:
            if f.getlength(line + ch) > maxw and line:
                cut = line.rfind(" ")
                if cut > len(line) * 0.6:
                    lines.append(line[:cut]); line = line[cut + 1:] + ch
                else:
                    lines.append(line); line = ch
            else:
                line += ch
        lines.append(line)
    return lines


def alpha_text(img, xy, text, f, fill, alpha=1.0, anchor="la", shadow=True):
    if alpha <= 0:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if shadow:
        d.text((xy[0] + 3, xy[1] + 3), text, font=f, fill=(0, 0, 0, int(140 * alpha)), anchor=anchor)
    d.text(xy, text, font=f, fill=fill + (int(255 * alpha),), anchor=anchor)
    img.alpha_composite(layer)


def rounded(img, box, r, fill):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(box, r, fill=fill)
    img.alpha_composite(layer)


def caption(img, title, sub="", alpha=1.0, x=60, y=None, maxw=1100):
    """Lower-left caption card: pink bar, white title, light subtitle."""
    if alpha <= 0:
        return
    ft, fs = font(52), font(30, bold=False)
    tw = max(ft.getlength(title), fs.getlength(sub) if sub else 0)
    h = 84 + (46 if sub else 0)
    y = H - h - 70 if y is None else y
    rounded(img, (x, y, x + tw + 70, y + h), 18, (20, 16, 19, int(185 * alpha)))
    rounded(img, (x, y, x + 12, y + h), 6, PINK + (int(255 * alpha),))
    alpha_text(img, (x + 38, y + 20), title, ft, WHITE, alpha, shadow=False)
    if sub:
        alpha_text(img, (x + 38, y + 84), sub, fs, (240, 225, 233), alpha, shadow=False)


def badge(img, text, x=60, y=50):
    f = font(34)
    w = f.getlength(text)
    rounded(img, (x, y, x + w + 36, y + 58), 29, PINK + (235,))
    alpha_text(img, (x + 18, y + 11), text, f, WHITE, shadow=False)


def logo(height):
    im = Image.open(LOGO).convert("RGBA")
    return im.resize((round(im.width * height / im.height), height), Image.LANCZOS)


# ------------------------------------------------------------------ recorded data
class Run:
    def __init__(self):
        self.rp = Replay(V / "run.pkl", size=(W, H))
        self.rp_split = Replay(V / "run.pkl", size=(W - PANEL_W, H))
        self.t0 = self.rp.t_begin
        sync = np.array(self.rp.run["sync"])
        self.sim2wall = lambda t: float(np.interp(t, sync[:, 0], sync[:, 1]))
        times = json.loads((V / "browser/times.json").read_text())
        self.btimes = np.array([t for _, t in times])
        self.bframes = [V / f"browser/f{i:05d}.png" for i, _ in times]
        self._bcache = {}
        day = datetime.date.fromtimestamp(sync[0, 1])
        self.chat = json.loads((V / "chat.json").read_text())
        for c in self.chat:
            hh, mm, ss = map(int, c["t"].split(":"))
            c["wall"] = datetime.datetime(day.year, day.month, day.day, hh, mm, ss).timestamp()
        self.fb = self.rp.run["plan_fb"]

    def event(self, match, after=0.0):
        """Sim time (relative to t0) of the first plan feedback whose text contains match."""
        for r in self.fb:
            if r["t"] - self.t0 >= after and match in f"{r['step'] + 1}/{r['action']}/{r['phase']} {r['detail']}":
                return r["t"] - self.t0
        raise KeyError(match)

    def browser(self, wall):
        i = int(np.clip(np.searchsorted(self.btimes, wall) - 1, 0, len(self.bframes) - 1))
        if i not in self._bcache:
            self._bcache.clear()
            self._bcache[i] = Image.open(self.bframes[i]).convert("RGB")
        return self._bcache[i]


# ------------------------------------------------------------------ the FMS side panel
def chat_panel(run, wall, msgs=None, height=H - 560, width=PANEL_W - 40):
    """Chat bubbles (the real FMS log) up to wall time, newest at the bottom."""
    panel = Image.new("RGBA", (width, height), (251, 249, 250, 255))
    d = ImageDraw.Draw(panel)
    items = msgs if msgs is not None else [c for c in run.chat if c["wall"] <= wall + 0.01]
    f, fw = font(25, bold=False), font(17, bold=False)
    y = height - 14
    for c in reversed(items):
        user = c["who"] == "사용자"
        lines = wrap(c["text"], f, width * 0.78 - 30)
        bh = 22 + 34 * len(lines) + 12
        bw = max(f.getlength(l) for l in lines) + 30
        y -= bh
        if y < -bh:
            break
        x = width - bw - 12 if user else 12
        fill = PINK if user else WHITE
        d.rounded_rectangle((x, y, x + bw, y + bh), 16, fill=fill, outline=None if user else (226, 218, 222), width=2)
        d.text((x + 15, y + 6), f"{c['who']} · {c['t']}", font=fw, fill=(253, 230, 240) if user else (107, 97, 104))
        for k, l in enumerate(lines):
            d.text((x + 15, y + 28 + 34 * k), l, font=f, fill=WHITE if user else INK)
        y -= 12
    return panel


def side_panel(run, wall, msgs=None, title="웹 FMS"):
    p = Image.new("RGBA", (PANEL_W, H), (244, 242, 243, 255))
    d = ImageDraw.Draw(p)
    d.rectangle((0, 0, PANEL_W, 70), fill=WHITE)
    d.rectangle((0, 66, PANEL_W, 70), fill=PINK)
    d.ellipse((24, 26, 42, 44), fill=PINK)
    d.text((54, 18), "PinkLAB", font=font(30), fill=PINK)
    d.text((54 + font(30).getlength("PinkLAB ") , 18), title, font=font(30), fill=INK)
    b = run.browser(wall)
    m = b.crop((63, 168, 842, 696))                                                                                  # booth part of the map canvas (1600 px capture)
    m = m.resize((PANEL_W - 40, round((PANEL_W - 40) * m.height / m.width)), Image.LANCZOS)
    p.paste(m, (20, 86))
    d.rounded_rectangle((18, 84, PANEL_W - 18, 86 + m.height + 2), 10, outline=(226, 218, 222), width=2)
    px = b.load()
    bottom = next((y for y in range(200, 420) if all(abs(px[1000, y][k] - (244, 242, 243)[k]) < 4 for k in range(3))), 318)
    s = b.crop((990, 110, 1580, bottom - 6))                                                                         # robot status card (down to its bottom edge)
    s = s.resize((PANEL_W - 40, round((PANEL_W - 40) * s.height / s.width)), Image.LANCZOS)
    y = 86 + m.height + 14
    p.paste(s, (20, y))
    y += s.height + 12
    d.text((24, y), "LLM 지령", font=font(26), fill=INK)
    cp = chat_panel(run, wall, msgs, height=H - y - 56)
    p.alpha_composite(cp, (20, y + 40))
    return p


def split(run, scene, wall, msgs=None):
    """3D scene (W - PANEL_W wide) + FMS panel on the right."""
    img = Image.new("RGBA", (W, H))
    img.paste(scene.convert("RGBA"), (0, 0))
    img.alpha_composite(side_panel(run, wall, msgs), (W - PANEL_W, 0))
    return img


# ------------------------------------------------------------------ scenes
ORBIT = dict(lookat=[4.5, -3.0, 1.2], distance=11.0)


def orbit_shot(u):
    return dict(mode="fixed", lookat=ORBIT["lookat"], distance=ORBIT["distance"] - 1.2 * ease(u),
                azimuth=-60 + 360 * u, elevation=-14 - 14 * ease(u))


def scenes(run):
    """[(seconds, fn(u, sec) -> RGBA image)] in order."""
    rp, rs, t0 = run.rp, run.rp_split, run.t0
    still = t0 + 2.0
    ev = run.event
    t_drive1, t_pick = ev("1/navigate/navigate"), ev("2/pick/start")
    t_dock1, t_lift = ev("dock: visual servo"), ev("carry:")
    t_drive2, t_dock2 = ev("3/navigate/start"), ev("dock: visual servo", after=ev("3/navigate/start"))
    t_release = ev("place: released") if any("released" in r["detail"] for r in run.fb) else ev("retreat:") - 4
    t_retreat = ev("retreat:")
    t_guide = ev("약국")
    chat = run.chat
    q_msgs, plan_msgs = chat[0:2], chat[2:5]
    sv = []

    # 1. booth orbit
    def s_orbit(u, sec):
        img = rp.render(still, orbit_shot(u)).convert("RGBA")
        a = fade(sec, 0.0, 0.9)
        if a < 1:
            img = Image.blend(Image.new("RGBA", img.size, (0, 0, 0, 255)), img, a)
        alpha_text(img, (60, 52), "ROBOWORLD 2026  ·  KINTEX 3홀 A03", font(34), WHITE, fade(sec, 0.6, 1.6) * (1 - fade(sec, 13.4, 14.4)))
        k = fade(sec, 4.0, 5.2) * (1 - fade(sec, 13.4, 14.4))
        if k > 0:
            band = Image.new("RGBA", img.size, (0, 0, 0, 0))
            g = np.linspace(0, 1, 360) ** 1.6
            arr = np.zeros((360, W, 4), np.uint8)
            arr[..., 3] = (g[:, None] * 190 * k).astype(np.uint8)
            band.paste(Image.fromarray(arr, "RGBA"), (0, H - 360))
            img.alpha_composite(band)
            alpha_text(img, (80, H - 250), "로보월드 2026 핑크랩 부스", font(84), WHITE, k)
            alpha_text(img, (84, H - 140), "시뮬레이션 속에 영원히 남겼습니다", font(46, bold=False), SOFT, fade(sec, 5.0, 6.2) * (1 - fade(sec, 13.4, 14.4)))
        return img
    sv.append((15.0, s_orbit))

    # 2. title
    bg_title = rp.render(still, orbit_shot(1.0)).filter(ImageFilter.GaussianBlur(14)).convert("RGBA")
    dark = Image.new("RGBA", (W, H), (18, 12, 16, 150))
    bg_title.alpha_composite(dark)
    lg = logo(150)

    def s_title(u, sec):
        img = bg_title.copy()
        a = fade(sec, 0.0, 0.8) * (1 - fade(sec, 5.4, 6.0))
        if a <= 0:
            return img
        lgx = lg.copy()
        lgx.putalpha(lgx.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(lgx, ((W - lg.width) // 2, 230))
        alpha_text(img, (W // 2, 520), "MuJoCo  ×  ROS 2  ×  Physical AI", font(92), WHITE, a, anchor="mm")
        alpha_text(img, (W // 2, 640), "시뮬레이션에서 배우는 핑크랩 피지컬 AI 로봇 수업", font(46, bold=False), SOFT, fade(sec, 0.8, 1.6) * a, anchor="mm")
        return img
    sv.append((6.0, s_title))

    # 3. the robot and the FMS
    def s_robot(u, sec):
        img = rp.render(still, dict(mode="track", offset=[0.1, 0, 0.95], distance=2.7 - 0.4 * ease(u), azimuth=130 + 70 * u, elevation=-10)).convert("RGBA")
        caption(img, "이동형 양팔로봇 PL-2M", "MuJoCo 물리 시뮬레이션 · 카메라 · 라이다", fade(sec, 0.3, 1.0) * (1 - fade(sec, 4.5, 5.0)))
        return img
    sv.append((5.0, s_robot))

    fms_still = run.browser(chat[1]["wall"] + 1.5).convert("RGBA")

    def s_fms(u, sec):
        s = 1.0 + 0.06 * ease(u)
        b = fms_still.resize((round(1600 * s * 1.2), round(913 * s * 1.2)), Image.LANCZOS)
        img = Image.new("RGBA", (W, H), (244, 242, 243, 255))
        img.alpha_composite(b, ((W - b.width) // 2, (H - b.height) // 2))
        caption(img, "ROS 2 · Nav2 · MoveIt + 웹 FMS", "지도 · 수동 조작 · 카메라 · LLM 지령을 브라우저 하나에서", fade(sec, 0.3, 1.0) * (1 - fade(sec, 4.5, 5.0)))
        return img
    sv.append((5.0, s_fms))

    # 4. ask a question
    def s_ask(u, sec):
        scene = rs.render(still, dict(mode="fixed", lookat=[5.0, -3.0, 0.8], distance=8.0 - 1.0 * ease(u), azimuth=-120 + 15 * u, elevation=-32))
        n = 0 if sec < 0.8 else 1 if sec < 2.6 else 2
        msgs = q_msgs[:n]
        img = split(run, scene, chat[1]["wall"], msgs)
        caption(img, "말로 묻고", "핑크랩 부스와 회사를 아는 안내 로봇 (OpenAI LLM)", fade(sec, 0.3, 1.0), maxw=900)
        return img
    sv.append((8.0, s_ask))

    # 5. the mission
    def s_plan(u, sec):
        scene = rs.render(t0 + t_drive1 - 1.0, dict(mode="track", offset_body=[0.2, 0, 0.8], distance=3.4 - 0.5 * ease(u), azimuth=200, elevation=-16, follow_heading=True))
        n = 0 if sec < 0.6 else 1 if sec < 2.4 else 2 if sec < 5.2 else 3
        img = split(run, scene, chat[2]["wall"], plan_msgs[:n])
        caption(img, "말 한마디로 일을 시키면", "\"2번 테이블 손님에게 물 한 잔 가져다 드려\" → 계획 · 확인", fade(sec, 0.3, 1.0))
        return img
    sv.append((7.0, s_plan))

    def mission(sim_a, sim_b, shot, title, sub, speed):
        def f(u, sec):
            t = t0 + sim_a + (sim_b - sim_a) * u
            scene = rs.render(t, shot(u))
            img = split(run, scene, run.sim2wall(t))
            caption(img, title, sub, fade(sec, 0.2, 0.8))
            if speed > 1.2:
                badge(img, f"×{speed:.0f} 빨리 감기")
            return img
        return f

    follow = lambda az, d=3.2, z=0.75, el=-17: (lambda u: dict(mode="track", offset_body=[0.3, 0, z], distance=d, azimuth=az, elevation=el, follow_heading=True))  # noqa: E731
    seg = [
        (t_drive1, t_dock1, 4.0, follow(150, 4.0, 0.7, -32), "Nav2 로 음료대까지", "지도 위 경로 계획 · 장애물 회피"),
        (t_dock1, t_lift + 2.0, 10.0, lambda u: dict(mode="fixed", lookat=[7.64, -1.93, 0.85], distance=1.95 - 0.2 * ease(u), azimuth=104 + 8 * u, elevation=-36),
         "마커 도킹 → MoveIt 으로 컵 집기", "카메라로 ArUco 마커를 보고 붙은 뒤 양팔 중 가까운 팔로"),
        (t_lift + 2.0, t_dock2, 8.0, follow(160, 3.4), "컵을 든 채로 2번 테이블까지", "운반 자세로 주행"),
        (t_dock2, t_retreat + 2.0, 9.0, lambda u: dict(mode="fixed", lookat=[6.0, -4.40, 0.8], distance=2.4 - 0.2 * ease(u), azimuth=-122 + 8 * u, elevation=-15),
         "손님 앞에 내려놓기", "테이블 가장자리 마커에 도킹 · 빈 자리를 찾아 놓기"),
    ]
    for a, b, secs, shot, title, sub in seg:
        sv.append((secs, mission(a, b, shot, title, sub, (b - a) / secs)))

    def s_done(u, sec):
        t = t0 + t_retreat + 2.0 + 3.0 * u
        scene = rs.render(t, dict(mode="fixed", lookat=[6.15, -4.40, 0.85], distance=1.9 - 0.3 * ease(u), azimuth=-140 + 6 * u, elevation=-14))
        result = next(c for c in chat if c["who"] == "로봇" and "놓았습니다" in c["text"])
        img = split(run, scene, result["wall"] + 1.0)                    # the moment the result sentence appeared
        caption(img, "\"분홍 컵을 2번 상담 테이블에 놓았습니다.\"", "결과는 말로 보고 · 컵 위치 표도 갱신", fade(sec, 0.2, 0.8))
        return img
    sv.append((4.5, s_done))

    # 6. guidance
    t_g0 = t_guide - 1.0
    t_g1 = min(run.rp.t_end - t0 - 0.5, t_g0 + 26.0)
    sv.append((7.0, mission(t_g0, t_g1, follow(140, 4.2, 0.7, -35), "\"약국으로 안내해 줘\"", "부스 장소를 알고 앞장서서 안내", (t_g1 - t_g0) / 7.0)))

    # 7. the course
    bg_course = rp.render(still, orbit_shot(0.35)).filter(ImageFilter.GaussianBlur(16)).convert("RGBA")
    bg_course.alpha_composite(Image.new("RGBA", (W, H), (250, 246, 248, 205)))
    tiles = [("MuJoCo", "물리 시뮬레이션\n센서 · 부스 월드"), ("ROS 2", "Nav2 주행\nMoveIt 양팔"),
             ("LLM", "자연어 → 작업 계획\n확인 · 결과 보고"), ("웹 FMS", "브라우저에서\n보고 · 몰고 · 시키기")]
    tracks = [("피지컬 AI", "ROS2 → 모방학습 → ACT · VLA → Teleop"), ("자율 주행", "ROS2 → SLAM → Nav2 → YOLO"),
              ("강화학습", "Isaac Sim → PhysX → PPO → Sim-to-Real")]

    def s_course(u, sec):
        img = bg_course.copy()
        alpha_text(img, (W // 2, 130), "이 영상 속 로봇을 직접 만들어 보는 수업", font(68), INK, fade(sec, 0.0, 0.7), anchor="mm", shadow=False)
        alpha_text(img, (W // 2, 210), "핑크랩 피지컬 AI 로봇 수업 · MuJoCo + ROS 2", font(38, bold=False), (107, 97, 104), fade(sec, 0.3, 1.0), anchor="mm", shadow=False)
        tw, gap, y0 = 400, 36, 300
        x0 = (W - (4 * tw + 3 * gap)) // 2
        for k, (t, s) in enumerate(tiles):
            a = fade(sec, 0.8 + 0.35 * k, 1.4 + 0.35 * k)
            if a <= 0:
                continue
            x = x0 + k * (tw + gap)
            rounded(img, (x, y0 + 30 * (1 - a), x + tw, y0 + 250 + 30 * (1 - a)), 22, PINK + (int(240 * a),))
            alpha_text(img, (x + tw // 2, y0 + 95 + 30 * (1 - a)), t, font(64), WHITE, a, anchor="mm", shadow=False)
            for j, line in enumerate(s.split("\n")):
                alpha_text(img, (x + tw // 2, y0 + 165 + 38 * j + 30 * (1 - a)), line, font(28, bold=False), WHITE, a, anchor="mm", shadow=False)
        a2 = fade(sec, 3.0, 3.8)
        alpha_text(img, (W // 2, 650), "핑크랩이 교육하는 분야", font(40), INK, a2, anchor="mm", shadow=False)
        for k, (t, s) in enumerate(tracks):
            a = fade(sec, 3.4 + 0.3 * k, 4.0 + 0.3 * k)
            y = 720 + 92 * k
            rounded(img, (360, y, W - 360, y + 76), 38, WHITE + (int(235 * a),))
            alpha_text(img, (410, y + 19), t, font(38), NAVY, a, shadow=False)
            alpha_text(img, (700, y + 22), s, font(34, bold=False), INK, a, shadow=False)
        return img
    sv.append((10.0, s_course))

    # 8. end card
    lg2 = logo(170)

    def s_end(u, sec):
        img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        a = fade(sec, 0.0, 0.8)
        lgx = lg2.copy()
        lgx.putalpha(lgx.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(lgx, ((W - lg2.width) // 2, 300))
        alpha_text(img, (W // 2, 590), "PinkLAB Studio", font(64), PINK, fade(sec, 0.4, 1.2), anchor="mm", shadow=False)
        alpha_text(img, (W // 2, 680), "Physical AI 교육, 로봇부터 교안·강의까지 핑크랩 스튜디오로 한 번에", font(38, bold=False), INK, fade(sec, 0.8, 1.6), anchor="mm", shadow=False)
        alpha_text(img, (W // 2, 780), "pinklab.art", font(40), NAVY, fade(sec, 1.2, 2.0), anchor="mm", shadow=False)
        out = fade(sec, 6.2, 7.0)
        if out > 0:
            img = Image.blend(img, Image.new("RGBA", img.size, (0, 0, 0, 255)), out)
        return img
    sv.append((7.0, s_end))
    return sv


def frames(run, only=None):
    sv = scenes(run)
    total = sum(s for s, _ in sv)
    print(f"{len(sv)} scenes, {total:.1f} s, {round(total * FPS)} frames", flush=True)
    start = 0.0
    for secs, fn in sv:
        n = round(secs * FPS)
        for i in range(n):
            t = start + i / FPS
            if only is not None and not any(abs(t - s) < 0.5 / FPS for s in only):
                continue
            yield t, fn(i / max(1, n - 1), i / FPS)
        start += n / FPS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=str(V / "pinklab_robotworld2026_intro.mp4"))
    ap.add_argument("--still", type=float, nargs="*", help="write single frames at these times (s) instead of the video")
    a = ap.parse_args()
    run = Run()
    if a.still:
        for t, img in frames(run, only=a.still):
            p = V / f"still_{t:06.2f}.png"
            img.convert("RGB").save(p)
            print("saved", p, flush=True)
        return
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out],
                          stdin=subprocess.PIPE)
    for k, (t, img) in enumerate(frames(run)):
        ff.stdin.write(img.convert("RGB").tobytes())
        if k % 300 == 0:
            print(f"{t:6.1f} s", flush=True)
    ff.stdin.close()
    ff.wait()
    print("saved", a.out, flush=True)


if __name__ == "__main__":
    main()
