import io
import math
import os
import random
import zipfile
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

import streamlit as st
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

# ======================================================================
#  PHOTO ALBUM MAKER  -  12 designs, live gallery, photo manager
# ======================================================================

CARD_TEXT = (70, 60, 55)

FORMATS = {
    "A4 Portrait (khadi)": (1654, 2339),
    "A4 Landscape (aadi)": (2339, 1654),
    "Square (Instagram)": (2000, 2000),
}

FILTERS = ["Design default", "Original", "Enhance", "B&W", "Sepia", "Warm", "Cool", "Vivid"]

PALETTES = {
    "Classic White": dict(bg=(250, 249, 246), fg=(35, 35, 35), accent=(176, 141, 87), card=(255, 255, 255)),
    "Dark Elegant": dict(bg=(26, 26, 31), fg=(240, 236, 228), accent=(212, 175, 55), card=(246, 241, 231)),
    "Soft Pink": dict(bg=(252, 235, 239), fg=(110, 45, 70), accent=(214, 96, 135), card=(255, 252, 252)),
    "Ocean Blue": dict(bg=(228, 241, 249), fg=(20, 55, 90), accent=(40, 120, 190), card=(255, 255, 255)),
    "Vintage Cream": dict(bg=(242, 231, 212), fg=(84, 58, 36), accent=(150, 100, 55), card=(253, 249, 240)),
    "Forest Green": dict(bg=(226, 238, 226), fg=(28, 62, 44), accent=(60, 130, 90), card=(255, 255, 252)),
}

# margin = (left, top, right, bottom) of the photo area, in base units (A4 @200dpi)
DESIGNS = {
    "Modern Magazine": dict(
        emoji="📰", desc="Full-photo cover, clean cards, golden frame",
        bg="paper", frame="shadow", cover="full", deco="magazine",
        margin=(110, 220, 110, 170), gap=44, radius=24, border=10, filt="Enhance",
        pal=dict(bg=(250, 249, 246), bg2=(236, 232, 222), fg=(35, 35, 35), accent=(176, 141, 87), card=(255, 255, 255))),
    "Polaroid Scrapbook": dict(
        emoji="📸", desc="Tape-lagi tedhi Polaroid cards, kraft paper",
        bg="paper", frame="polaroid", cover="polaroid", deco="page_no",
        margin=(80, 100, 80, 170), gap=40, radius=0, border=0, filt="Warm",
        pal=dict(bg=(228, 212, 186), bg2=(210, 190, 160), fg=(75, 52, 36), accent=(196, 86, 86), card=(253, 250, 243))),
    "Cinematic Blur": dict(
        emoji="🎬", desc="Photo ka blur background, movie poster jaisa",
        bg="blur", frame="shadow", cover="blur", deco="page_no",
        margin=(110, 120, 110, 190), gap=44, radius=20, border=14, filt="Enhance",
        pal=dict(bg=(20, 20, 24), bg2=(0, 0, 0), fg=(255, 255, 255), accent=(230, 190, 110), card=(255, 255, 255))),
    "Minimal Gallery": dict(
        emoji="🖼️", desc="Safed gallery wall jaisa, bahut saaf aur simple",
        bg="solid", frame="plain", cover="framed", deco="minimal",
        margin=(170, 170, 170, 230), gap=64, radius=0, border=0, filt="Original",
        pal=dict(bg=(255, 255, 255), bg2=(240, 240, 240), fg=(30, 30, 30), accent=(160, 160, 160), card=(255, 255, 255))),
    "Film Strip": dict(
        emoji="🎞️", desc="Purani film roll jaisa black frame aur holes",
        bg="solid", frame="film", cover="framed", deco="page_no",
        margin=(100, 140, 100, 200), gap=40, radius=0, border=0, filt="Enhance",
        pal=dict(bg=(24, 24, 27), bg2=(10, 10, 12), fg=(236, 236, 236), accent=(240, 190, 60), card=(255, 255, 255))),
    "Vintage Sepia": dict(
        emoji="🕰️", desc="Purani yaadon wala sepia, double frame",
        bg="paper", frame="matted", cover="framed", deco="frame_double",
        margin=(140, 150, 140, 200), gap=48, radius=0, border=26, filt="Sepia",
        pal=dict(bg=(240, 228, 205), bg2=(222, 205, 176), fg=(84, 58, 36), accent=(140, 95, 55), card=(250, 243, 226))),
    "Black & White": dict(
        emoji="⚫", desc="Classic black & white, moti kaali border",
        bg="solid", frame="shadow", cover="framed", deco="minimal",
        margin=(130, 150, 130, 220), gap=52, radius=0, border=20, filt="B&W",
        pal=dict(bg=(236, 236, 236), bg2=(220, 220, 220), fg=(16, 16, 16), accent=(16, 16, 16), card=(16, 16, 16))),
    "Gold Luxe": dict(
        emoji="✨", desc="Wedding / royal look: navy + golden frame",
        bg="gradient", frame="matted", cover="framed", deco="frame_double",
        margin=(150, 160, 150, 210), gap=50, radius=0, border=30, filt="Enhance",
        pal=dict(bg=(10, 14, 30), bg2=(32, 38, 70), fg=(236, 226, 200), accent=(205, 170, 95), card=(244, 236, 216))),
    "Neon Glow": dict(
        emoji="🌃", desc="Night-party style, glowing neon border",
        bg="gradient", frame="glow", cover="framed", deco="page_no",
        margin=(130, 140, 130, 200), gap=60, radius=14, border=0, filt="Vivid",
        pal=dict(bg=(26, 10, 52), bg2=(6, 24, 64), fg=(240, 240, 255), accent=(255, 64, 200), card=(255, 255, 255))),
    "Postage Stamp": dict(
        emoji="✉️", desc="Travel album: har photo ek dak-ticket jaisi",
        bg="paper", frame="stamp", cover="framed", deco="page_no",
        margin=(110, 140, 110, 200), gap=50, radius=0, border=0, filt="Enhance",
        pal=dict(bg=(214, 226, 235), bg2=(196, 212, 224), fg=(30, 60, 80), accent=(200, 70, 60), card=(255, 253, 246))),
    "Pastel Confetti": dict(
        emoji="🎉", desc="Birthday / kids ke liye rangeen confetti",
        bg="confetti", frame="shadow", cover="framed", deco="page_no",
        margin=(120, 140, 120, 190), gap=50, radius=40, border=16, filt="Vivid",
        pal=dict(bg=(255, 245, 248), bg2=(255, 232, 240), fg=(110, 60, 100), accent=(255, 120, 150), card=(255, 255, 255),
                 confetti=[(255, 154, 162), (255, 218, 193), (181, 234, 215), (199, 206, 234), (255, 236, 153)])),
    "Full-Bleed Mosaic": dict(
        emoji="🧩", desc="Edge-to-edge tight collage, koi margin nahi",
        bg="solid", frame="plain", cover="full", deco="none",
        margin=(0, 0, 0, 0), gap=8, radius=0, border=0, filt="Enhance",
        pal=dict(bg=(8, 8, 8), bg2=(0, 0, 0), fg=(255, 255, 255), accent=(255, 255, 255), card=(255, 255, 255))),
}


# ----------------------------------------------------------------------
#  Context
# ----------------------------------------------------------------------
@dataclass
class Ctx:
    W: int
    H: int
    K: float
    d: dict
    pal: dict
    title: str
    subtitle: str
    radius: int
    gap: int
    border: int
    grain: object = None

    def u(self, v):
        r = int(round(v * self.K))
        return r if v == 0 else max(1, r)

    @property
    def landscape(self):
        return self.W > self.H * 1.05


def mix(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def palette_from(p):
    q = dict(p)
    q["bg2"] = mix(p["bg"], p["fg"], 0.18)
    a = p["accent"]
    q["confetti"] = [a, mix(a, p["bg"], 0.5), mix(p["fg"], p["bg"], 0.55), mix(a, (255, 255, 255), 0.5)]
    return q


def make_ctx(design_name, pal_name, fmt_name, title, subtitle, custom, K):
    d = DESIGNS[design_name]
    pal = dict(d["pal"]) if pal_name == "Design default" else palette_from(PALETTES[pal_name])
    if d["bg"] == "blur":
        pal["fg"] = (255, 255, 255)
    bw, bh = FORMATS[fmt_name]
    W, H = max(40, int(round(bw * K))), max(40, int(round(bh * K)))
    c = custom or {}
    ctx = Ctx(W, H, K, d, pal, title or "My Album", subtitle or "",
              c.get("radius", d["radius"]), c.get("gap", d["gap"]), c.get("border", d["border"]))
    if d["bg"] in ("paper", "confetti"):
        ctx.grain = Image.effect_noise((W, H), 30).convert("RGB")
    return ctx


# ----------------------------------------------------------------------
#  Fonts & text
# ----------------------------------------------------------------------
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


@lru_cache(maxsize=256)
def get_font(size, kind="title"):
    """Tip: fonts/ folder me title.ttf / body.ttf daalo to apna font use hoga."""
    size = max(8, int(size))
    names = [os.path.join(FONT_DIR, "title.ttf" if kind == "title" else "body.ttf")]
    if kind == "title":
        names += ["DejaVuSerif-Bold.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"]
    else:
        names += ["DejaVuSans.ttf", "Arial.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def fit_font(d, text, max_w, size, kind="title"):
    size = max(8, int(size))
    font = get_font(size, kind)
    while size > 10 and d.textlength(text, font=font) > max_w:
        size = int(size * 0.93)
        font = get_font(size, kind)
    return font


def spaced_text(d, cx, cy, text, font, fill, spacing=10):
    text = text.upper()
    widths = [d.textlength(ch, font=font) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        d.text((x, cy), ch, font=font, fill=fill, anchor="lm")
        x += w + spacing


# ----------------------------------------------------------------------
#  Photo filters
# ----------------------------------------------------------------------
def apply_filter(img, name):
    if name == "Original":
        return img
    if name == "Enhance":
        img = ImageOps.autocontrast(img, cutoff=1)
        img = ImageEnhance.Color(img).enhance(1.12)
        img = ImageEnhance.Contrast(img).enhance(1.05)
        return ImageEnhance.Sharpness(img).enhance(1.15)
    if name == "B&W":
        g = ImageOps.autocontrast(ImageOps.grayscale(img), cutoff=1)
        return ImageEnhance.Contrast(g).enhance(1.1).convert("RGB")
    if name == "Sepia":
        g = ImageOps.autocontrast(ImageOps.grayscale(img), cutoff=1)
        return ImageOps.colorize(g, (35, 20, 8), (255, 242, 220), mid=(150, 105, 65))
    if name in ("Warm", "Cool"):
        r, g, b = img.split()
        up, down = (1.07, 0.9) if name == "Warm" else (0.9, 1.07)
        r = r.point(lambda p: min(255, int(p * up)))
        b = b.point(lambda p: min(255, int(p * down)))
        return ImageEnhance.Color(Image.merge("RGB", (r, g, b))).enhance(1.08)
    if name == "Vivid":
        img = ImageEnhance.Color(img).enhance(1.35)
        img = ImageEnhance.Contrast(img).enhance(1.1)
        return ImageEnhance.Sharpness(img).enhance(1.2)
    return img


# ----------------------------------------------------------------------
#  Low-level drawing helpers
# ----------------------------------------------------------------------
def rr_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=max(0, r), fill=255)
    return m


def mask_shadow(canvas, mask, x, y, blur, opacity, color=(0, 0, 0), offset=(0, 0)):
    pad = blur * 3
    big = Image.new("L", (mask.width + 2 * pad, mask.height + 2 * pad), 0)
    big.paste(mask, (pad, pad))
    big = big.filter(ImageFilter.GaussianBlur(blur)).point(lambda p: int(p * opacity))
    canvas.paste(color, (x - pad + offset[0], y - pad + offset[1]), big)


def add_caption(ctx, photo, text):
    w, h = photo.size
    bh = min(int(h * 0.22), ctx.u(130))
    if bh < 6:
        return
    g = Image.linear_gradient("L").resize((w, bh)).point(lambda p: int(p * 0.78))
    photo.paste((0, 0, 0), (0, h - bh), g)
    d = ImageDraw.Draw(photo)
    font = fit_font(d, text, w - ctx.u(40), ctx.u(40), "body")
    d.text((w / 2, h - bh * 0.35), text, font=font, fill=(255, 255, 255), anchor="mm")


def cropped(ctx, img, w, h, caption=""):
    p = ImageOps.fit(img, (max(1, w), max(1, h)), Image.LANCZOS, centering=(0.5, 0.4))
    if caption:
        add_caption(ctx, p, caption)
    return p


def gradient_overlay(canvas, ctx, y0, y1, max_alpha=0.85):
    g = Image.linear_gradient("L").resize((ctx.W, max(1, y1 - y0)))
    g = g.point(lambda p: int(p * max_alpha))
    canvas.paste((0, 0, 0), (0, y0), g)


def polaroid(ctx, img, w, h, angle, caption, rng):
    card_color = ctx.pal["card"]
    side = max(2, int(w * 0.05))
    bottom = int(h * 0.17)
    card = Image.new("RGBA", (w, h), card_color + (255,))
    inner = ImageOps.fit(img, (w - 2 * side, h - side - bottom), Image.LANCZOS, centering=(0.5, 0.4))
    card.paste(inner, (side, side))
    if caption:
        cd = ImageDraw.Draw(card)
        font = fit_font(cd, caption, w - 2 * side - ctx.u(20), int(bottom * 0.5))
        cd.text((w / 2, h - bottom / 2 - ctx.u(6)), caption, font=font, fill=CARD_TEXT, anchor="mm")
    tape_w, tape_h = max(8, int(w * 0.32)), max(int(h * 0.055), 6)
    pad = tape_h // 2
    full = Image.new("RGBA", (w, h + pad), card_color + (0,))
    full.paste(card, (0, pad))
    tape = Image.new("RGBA", (tape_w, tape_h), ctx.pal["accent"] + (150,))
    tape = tape.rotate(rng.uniform(-6, 6), expand=True, resample=Image.BICUBIC)
    full.alpha_composite(tape, (max(w // 2 - tape.width // 2, 0), 0))
    return full.rotate(angle, expand=True, resample=Image.BICUBIC)


def place_rgba(canvas, ctx, rgba, cx, cy):
    x, y = int(cx - rgba.width / 2), int(cy - rgba.height / 2)
    alpha = rgba.split()[3]
    mask_shadow(canvas, alpha, x, y, ctx.u(16), 0.4, (0, 0, 0), (ctx.u(10), ctx.u(22)))
    canvas.paste(rgba.convert("RGB"), (x, y), alpha)


# ----------------------------------------------------------------------
#  Photo frames
# ----------------------------------------------------------------------
def render_photo(canvas, ctx, img, caption, box, rng, frame=None):
    frame = frame or ctx.d["frame"]
    x, y, w, h = [int(v) for v in box]
    if w < 8 or h < 8:
        return
    u, pal = ctx.u, ctx.pal
    rpx = u(ctx.radius) if ctx.radius else 0

    if frame == "polaroid":
        ratio = 1.15 if img.width >= img.height else 0.8
        cw = min(w * 0.88, h * 0.88 * ratio)
        ch = cw / ratio
        angle = rng.choice([-1, 1]) * rng.uniform(1.5, 5)
        place_rgba(canvas, ctx, polaroid(ctx, img, int(cw), int(ch), angle, caption, rng), x + w / 2, y + h / 2)
        return

    shadows = [(u(26), 0.38, (0, 0, 0), (0, u(18)))]

    if frame in ("shadow", "plain", "glow"):
        b = u(7) if frame == "glow" else (u(ctx.border) if ctx.border else 0)
        b = min(b, w // 4, h // 4)
        if b > 0:
            tile = Image.new("RGB", (w, h), pal["accent"] if frame == "glow" else pal["card"])
            tile.paste(cropped(ctx, img, w - 2 * b, h - 2 * b, caption), (b, b))
        else:
            tile = cropped(ctx, img, w, h, caption)
        mask = rr_mask(w, h, rpx)
        if frame == "plain":
            shadows = []
        elif frame == "glow":
            shadows = [(u(40), 0.9, pal["accent"], (0, 0)), (u(12), 0.9, pal["accent"], (0, 0))]

    elif frame == "matted":
        inset = min(max(u(ctx.border), u(22)), w // 4, h // 4)
        tile = Image.new("RGB", (w, h), pal["card"])
        tile.paste(cropped(ctx, img, w - 2 * inset, h - 2 * inset, caption), (inset, inset))
        td = ImageDraw.Draw(tile)
        lw, g, o = max(1, u(2)), u(6), u(8)
        td.rectangle((inset - g, inset - g, w - inset + g - 1, h - inset + g - 1), outline=pal["accent"], width=lw)
        td.rectangle((o, o, w - o - 1, h - o - 1), outline=pal["accent"], width=lw)
        mask = rr_mask(w, h, rpx)
        shadows = [(u(22), 0.32, (0, 0, 0), (0, u(14)))]

    elif frame == "film":
        band, side = min(u(40), h // 4, w // 4), u(14)
        tile = Image.new("RGB", (w, h), (14, 14, 16))
        td = ImageDraw.Draw(tile)
        hw, hh, pitch, hole = u(20), u(26), u(46), (232, 228, 218)
        if w >= h:
            iw, ih, ix, iy = w - 2 * side, h - 2 * band, side, band
            n = max(2, (w - 2 * side) // pitch)
            for i in range(n):
                cx = side + (i + 0.5) * (w - 2 * side) / n
                for cy in (band / 2, h - band / 2):
                    td.rounded_rectangle((cx - hw / 2, cy - hh / 2, cx + hw / 2, cy + hh / 2), radius=max(1, u(5)), fill=hole)
        else:
            iw, ih, ix, iy = w - 2 * band, h - 2 * side, band, side
            n = max(2, (h - 2 * side) // pitch)
            for i in range(n):
                cy = side + (i + 0.5) * (h - 2 * side) / n
                for cx in (band / 2, w - band / 2):
                    td.rounded_rectangle((cx - hh / 2, cy - hw / 2, cx + hh / 2, cy + hw / 2), radius=max(1, u(5)), fill=hole)
        tile.paste(cropped(ctx, img, iw, ih, caption), (ix, iy))
        mask = rr_mask(w, h, u(10))

    elif frame == "stamp":
        edge = min(u(34), w // 5, h // 5)
        tile = Image.new("RGB", (w, h), pal["card"])
        tile.paste(cropped(ctx, img, w - 2 * edge, h - 2 * edge, caption), (edge, edge))
        mask = Image.new("L", (w, h), 255)
        md = ImageDraw.Draw(mask)
        r, pitch = max(2, u(11)), u(36)
        nx, ny = max(3, round(w / pitch)), max(3, round(h / pitch))
        for i in range(nx + 1):
            cx = i * w / nx
            md.ellipse((cx - r, -r, cx + r, r), fill=0)
            md.ellipse((cx - r, h - 1 - r, cx + r, h - 1 + r), fill=0)
        for j in range(ny + 1):
            cy = j * h / ny
            md.ellipse((-r, cy - r, r, cy + r), fill=0)
            md.ellipse((w - 1 - r, cy - r, w - 1 + r, cy + r), fill=0)
    else:
        tile, mask = cropped(ctx, img, w, h, caption), rr_mask(w, h, rpx)

    for blur, op, col, off in shadows:
        mask_shadow(canvas, mask, x, y, blur, op, col, off)
    canvas.paste(tile, (x, y), mask)


# ----------------------------------------------------------------------
#  Backgrounds, decoration, layouts
# ----------------------------------------------------------------------
def make_bg(ctx, page_no, img=None, darken=0.55):
    t, pal, W, H = ctx.d["bg"], ctx.pal, ctx.W, ctx.H
    if t == "blur" and img is not None:
        small = ImageOps.fit(img, (max(8, W // 10), max(8, H // 10)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(4))
        bg = small.resize((W, H), Image.BICUBIC)
        return Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), darken)
    if t == "gradient":
        g = Image.linear_gradient("L").resize((W, H), Image.BILINEAR)
        return ImageOps.colorize(g, pal["bg"], pal["bg2"])
    base = Image.new("RGB", (W, H), pal["bg"])
    if t in ("paper", "confetti") and ctx.grain is not None:
        base = Image.blend(base, ctx.grain, 0.035)
    if t == "confetti":
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        rr = random.Random(page_no * 7 + 3)
        cols = pal.get("confetti") or [pal["accent"]]
        for _ in range(70):
            s = rr.randint(ctx.u(14), ctx.u(54))
            x, y = rr.randint(0, W), rr.randint(0, H)
            c = rr.choice(cols) + (120,)
            k = rr.random()
            if k < 0.5:
                od.ellipse((x, y, x + s, y + s), fill=c)
            elif k < 0.8:
                od.rounded_rectangle((x, y, x + s, y + s), radius=s // 4, fill=c)
            else:
                od.polygon([(x + s / 2, y), (x + s, y + s), (x, y + s)], fill=c)
        base = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")
    return base


def decorate(canvas, ctx, page_no=None):
    d = ImageDraw.Draw(canvas)
    u, W, H = ctx.u, ctx.W, ctx.H
    deco, fg, acc = ctx.d["deco"], ctx.pal["fg"], ctx.pal["accent"]
    cover = page_no is None
    if deco == "magazine":
        d.rectangle((u(55), u(55), W - u(55), H - u(55)), outline=acc, width=u(3))
        if not cover:
            spaced_text(d, W / 2, u(125), ctx.title, get_font(u(36), "body"), fg, u(14))
            d.line((W / 2 - u(110), u(165), W / 2 + u(110), u(165)), fill=acc, width=u(4))
    elif deco == "frame_double":
        d.rectangle((u(50), u(50), W - u(50), H - u(50)), outline=acc, width=u(4))
        d.rectangle((u(72), u(72), W - u(72), H - u(72)), outline=acc, width=max(1, u(2)))
    if cover or deco == "none":
        return
    if deco == "minimal":
        f = get_font(u(30), "body")
        d.text((u(170), H - u(120)), ctx.title.upper(), font=f, fill=fg, anchor="lm")
        d.text((W - u(170), H - u(120)), f"{page_no:02d}", font=f, fill=fg, anchor="rm")
        return
    d.line((W / 2 - u(50), H - u(135), W / 2 + u(50), H - u(135)), fill=acc, width=max(1, u(3)))
    spaced_text(d, W / 2, H - u(95), f"{page_no:02d}", get_font(u(34), "body"), fg, u(8))


def choose_layout(items, landscape_page):
    n = len(items)
    land = lambda it: it["img"].width >= it["img"].height
    two_by_two = [(0, 0, 0.5, 0.5), (0.5, 0, 0.5, 0.5), (0, 0.5, 0.5, 0.5), (0.5, 0.5, 0.5, 0.5)]
    if n == 1:
        return [(0, 0, 1, 1)]
    if landscape_page:
        if n == 2:
            return [(0, 0, 0.5, 1), (0.5, 0, 0.5, 1)]
        if n == 3:
            return [(0, 0, 0.6, 1), (0.6, 0, 0.4, 0.5), (0.6, 0.5, 0.4, 0.5)]
        return two_by_two
    if n == 2:
        if land(items[0]) and land(items[1]):
            return [(0, 0, 1, 0.5), (0, 0.5, 1, 0.5)]
        return [(0, 0, 0.5, 1), (0.5, 0, 0.5, 1)]
    if n == 3:
        if land(items[0]):
            return [(0, 0, 1, 0.55), (0, 0.55, 0.5, 0.45), (0.5, 0.55, 0.5, 0.45)]
        return [(0, 0, 0.6, 1), (0.6, 0, 0.4, 0.5), (0.6, 0.5, 0.4, 0.5)]
    return two_by_two


def cell_boxes(ctx, items):
    ml, mt, mr, mb = [ctx.u(v) for v in ctx.d["margin"]]
    ax, ay, aw, ah = ml, mt, ctx.W - ml - mr, ctx.H - mt - mb
    gap = ctx.u(ctx.gap)
    return [
        (int(ax + fx * aw + gap / 2), int(ay + fy * ah + gap / 2), int(fw * aw - gap), int(fh * ah - gap))
        for fx, fy, fw, fh in choose_layout(items, ctx.landscape)
    ]


# ----------------------------------------------------------------------
#  Pages, cover, back cover
# ----------------------------------------------------------------------
def make_page(ctx, items, page_no):
    canvas = make_bg(ctx, page_no, items[0]["img"])
    rng = random.Random(page_no)
    for it, box in zip(items, cell_boxes(ctx, items)):
        render_photo(canvas, ctx, it["img"], it["caption"], box, rng)
    decorate(canvas, ctx, page_no)
    return canvas


def make_cover(ctx, hero):
    kind, u, W, H, pal = ctx.d["cover"], ctx.u, ctx.W, ctx.H, ctx.pal
    rng = random.Random(1)
    white = (255, 255, 255)

    if kind == "full":
        canvas = ImageOps.fit(hero, (W, H), Image.LANCZOS, centering=(0.5, 0.4))
        gradient_overlay(canvas, ctx, int(H * 0.48), H, 0.9)
        d = ImageDraw.Draw(canvas)
        d.rectangle((u(50), u(50), W - u(50), H - u(50)), outline=white, width=u(3))
        spaced_text(d, W / 2, u(150), "Photo Album", get_font(u(40), "body"), white, u(16))
        font = fit_font(d, ctx.title, W - 2 * u(140), u(160))
        d.text((W / 2, H - u(520)), ctx.title, font=font, fill=white, anchor="mm")
        d.line((W / 2 - u(150), H - u(420), W / 2 + u(150), H - u(420)), fill=pal["accent"], width=u(6))
        if ctx.subtitle:
            spaced_text(d, W / 2, H - u(340), ctx.subtitle, get_font(u(46), "body"), white, u(14))
        return canvas

    if kind == "polaroid":
        canvas = make_bg(ctx, 0, hero)
        d = ImageDraw.Draw(canvas)
        ch = int(H * 0.64)
        cw = int(min(W * 0.7, ch * 0.77))
        place_rgba(canvas, ctx, polaroid(ctx, hero, cw, ch, -3, ctx.title, rng), W / 2, H * 0.47)
        d.line((W / 2 - u(150), H * 0.855, W / 2 + u(150), H * 0.855), fill=pal["accent"], width=u(5))
        if ctx.subtitle:
            spaced_text(d, W / 2, H * 0.905, ctx.subtitle, get_font(u(46), "body"), pal["fg"], u(14))
        return canvas

    canvas = make_bg(ctx, 0, hero, 0.45)
    d = ImageDraw.Draw(canvas)
    if kind == "blur":
        bw, bh = int(W * 0.78), int(H * 0.64)
        render_photo(canvas, ctx, hero, "", ((W - bw) // 2, int(H * 0.08), bw, bh), rng, frame="shadow")
        ty, ly, sy = H * 0.865, None, H * 0.925
    else:  # framed (uses the design's own frame style)
        bw, bh = int(W * 0.76), int(H * 0.62)
        render_photo(canvas, ctx, hero, "", ((W - bw) // 2, int(H * 0.085), bw, bh), rng)
        decorate(canvas, ctx, None)
        ty, ly, sy = H * 0.80, H * 0.86, H * 0.91
    font = fit_font(d, ctx.title, W * 0.8, u(130))
    d.text((W / 2, ty), ctx.title, font=font, fill=pal["fg"], anchor="mm")
    if ly:
        d.line((W / 2 - u(140), ly, W / 2 + u(140), ly), fill=pal["accent"], width=max(1, u(5)))
    if ctx.subtitle:
        spaced_text(d, W / 2, sy, ctx.subtitle, get_font(u(44), "body"), pal["fg"], u(14))
    return canvas


def make_back(ctx, last):
    canvas = make_bg(ctx, 999, last, 0.6)
    decorate(canvas, ctx, None)
    d = ImageDraw.Draw(canvas)
    u, W, H, pal = ctx.u, ctx.W, ctx.H, ctx.pal
    font = fit_font(d, "Thank You", W - 2 * u(110), u(150))
    d.text((W / 2, H / 2 - u(40)), "Thank You", font=font, fill=pal["fg"], anchor="mm")
    d.line((W / 2 - u(160), H / 2 + u(60), W / 2 + u(160), H / 2 + u(60)), fill=pal["accent"], width=max(1, u(6)))
    spaced_text(d, W / 2, H / 2 + u(135), ctx.title, get_font(u(42), "body"), pal["fg"], u(12))
    return canvas


def plan_pages(n, per):
    pattern = [3, 2, 4, 1] if per == "Auto mix" else [int(per)]
    out, i, k = [], 0, 0
    while i < n:
        c = min(pattern[k % len(pattern)], n - i)
        out.append(c)
        i += c
        k += 1
    return out


def build_album(ctx, items, cover_idx, per, back_cover, filt, progress=None):
    """items: list of dicts {img (PIL), caption}. Returns list of PIL pages."""
    counts = plan_pages(len(items), per)
    total = len(counts) + 1 + (1 if back_cover else 0)
    done = 0

    def tick(msg):
        nonlocal done
        done += 1
        if progress:
            progress(done / total, msg)

    pages = [make_cover(ctx, items[cover_idx]["img"])]
    tick("Cover ban gaya")
    i = 0
    for c in counts:
        pages.append(make_page(ctx, items[i:i + c], len(pages)))
        i += c
        tick(f"Page {len(pages) - 1} ready")
    if back_cover:
        pages.append(make_back(ctx, items[-1]["img"]))
        tick("Last page ready")
    return pages


def decode_item(data, filt, maxsize=2000):
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    im.thumbnail((maxsize, maxsize))
    return apply_filter(im, filt)


def export_outputs(pages):
    jpgs = []
    for p in pages:
        b = io.BytesIO()
        p.save(b, "JPEG", quality=90)
        jpgs.append(b.getvalue())
    pdf = io.BytesIO()
    pages[0].save(pdf, "PDF", save_all=True, append_images=pages[1:], resolution=200.0, quality=92)
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, "w", zipfile.ZIP_DEFLATED) as z:
        for i, j in enumerate(jpgs, 1):
            z.writestr(f"album_page_{i:02d}.jpg", j)
    return jpgs, pdf.getvalue(), zb.getvalue()


# ----------------------------------------------------------------------
#  Sample photos (design preview, jab tak photos upload na hon)
# ----------------------------------------------------------------------
def _scene(w, h, top, bottom, sun, hill1, hill2):
    img = ImageOps.colorize(Image.linear_gradient("L").resize((w, h)), top, bottom)
    d = ImageDraw.Draw(img)
    r = int(min(w, h) * 0.12)
    sx, sy = int(w * sun[0]), int(h * sun[1])
    d.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(255, 238, 190))
    for base, amp, col in ((0.72, 0.07, hill1), (0.84, 0.06, hill2)):
        pts = [(x, int(h * base + math.sin(x / w * 6.0 + amp * 20) * h * amp)) for x in range(0, w + 8, 8)]
        d.polygon(pts + [(w, h), (0, h)], fill=col)
    return img


@st.cache_resource
def sample_images():
    return [
        _scene(700, 480, (255, 170, 110), (120, 70, 140), (0.7, 0.45), (90, 50, 110), (50, 30, 80)),
        _scene(480, 700, (90, 140, 220), (200, 225, 245), (0.3, 0.3), (60, 110, 90), (35, 80, 65)),
        _scene(700, 500, (120, 200, 240), (235, 245, 255), (0.25, 0.28), (70, 150, 90), (40, 110, 70)),
        _scene(600, 600, (250, 170, 200), (255, 230, 215), (0.65, 0.4), (200, 110, 140), (160, 80, 110)),
    ]


@st.cache_data(show_spinner=False, max_entries=300)
def design_preview(design_name, pal_name, fmt_name, filt_name, title, subtitle, sig, _thumbs):
    ctx = make_ctx(design_name, pal_name, fmt_name, title, subtitle, None, 0.28)
    filt = ctx.d["filt"] if filt_name == "Design default" else filt_name
    imgs = [apply_filter(t, filt) for t in _thumbs]
    cover = make_cover(ctx, imgs[0])
    chosen = [{"img": imgs[(i + 1) % len(imgs)], "caption": ""} for i in range(3)]
    page = make_page(ctx, chosen, 1)
    gap = max(8, int(ctx.W * 0.05))
    sheet = Image.new("RGB", (ctx.W * 2 + gap, ctx.H), (238, 238, 246))
    sheet.paste(cover, (0, 0))
    sheet.paste(page, (ctx.W + gap, 0))
    buf = io.BytesIO()
    sheet.save(buf, "JPEG", quality=88)
    return buf.getvalue()


# ======================================================================
#  UI
# ======================================================================
CSS = """
<style>
.block-container {padding-top: 1.4rem; max-width: 1250px;}
.hero {background: linear-gradient(120deg,#6a11cb 0%,#2575fc 55%,#ff6ec4 130%);
       border-radius: 20px; padding: 26px 32px; color: #fff; margin-bottom: 16px;
       box-shadow: 0 10px 30px rgba(80,60,200,.25);}
.hero h1 {margin: 0; font-size: 2.1rem; color: #fff; padding: 0;}
.hero p {margin: 6px 0 0 0; opacity: .93; font-size: 1.02rem;}
.stButton > button, .stDownloadButton > button {
    border-radius: 12px; font-weight: 600; padding: .5rem 1rem;
    border: 1px solid rgba(120,120,170,.35); transition: all .15s ease;}
.stButton > button:hover, .stDownloadButton > button:hover {
    transform: translateY(-1px); box-shadow: 0 6px 16px rgba(90,80,170,.25);}
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"],
.stDownloadButton > button[kind="primary"], .stDownloadButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(90deg,#7b2ff7,#f107a3); color: #fff; border: none;}
.stTabs [data-baseweb="tab-list"] {gap: 6px;}
.stTabs [data-baseweb="tab"] {border-radius: 10px 10px 0 0; padding: 10px 18px; font-weight: 600;}
.pill {display: inline-block; padding: 3px 12px; border-radius: 999px;
       background: rgba(123,47,247,.13); font-size: .82rem; margin: 2px 6px 2px 0;}
.dname {font-weight: 700; font-size: 1.05rem; margin: 4px 0 0 0;}
.ddesc {opacity: .72; font-size: .86rem; margin-bottom: 8px;}
</style>
"""


def _init_state():
    ss = st.session_state
    ss.setdefault("photos", [])
    ss.setdefault("seen", set())
    ss.setdefault("up_n", 0)
    ss.setdefault("next_id", 1)
    ss.setdefault("cover_id", None)
    ss.setdefault("design", "Modern Magazine")
    ss.setdefault("result", None)


def _sync_uploads(files):
    ss = st.session_state
    for f in files or []:
        key = (f.name, f.size)
        if key in ss.seen:
            continue
        ss.seen.add(key)
        data = f.getvalue()
        try:
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
        except Exception:
            continue
        th = im.copy()
        th.thumbnail((700, 700))
        ss.photos.append({"id": ss.next_id, "name": f.name, "data": data, "thumb": th, "caption": ""})
        ss.next_id += 1


def _move(i, delta):
    items, j = st.session_state.photos, i + delta
    if 0 <= j < len(items):
        items[i], items[j] = items[j], items[i]


def _delete(item_id):
    st.session_state.photos = [it for it in st.session_state.photos if it["id"] != item_id]


def _set_cover(item_id):
    st.session_state.cover_id = item_id


def _sort(mode):
    items = st.session_state.photos
    if mode == "az":
        items.sort(key=lambda x: x["name"].lower())
    elif mode == "za":
        items.sort(key=lambda x: x["name"].lower(), reverse=True)
    elif mode == "shuffle":
        random.shuffle(items)
    elif mode == "reverse":
        items.reverse()


def _clear():
    ss = st.session_state
    ss.photos, ss.seen, ss.cover_id, ss.result = [], set(), None, None
    ss.up_n += 1


def _pick_design(name):
    st.session_state.design = name


def _surprise():
    st.session_state.design = random.choice(list(DESIGNS))


def main():
    st.set_page_config(page_title="Photo Album Maker", page_icon="📸", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    _init_state()
    ss = st.session_state

    st.markdown(
        '<div class="hero"><h1>📸 Photo Album Maker</h1>'
        "<p>Photos upload karo → apna design chuno → ek sundar album PDF me download karo.</p></div>",
        unsafe_allow_html=True,
    )

    tab_photos, tab_design, tab_settings, tab_album = st.tabs(
        ["📷 1. Photos", "🎨 2. Design chuno", "⚙️ 3. Settings", "📖 4. Album & Download"]
    )

    # ---------------------------------------------------------------- Photos
    with tab_photos:
        files = st.file_uploader(
            "Photos yahan daalo (ek saath kai)", type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True, key=f"up_{ss.up_n}",
        )
        _sync_uploads(files)
        items = ss.photos
        if not items:
            st.info("Abhi koi photo nahi hai. Upar se upload karo, phir yahin unhe set kar sakte ho.")
        else:
            top = st.columns([2.2, 1, 1, 1, 1, 1.2])
            top[0].markdown(f"**{len(items)} photos** — caption likho, aage-peeche karo, cover chuno ya hatao.")
            top[1].button("🔤 A → Z", on_click=_sort, args=("az",), use_container_width=True)
            top[2].button("🔡 Z → A", on_click=_sort, args=("za",), use_container_width=True)
            top[3].button("🔀 Shuffle", on_click=_sort, args=("shuffle",), use_container_width=True)
            top[4].button("↕️ Ulta", on_click=_sort, args=("reverse",), use_container_width=True)
            top[5].button("🗑️ Sab hatao", on_click=_clear, use_container_width=True)

            cover_id = ss.cover_id if any(it["id"] == ss.cover_id for it in items) else items[0]["id"]
            cols = st.columns(4)
            for i, it in enumerate(items):
                with cols[i % 4]:
                    with st.container(border=True):
                        st.image(it["thumb"], use_container_width=True)
                        tag = "⭐ Cover photo" if it["id"] == cover_id else it["name"][:24]
                        st.caption(f"{i + 1}. {tag}")
                        it["caption"] = st.text_input(
                            "Caption", value=it["caption"], key=f"cap_{it['id']}",
                            placeholder="Caption (optional)", label_visibility="collapsed",
                        )
                        b = st.columns(4)
                        b[0].button("◀", key=f"l{it['id']}", on_click=_move, args=(i, -1), help="Pehle laao", use_container_width=True)
                        b[1].button("▶", key=f"r{it['id']}", on_click=_move, args=(i, 1), help="Baad me bhejo", use_container_width=True)
                        b[2].button("⭐", key=f"c{it['id']}", on_click=_set_cover, args=(it["id"],), help="Cover banao", use_container_width=True)
                        b[3].button("🗑️", key=f"d{it['id']}", on_click=_delete, args=(it["id"],), help="Hatao", use_container_width=True)

    items = ss.photos

    # ---------------------------------------------------------------- Design
    with tab_design:
        r1 = st.columns([1.3, 1.3, 1])
        title = r1[0].text_input("Album ka naam (English me best)", "My Memories")
        subtitle = r1[1].text_input("Subtitle", date.today().strftime("%B %Y"))
        fmt_name = r1[2].selectbox("Page format", list(FORMATS.keys()))
        r2 = st.columns([1.3, 1.3, 1])
        pal_name = r2[0].selectbox("🎨 Colour mood", ["Design default"] + list(PALETTES.keys()))
        filt_name = r2[1].selectbox("🧪 Photo filter", FILTERS)
        r2[2].markdown("&nbsp;")
        r2[2].button("🎲 Surprise me", on_click=_surprise, use_container_width=True)

        st.markdown(
            f'<span class="pill">Chuna hua design: {DESIGNS[ss.design]["emoji"]} {ss.design}</span>',
            unsafe_allow_html=True,
        )
        thumbs = [it["thumb"] for it in items[:4]] or sample_images()
        sig = tuple(it["id"] for it in items[:4]) or ("sample",)
        if not items:
            st.caption("Preview abhi sample photos se bana hai. Photos upload karoge to aapki apni photos se dikhega.")

        gcols = st.columns(3)
        for i, (name, spec) in enumerate(DESIGNS.items()):
            with gcols[i % 3]:
                with st.container(border=True):
                    st.image(
                        design_preview(name, pal_name, fmt_name, filt_name, title, subtitle, sig, thumbs),
                        use_container_width=True,
                    )
                    st.markdown(f'<div class="dname">{spec["emoji"]} {name}</div>'
                                f'<div class="ddesc">{spec["desc"]}</div>', unsafe_allow_html=True)
                    sel = name == ss.design
                    st.button("✅ Chuna hua" if sel else "Ye design chuno", key=f"pick_{name}",
                              on_click=_pick_design, args=(name,),
                              type="primary" if sel else "secondary", use_container_width=True)

    # -------------------------------------------------------------- Settings
    with tab_settings:
        st.subheader("Layout")
        s1 = st.columns(2)
        per_page = s1[0].selectbox("Ek page par kitni photos", ["Auto mix", "1", "2", "3", "4"])
        back_cover = s1[1].toggle("Last me 'Thank You' page", value=True)
        st.subheader("Look")
        spec = DESIGNS[ss.design]
        use_default = st.toggle(f"'{ss.design}' ke default look use karo", value=True)
        custom = None
        if not use_default:
            s2 = st.columns(3)
            custom = {
                "radius": s2[0].slider("Corner roundness", 0, 80, spec["radius"]),
                "gap": s2[1].slider("Photos ke beech gap", 0, 120, spec["gap"]),
                "border": s2[2].slider("Photo border", 0, 40, spec["border"]),
            }
        st.caption("Tip: apna font chahiye? Repo me `fonts/title.ttf` aur `fonts/body.ttf` rakh do.")

    # ----------------------------------------------------------------- Album
    with tab_album:
        n = len(items)
        pages_est = len(plan_pages(n, per_page)) + 1 + (1 if back_cover else 0) if n else 0
        m = st.columns(4)
        m[0].metric("Photos", n)
        m[1].metric("Design", f'{DESIGNS[ss.design]["emoji"]} {ss.design}')
        m[2].metric("Format", fmt_name.split(" (")[0])
        m[3].metric("Pages (approx)", pages_est)

        if st.button("✨ Album banao", type="primary", use_container_width=True, disabled=n == 0):
            filt = DESIGNS[ss.design]["filt"] if filt_name == "Design default" else filt_name
            with st.status("Album ban raha hai...", expanded=True) as status:
                bar = st.progress(0.0, text="Shuru...")
                ctx = make_ctx(ss.design, pal_name, fmt_name, title, subtitle, custom, 1.0)
                cover_id = ss.cover_id if any(it["id"] == ss.cover_id for it in items) else items[0]["id"]
                cover_idx = next(k for k, it in enumerate(items) if it["id"] == cover_id)
                loaded = [{"img": decode_item(it["data"], filt), "caption": it["caption"].strip()} for it in items]
                pages = build_album(ctx, loaded, cover_idx, per_page, back_cover, filt,
                                    progress=lambda f, msg: bar.progress(min(f, 1.0), text=msg))
                bar.progress(1.0, text="Files tayyar kar raha hoon...")
                jpgs, pdf, zipb = export_outputs(pages)
                ss.result = {"jpgs": jpgs, "pdf": pdf, "zip": zipb, "design": ss.design}
                status.update(label="Album ready! 🎉", state="complete", expanded=False)

        res = ss.result
        if res:
            st.success(f"{len(res['jpgs'])} pages ka album ready hai ({res['design']}).")
            d1, d2, d3 = st.columns(3)
            d1.download_button("📄 PDF download karo", res["pdf"], "album.pdf", "application/pdf",
                               type="primary", use_container_width=True)
            d2.download_button("🗜️ Saare pages (ZIP)", res["zip"], "album_pages.zip", "application/zip",
                               use_container_width=True)
            total = len(res["jpgs"])
            pg = st.slider("Page dekho", 1, total, 1) if total > 1 else 1
            v1, v2 = st.columns([3, 1])
            v1.image(res["jpgs"][pg - 1], use_container_width=True, caption=f"Page {pg} / {total}")
            v2.download_button("⬇️ Sirf ye page (JPG)", res["jpgs"][pg - 1], f"page_{pg:02d}.jpg",
                               "image/jpeg", use_container_width=True)
            with st.expander("Saare pages ek saath dekho"):
                gc = st.columns(4)
                for i, j in enumerate(res["jpgs"]):
                    gc[i % 4].image(j, use_container_width=True, caption=f"Page {i + 1}")
        elif n == 0:
            st.info("Pehle photos upload karo (Tab 1), design chuno (Tab 2), phir yahan album banao.")


if __name__ == "__main__":
    main()
