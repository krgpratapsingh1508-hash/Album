import io
import os
import random
import zipfile
from datetime import date

import streamlit as st
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

# ======================================================================
#  Photo Album Maker  -  3 premium styles
#  Modern Magazine | Polaroid Scrapbook | Cinematic Blur
# ======================================================================

W, H = 1654, 2339          # A4 portrait @ ~200 dpi
MARGIN = 110
CARD_TEXT = (70, 60, 55)
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

THEMES = {
    "Classic White": {"bg": (250, 249, 246), "fg": (35, 35, 35), "accent": (176, 141, 87), "card": (255, 255, 255)},
    "Dark Elegant": {"bg": (26, 26, 31), "fg": (240, 236, 228), "accent": (212, 175, 55), "card": (246, 241, 231)},
    "Soft Pink": {"bg": (252, 235, 239), "fg": (110, 45, 70), "accent": (214, 96, 135), "card": (255, 252, 252)},
    "Ocean Blue": {"bg": (228, 241, 249), "fg": (20, 55, 90), "accent": (40, 120, 190), "card": (255, 255, 255)},
    "Vintage Cream": {"bg": (242, 231, 212), "fg": (84, 58, 36), "accent": (150, 100, 55), "card": (253, 249, 240)},
}

STYLES = ["Modern Magazine", "Polaroid Scrapbook", "Cinematic Blur"]


# ----------------------------------------------------------------------
#  Fonts & text
# ----------------------------------------------------------------------
def get_font(size, kind="title"):
    """Tip: fonts/ folder me title.ttf / body.ttf daalo to apna font use hoga."""
    custom = os.path.join(FONT_DIR, "title.ttf" if kind == "title" else "body.ttf")
    names = [custom]
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


def fit_font(draw, text, max_w, size, kind="title"):
    font = get_font(size, kind)
    while size > 36 and draw.textlength(text, font=font) > max_w:
        size -= 6
        font = get_font(size, kind)
    return font


def spaced_text(d, cx, cy, text, font, fill, spacing=10):
    """Letter-spaced, uppercase text (looks premium for labels)."""
    text = text.upper()
    widths = [d.textlength(ch, font=font) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        d.text((x, cy), ch, font=font, fill=fill, anchor="lm")
        x += w + spacing


# ----------------------------------------------------------------------
#  Image helpers
# ----------------------------------------------------------------------
def load_image(file, enhance):
    img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
    img.thumbnail((2400, 2400))
    if enhance:
        img = ImageOps.autocontrast(img, cutoff=1)
        img = ImageEnhance.Color(img).enhance(1.12)
        img = ImageEnhance.Contrast(img).enhance(1.05)
        img = ImageEnhance.Sharpness(img).enhance(1.15)
    return img


def draw_shadow(canvas, x, y, w, h, radius, blur=26, offset=(0, 18), opacity=0.38):
    pad = blur * 3
    m = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    ImageDraw.Draw(m).rounded_rectangle((pad, pad, pad + w, pad + h), radius=radius, fill=int(255 * opacity))
    m = m.filter(ImageFilter.GaussianBlur(blur))
    canvas.paste((0, 0, 0), (x - pad + offset[0], y - pad + offset[1]), m)


def place_photo(canvas, img, box, radius, border, border_color, shadow=True):
    x, y, w, h = [int(v) for v in box]
    if shadow:
        draw_shadow(canvas, x, y, w, h, radius)
    if border > 0:
        inner = ImageOps.fit(img, (w - 2 * border, h - 2 * border), Image.LANCZOS, centering=(0.5, 0.4))
        tile = Image.new("RGB", (w, h), border_color)
        tile.paste(inner, (border, border))
    else:
        tile = ImageOps.fit(img, (w, h), Image.LANCZOS, centering=(0.5, 0.4))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    canvas.paste(tile, (x, y), mask)


def polaroid(img, w, h, angle, theme, caption=None):
    """Polaroid card with tape, rotated. Returns RGBA image."""
    card_color = theme["card"]
    side = int(w * 0.05)
    bottom = int(h * 0.17)
    card = Image.new("RGBA", (w, h), card_color + (255,))
    inner = ImageOps.fit(img, (w - 2 * side, h - side - bottom), Image.LANCZOS, centering=(0.5, 0.4))
    card.paste(inner, (side, side))
    if caption:
        cd = ImageDraw.Draw(card)
        font = fit_font(cd, caption, w - 2 * side - 20, int(bottom * 0.5))
        cd.text((w / 2, h - bottom / 2 - 6), caption, font=font, fill=CARD_TEXT, anchor="mm")

    tape_w, tape_h = int(w * 0.32), max(int(h * 0.055), 20)
    pad = tape_h // 2
    full = Image.new("RGBA", (w, h + pad), card_color + (0,))
    full.paste(card, (0, pad))
    tape = Image.new("RGBA", (tape_w, tape_h), theme["accent"] + (150,))
    tape = tape.rotate(random.uniform(-6, 6), expand=True, resample=Image.BICUBIC)
    full.alpha_composite(tape, (max(w // 2 - tape.width // 2, 0), 0))
    return full.rotate(angle, expand=True, resample=Image.BICUBIC)


def place_rgba(canvas, rgba, cx, cy):
    x, y = int(cx - rgba.width / 2), int(cy - rgba.height / 2)
    alpha = rgba.split()[3]
    sh = alpha.filter(ImageFilter.GaussianBlur(16)).point(lambda p: int(p * 0.4))
    canvas.paste((0, 0, 0), (x + 10, y + 22), sh)
    canvas.paste(rgba.convert("RGB"), (x, y), alpha)


# ----------------------------------------------------------------------
#  Backgrounds
# ----------------------------------------------------------------------
def paper_bg(theme, grain):
    base = Image.new("RGB", (W, H), theme["bg"])
    return Image.blend(base, grain, 0.035)


def blurred_bg(img, darken=0.55):
    small = ImageOps.fit(img, (W // 10, H // 10), Image.LANCZOS).filter(ImageFilter.GaussianBlur(5))
    bg = small.resize((W, H), Image.BICUBIC)
    return Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), darken)


def gradient_overlay(canvas, y0, y1, max_alpha=0.85):
    g = Image.linear_gradient("L").resize((W, y1 - y0))
    g = g.point(lambda p: int(p * max_alpha))
    canvas.paste((0, 0, 0), (0, y0), g)


# ----------------------------------------------------------------------
#  Layouts (orientation-aware)
# ----------------------------------------------------------------------
def is_landscape(img):
    return img.width >= img.height


def choose_layout(photos):
    n = len(photos)
    if n == 1:
        return [(0, 0, 1, 1)]
    if n == 2:
        if is_landscape(photos[0]) and is_landscape(photos[1]):
            return [(0, 0, 1, 0.5), (0, 0.5, 1, 0.5)]
        return [(0, 0, 0.5, 1), (0.5, 0, 0.5, 1)]
    if n == 3:
        if is_landscape(photos[0]):
            return [(0, 0, 1, 0.55), (0, 0.55, 0.5, 0.45), (0.5, 0.55, 0.5, 0.45)]
        return [(0, 0, 0.6, 1), (0.6, 0, 0.4, 0.5), (0.6, 0.5, 0.4, 0.5)]
    return [(0, 0, 0.5, 0.5), (0.5, 0, 0.5, 0.5), (0, 0.5, 0.5, 0.5), (0.5, 0.5, 0.5, 0.5)]


def content_area(style):
    if style == "Modern Magazine":
        return (MARGIN, 220, W - 2 * MARGIN, H - 220 - 170)
    if style == "Polaroid Scrapbook":
        return (80, 100, W - 160, H - 100 - 170)
    return (MARGIN, 120, W - 2 * MARGIN, H - 120 - 190)


def cell_boxes(photos, area, gap):
    ax, ay, aw, ah = area
    return [
        (int(ax + fx * aw + gap / 2), int(ay + fy * ah + gap / 2), int(fw * aw - gap), int(fh * ah - gap))
        for fx, fy, fw, fh in choose_layout(photos)
    ]


# ----------------------------------------------------------------------
#  Pages
# ----------------------------------------------------------------------
def make_page(style, theme, photos, page_no, gap, radius, border, grain, title):
    fg, accent = theme["fg"], theme["accent"]
    if style == "Cinematic Blur":
        canvas = blurred_bg(photos[0])
        fg = (255, 255, 255)
    else:
        canvas = paper_bg(theme, grain)
    d = ImageDraw.Draw(canvas)

    rng = random.Random(page_no)
    for img, (x, y, w, h) in zip(photos, cell_boxes(photos, content_area(style), gap)):
        if style == "Polaroid Scrapbook":
            ratio = 0.8 if not is_landscape(img) else 1.15
            cw = min(w * 0.88, h * 0.88 * ratio)
            ch = cw / ratio
            angle = rng.choice([-1, 1]) * rng.uniform(1.5, 5)
            place_rgba(canvas, polaroid(img, int(cw), int(ch), angle, theme), x + w / 2, y + h / 2)
        else:
            bcolor = (255, 255, 255) if style == "Cinematic Blur" else theme["card"]
            place_photo(canvas, img, (x, y, w, h), radius, border, bcolor)

    if style == "Modern Magazine":
        d.rectangle((55, 55, W - 55, H - 55), outline=accent, width=3)
        spaced_text(d, W / 2, 125, title, get_font(36, "body"), fg, 14)
        d.line((W / 2 - 110, 165, W / 2 + 110, 165), fill=accent, width=4)

    d.line((W / 2 - 50, H - 135, W / 2 + 50, H - 135), fill=accent, width=3)
    spaced_text(d, W / 2, H - 95, f"{page_no:02d}", get_font(34, "body"), fg, 8)
    return canvas


def make_cover(style, theme, img, title, subtitle, radius, grain):
    accent = theme["accent"]
    if style == "Modern Magazine":
        canvas = ImageOps.fit(img, (W, H), Image.LANCZOS, centering=(0.5, 0.4))
        gradient_overlay(canvas, int(H * 0.5), H, 0.9)
        d = ImageDraw.Draw(canvas)
        d.rectangle((50, 50, W - 50, H - 50), outline=(255, 255, 255), width=3)
        spaced_text(d, W / 2, 150, "Photo Album", get_font(40, "body"), (255, 255, 255), 16)
        font = fit_font(d, title, W - 2 * MARGIN - 60, 160)
        d.text((W / 2, H - 520), title, font=font, fill=(255, 255, 255), anchor="mm")
        d.line((W / 2 - 150, H - 420, W / 2 + 150, H - 420), fill=accent, width=6)
        if subtitle:
            spaced_text(d, W / 2, H - 340, subtitle, get_font(46, "body"), (255, 255, 255), 14)
        return canvas

    if style == "Polaroid Scrapbook":
        canvas = paper_bg(theme, grain)
        d = ImageDraw.Draw(canvas)
        place_rgba(canvas, polaroid(img, 1150, 1500, -3, theme, caption=title), W / 2, 1120)
        d.line((W / 2 - 150, 2010, W / 2 + 150, 2010), fill=accent, width=5)
        if subtitle:
            spaced_text(d, W / 2, 2090, subtitle, get_font(46, "body"), theme["fg"], 14)
        return canvas

    canvas = blurred_bg(img, 0.45)
    d = ImageDraw.Draw(canvas)
    place_photo(canvas, img, ((W - 1300) // 2, 230, 1300, 1560), radius, 16, (255, 255, 255))
    font = fit_font(d, title, W - 2 * MARGIN, 140)
    d.text((W / 2, 2010), title, font=font, fill=(255, 255, 255), anchor="mm")
    if subtitle:
        spaced_text(d, W / 2, 2135, subtitle, get_font(44, "body"), (255, 255, 255), 14)
    return canvas


def make_back(style, theme, last_img, title, grain):
    if style == "Cinematic Blur":
        canvas, fg = blurred_bg(last_img, 0.6), (255, 255, 255)
    else:
        canvas, fg = paper_bg(theme, grain), theme["fg"]
    d = ImageDraw.Draw(canvas)
    if style == "Modern Magazine":
        d.rectangle((55, 55, W - 55, H - 55), outline=theme["accent"], width=3)
    font = fit_font(d, "Thank You", W - 2 * MARGIN, 150)
    d.text((W / 2, H / 2 - 40), "Thank You", font=font, fill=fg, anchor="mm")
    d.line((W / 2 - 160, H / 2 + 60, W / 2 + 160, H / 2 + 60), fill=theme["accent"], width=6)
    spaced_text(d, W / 2, H / 2 + 135, title, get_font(42, "body"), fg, 12)
    return canvas


def build_album(images, style, theme, title, subtitle, per_page, radius, gap, border, back_cover):
    grain = Image.effect_noise((W, H), 30).convert("RGB")
    pages = [make_cover(style, theme, images[0], title, subtitle, radius, grain)]
    pattern = [3, 2, 4, 1] if per_page == "Auto mix" else [int(per_page)]
    i = k = 0
    while i < len(images):
        n = min(pattern[k % len(pattern)], len(images) - i)
        pages.append(make_page(style, theme, images[i:i + n], len(pages), gap, radius, border, grain, title))
        i += n
        k += 1
    if back_cover:
        pages.append(make_back(style, theme, images[-1], title, grain))
    return pages


def to_pdf_bytes(pages):
    buf = io.BytesIO()
    pages[0].save(buf, "PDF", save_all=True, append_images=pages[1:], resolution=200.0)
    return buf.getvalue()


def to_zip_bytes(pages):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, p in enumerate(pages, 1):
            jb = io.BytesIO()
            p.save(jb, "JPEG", quality=92)
            z.writestr(f"album_page_{i:02d}.jpg", jb.getvalue())
    return buf.getvalue()


# ======================================================================
#  UI
# ======================================================================
if __name__ == "__main__":
    st.set_page_config(page_title="Photo Album Maker", page_icon="📸", layout="wide")
    st.title("📸 Photo Album Maker")
    st.caption("Photos upload karo, ek sundar album ready ho jayega.")

    with st.sidebar:
        st.header("Design")
        style = st.selectbox("Album style", STYLES)
        theme_name = st.selectbox("Colour theme", list(THEMES.keys()))
        title = st.text_input("Album ka naam (English me best)", "My Memories")
        subtitle = st.text_input("Subtitle", date.today().strftime("%B %Y"))
        st.header("Layout")
        per_page = st.selectbox("Ek page par photos", ["Auto mix", "1", "2", "3", "4"])
        enhance = st.checkbox("Auto-enhance (colour + sharpness)", value=True)
        sort_names = st.checkbox("File name se sort karo", value=True)
        back_cover = st.checkbox("Last me 'Thank You' page", value=True)
        st.header("Fine tuning")
        st.caption("Magazine / Cinematic style ke liye")
        radius = st.slider("Corner roundness", 0, 80, 24)
        gap = st.slider("Photos ke beech gap", 20, 100, 44)
        border = st.slider("Photo border", 0, 30, 10)

    files = st.file_uploader(
        "Photos upload karo", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True
    )

    if files:
        st.write(f"{len(files)} photos select hui hain.")
        if st.button("✨ Album banao", type="primary"):
            with st.spinner("Album ban raha hai..."):
                ordered = sorted(files, key=lambda f: f.name.lower()) if sort_names else files
                images = [load_image(f, enhance) for f in ordered]
                pages = build_album(images, style, THEMES[theme_name], title, subtitle,
                                    per_page, radius, gap, border, back_cover)
                st.session_state["pages"] = pages
                st.session_state["pdf"] = to_pdf_bytes(pages)
                st.session_state["zip"] = to_zip_bytes(pages)

    if "pages" in st.session_state:
        st.success(f"Album ready! Total {len(st.session_state['pages'])} pages.")
        c1, c2 = st.columns(2)
        c1.download_button("⬇️ PDF download", st.session_state["pdf"], "album.pdf", "application/pdf")
        c2.download_button("⬇️ Pages (ZIP of JPGs)", st.session_state["zip"], "album_pages.zip", "application/zip")
        cols = st.columns(3)
        for i, page in enumerate(st.session_state["pages"]):
            cols[i % 3].image(page, use_container_width=True, caption=f"Page {i + 1}")
    else:
        st.info("Pehle photos upload karo, phir 'Album banao' dabao.")
