"""Wall graphics for the booth, drawn with Pillow at build time (MuJoCo shows them as plane textures).

MuJoCo ignores texture alpha, so every texture here is opaque: logos are composited onto the colour of the
surface they sit on. Korean text needs a Hangul font (Ubuntu: fonts-nanum).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMAGES = Path(__file__).resolve().parents[1] / "booth/images"
FONTS = [
    "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
PX = 200  # texture pixels per metre


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def font(size):
    for f in FONTS:
        if Path(f).is_file():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def canvas(w_m, h_m, color):
    return Image.new("RGB", (max(8, round(w_m * PX)), max(8, round(h_m * PX))), hex_rgb(color) if isinstance(color, str) else color)


def paste_fit(img, src, box, bg=None):
    """Paste src (path or image) into box (x0, y0, x1, y1 px), keeping aspect, centred. RGBA is composited."""
    im = src if isinstance(src, Image.Image) else Image.open(src)
    im = im.convert("RGBA")
    bw, bh = box[2] - box[0], box[3] - box[1]
    s = min(bw / im.width, bh / im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    x, y = box[0] + (bw - im.width) // 2, box[1] + (bh - im.height) // 2
    img.paste(im, (x, y), im)
    return img


def text(img, xy, s, size, color="#231F20", anchor="mm"):
    ImageDraw.Draw(img).text(xy, s, font=font(size), fill=hex_rgb(color) if isinstance(color, str) else color, anchor=anchor)


def text_fit(img, box, s, color="#231F20", max_size=200):
    """Largest single line that fits box."""
    size = max_size
    d = ImageDraw.Draw(img)
    while size > 6:
        l, t, r, b = d.textbbox((0, 0), s, font=font(size))
        if r - l <= box[2] - box[0] and b - t <= box[3] - box[1]:
            break
        size -= 2
    text(img, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), s, size, color)


class Textures:
    """Writes PNGs into out_dir and remembers them, so the builder can declare one texture per file."""

    def __init__(self, out_dir, colors):
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.c = colors

    def save(self, name, img):
        path = self.out / f"{name}.png"
        img.save(path)
        return path

    # ---------------------------------------------------------------- logos and plain images
    def logo_on(self, name, w_m, h_m, bg, which="h", pad=0.08):
        img = canvas(w_m, h_m, bg)
        p = round(min(img.size) * pad)
        return self.save(name, paste_fit(img, IMAGES / f"logo_{which}.png", (p, p, img.width - p, img.height - p)))

    def image(self, name, file, w_m, h_m, bg="#ffffff"):
        img = canvas(w_m, h_m, bg)
        return self.save(name, paste_fit(img, IMAGES / file, (0, 0, img.width, img.height)))

    def lines(self, name, w_m, h_m, lines, bg="#ffffff", fg="#231F20", head=None, head_bg=None):
        """Text panel: optional coloured head band + centred lines."""
        img = canvas(w_m, h_m, bg)
        top = 0
        if head:
            hb = round(img.height * 0.22)
            ImageDraw.Draw(img).rectangle((0, 0, img.width, hb), fill=hex_rgb(head_bg or self.c["pink"]))
            text_fit(img, (8, 4, img.width - 8, hb - 4), head, "#ffffff")
            top = hb
        n = len(lines)
        step = (img.height - top) / (n + 1)
        for i, s in enumerate(lines):
            y = top + step * (i + 1)
            text_fit(img, (10, y - step * 0.4, img.width - 10, y + step * 0.4), s, fg, max_size=round(step * 0.6))
        return self.save(name, img)

    # ---------------------------------------------------------------- composed walls
    def outer_wall(self, d, w_m, h_m):
        """Outside of the left wall: pink, logo, slogan (the side seen from the hall wall aisle)."""
        img = canvas(w_m, h_m, self.c["pink"])
        W, H = img.size
        paste_fit(img, IMAGES / "logo_h.png", (round(W * 0.12), round(H * 0.40), round(W * 0.88), round(H * 0.58)))
        text_fit(img, (round(W * 0.1), round(H * 0.60), round(W * 0.9), round(H * 0.66)), d["outerWall"]["slogan"], "#ffffff")
        return self.save("outer_wall", img)

    def studio_wall(self, sw, z0, z1, top):
        """Inside of the left wall over classroom 1 (z0..z1 cm, floor..top m): title, five benefits, wainscot.
        Image left = larger z (viewer faces -x... no: viewer faces the wall from +x, so left = larger z)."""
        w_m, h_m = (z1 - z0) / 100, top
        img = canvas(w_m, h_m, self.c["wall"])
        W, H = img.size
        d = ImageDraw.Draw(img)
        u = lambda z: round((z1 - z) / 100 * PX)           # wall z -> image x (left = z1)
        v = lambda y: round((top - y) * PX)                 # height -> image y
        # wainscot: vertical grooves below sw["wainscot"]
        for x in range(0, W, 18):
            d.line((x, v(sw["wainscot"]), x, H), fill=(222, 220, 224), width=2)
        d.line((0, v(sw["wainscot"]), W, v(sw["wainscot"])), fill=(200, 196, 202), width=3)
        bz0, bz1 = sw["benefitZ"]
        by0, by1 = sw["benefitY"]
        text_fit(img, (u(bz1), v(by1 + 0.02), u(bz0), v(by1 - 0.12)), sw["benefitTitle"], "#231F20")
        n = len(sw["benefits"])
        cell = (bz1 - bz0) / n
        for i, (head, sub) in enumerate(sw["benefits"]):
            cz = bz1 - cell * (i + 0.5)
            cy = (by0 + by1 - 0.12) / 2 + (0.08 if i % 2 else -0.04)
            r = sw["hexW"] / 2 * PX
            cx, cyy = u(cz), v(cy)
            hexagon = [(cx + r * c, cyy + r * s) for c, s in ((1, 0), (0.5, 0.866), (-0.5, 0.866), (-1, 0), (-0.5, -0.866), (0.5, -0.866))]
            d.polygon(hexagon, fill=hex_rgb(self.c["pink"]))
            text(img, (cx, cyy - r * 0.28), head, round(r * 0.30), "#ffffff")
            for k, s in enumerate(sub):
                text(img, (cx, cyy + r * (0.12 + 0.26 * k)), s, round(r * 0.17), "#ffffff")
        return self.save("studio_wall", img)

    def studio_band(self, sw, z0, z1, h_m):
        """Pink band over classroom 1 with the white 'PinkLAB Studio' title at titleZ (left = larger z)."""
        img = canvas((z1 - z0) / 100, h_m, self.c["pink"])
        tz0, tz1 = sw["titleZ"]
        u = lambda z: round((z1 - z) / 100 * PX)
        text_fit(img, (u(tz1), round(0.10 * PX), u(tz0), round((0.10 + sw["titleH"]) * PX)), sw["title"], "#ffffff")
        return self.save("studio_band", img)

    def pharmacy(self, ph, z0, z1):
        """Printed pharmacy shelves on the storage outer wall (+x face): navy head band + 4 rows of boxes."""
        y0, y1 = ph["y"]
        img = canvas((z1 - z0) / 100, y1 - y0, "#f2f4f8")
        W, H = img.size
        d = ImageDraw.Draw(img)
        hb = round(ph["headH"] * PX)
        d.rectangle((0, 0, W, hb), fill=hex_rgb(self.c["navy"]))
        text_fit(img, (10, 4, W - 10, hb - 4), ph["head"], "#ffffff")
        rows = ph["rows"]
        rh = (H - hb) / rows
        palette = [(222, 107, 167), (72, 99, 174), (126, 143, 195), (240, 179, 207), (250, 250, 250), (110, 190, 160)]
        for r in range(rows):
            yb = hb + rh * (r + 1)
            d.rectangle((0, yb - 8, W, yb), fill=(170, 170, 178))
            x = 6
            k = r * 3
            while x < W - 30:
                bw = 22 + (k * 7) % 26
                bh = rh * (0.45 + ((k * 13) % 30) / 100)
                d.rectangle((x, yb - 8 - bh, x + bw, yb - 8), fill=palette[k % len(palette)], outline=(120, 120, 130))
                x += bw + 4
                k += 1
        return self.save("pharmacy", img)

    def history(self, items, w_m, h_m):
        img = canvas(w_m, h_m, self.c["wall"])
        W, H = img.size
        d = ImageDraw.Draw(img)
        d.line((10, H // 2, W - 10, H // 2), fill=hex_rgb(self.c["pink"]), width=6)
        n = len(items)
        for i, (year, month, body) in enumerate(items):
            x = round(W * (i + 0.5) / n)
            d.ellipse((x - 9, H // 2 - 9, x + 9, H // 2 + 9), fill=hex_rgb(self.c["pink"]))
            up = i % 2 == 0
            text(img, (x, H * (0.22 if up else 0.70)), year, round(H * 0.16), self.c["pink"])
            text(img, (x, H * (0.38 if up else 0.86)), body.replace("\n", " "), round(H * 0.08), "#6b6168")
        return self.save("history", img)

    def stats(self, st):
        w_m, h_m = (st["u"][1] - st["u"][0]) / 100, st["y"][1] - st["y"][0]
        img = canvas(w_m, h_m, self.c["wall"])
        W, H = img.size
        text_fit(img, (0, 0, W, round(H * 0.3)), st["title"], "#231F20")
        n = len(st["items"])
        for i, (num, label) in enumerate(st["items"]):
            x0, x1 = W * i / n, W * (i + 1) / n
            text_fit(img, (x0 + 6, H * 0.34, x1 - 6, H * 0.74), num, self.c["pink"])
            text_fit(img, (x0 + 6, H * 0.76, x1 - 6, H * 0.96), label, "#6b6168")
        return self.save("stats", img)

    def tracks(self, p):
        h_m = p["y"][1] - p["y"][0]
        img = canvas(p["w"], h_m, "#ffffff")
        W, H = img.size
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, W, round(H * 0.2)), fill=hex_rgb(self.c["pink"]))
        text_fit(img, (8, 4, W - 8, round(H * 0.2) - 4), p["title"], "#ffffff")
        text_fit(img, (8, round(H * 0.21), W - 8, round(H * 0.3)), p["sub"], "#6b6168")
        for i, (name, path) in enumerate(p["tracks"]):
            y = H * (0.36 + 0.21 * i)
            text_fit(img, (12, y, W - 12, y + H * 0.09), name, self.c["navy"])
            text_fit(img, (12, y + H * 0.09, W - 12, y + H * 0.16), path, "#231F20")
        return self.save("tracks", img)

    def floor_text(self, name, s, w_m, color):
        img = canvas(w_m, w_m * 0.09, self.c["pink"])
        text_fit(img, (4, 2, img.width - 4, img.height - 2), s, color)
        return self.save(name, img)

    def door(self, w_m, h_m, label):
        img = canvas(w_m, h_m, "#ececee")
        W, H = img.size
        d = ImageDraw.Draw(img)
        d.rectangle((4, 4, W - 5, H - 5), outline=(190, 190, 196), width=4)
        text_fit(img, (W * 0.15, H * 0.30, W * 0.85, H * 0.36), label, "#231F20")
        d.ellipse((W * 0.82, H * 0.50, W * 0.86, H * 0.53), fill=(150, 150, 156))
        return self.save("door", img)

    def screen(self, name, file, aspect=16 / 9):
        img = Image.new("RGB", (640, round(640 / aspect)), (12, 12, 14))
        return self.save(name, paste_fit(img, IMAGES / file, (0, 0, img.width, img.height)))

    def qr_bubble(self, items, w_m, h_m):
        img = canvas(w_m, h_m, self.c["pink"])
        W, H = img.size
        for i, (key, label) in enumerate(items):
            x0 = W * (0.06 if i == 0 else 0.40)
            y0 = H * (0.04 if i == 0 else 0.50)
            bw, bh = W * 0.54, H * 0.44
            d = ImageDraw.Draw(img)
            d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=18, fill=(255, 255, 255))
            paste_fit(img, Image.open(IMAGES / f"qr_{key}.png").resize((256, 256), Image.NEAREST), (round(x0 + bw * 0.12), round(y0 + bh * 0.06), round(x0 + bw * 0.88), round(y0 + bh * 0.76)))
            text_fit(img, (x0 + 8, y0 + bh * 0.78, x0 + bw - 8, y0 + bh * 0.96), label, "#231F20")
        return self.save("qr", img)
