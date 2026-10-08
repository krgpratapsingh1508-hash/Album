import io
import zipfile
from datetime import date

import streamlit as st
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

# ---------- Page settings (A4 portrait, ~200 dpi) ----------
PAGE_W, PAGE_H = 1654, 2339
MARGIN = 110
FOOTER = 90

THEMES = {
    "Classic White": {"bg": (255, 255, 255), "fg": (35, 35, 35), "accent": (180, 150, 90), "border": (255, 255, 255)},
    "Dark Elegant": {"bg": (24, 24, 28), "fg": (240, 240, 240), "accent": (212, 175, 55), "border": (40, 40, 46)},
    "Soft Pink": {"bg": (253, 238, 241), "fg": (90, 40, 60), "accent": (214, 96, 135), "border": (255, 255, 255)},
    "Ocean Blue": {"bg": (232, 243, 250), "fg": (20, 55, 90), "accent": (40, 120, 190), "border": (255, 255, 255)},
    "Vintage Cream": {"bg": (245, 236, 220), "fg": (80, 55, 35), "accent": (150, 100, 55), "border": (252, 247, 236)},
}

# (x, y, w, h) as fractions of the content area
LAYOUTS = {
    1: [(0, 0, 1, 1)],
    2: [(0, 0, 1, 0.5), (0, 0.5, 1, 0.5)],
    3: [(0, 0, 1, 0.55), (0, 0.55, 0.5, 0.45), (0.5, 0.55, 0.5, 0.45)],
    4: [(0, 0, 0.5, 0.5), (0.5, 0, 0.5, 0.5), (0, 0.5, 0.5, 0.5), (0.5, 0.5, 0.5, 0.5)],
}


# ---------- Helpers ----------
def get_font(size, bold=True):
    names = ["DejaVuSans-Bold.ttf", "DejaVuSerif-Bold.ttf", "Arial Bold.ttf"] if bold else [
        "DejaVuSans.ttf", "DejaVuSerif.ttf", "Arial.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def fit_font(draw, text, max_w, size, bold=True):
    font = get_font(size, bold)
    while size > 40 and draw.textlength(text, font=font) > max_w:
        size -= 6
        font = get_font(size, bold)
    return font


def load_image(file, enhance):
    img = Image.open(file)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((2400, 2400))
    if enhance:
        img = ImageOps.autocontrast(img, cutoff=1)
        img = ImageEnhance.Color(img).enhance(1.12)
        img = ImageEnhance.Sharpness(img).enhance(1.15)
        img = ImageEnhance.Contrast(img).enhance(1.05)
    return img


def paste_photo(canvas, img, box, radius, border, border_color):
    x, y, w, h = [int(v) for v in box]
    if border > 0:
        inner = ImageOps.fit(img, (w - 2 * border, h - 2 * border), Image.LANCZOS, centering=(0.5, 0.4))
        tile = Image.new("RGB", (w, h), border_color)
        tile.paste(inner, (border, border))
    else:
        tile = ImageOps.fit(img, (w, h), Image.LANCZOS, centering=(0.5, 0.4))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    canvas.paste(tile, (x, y), mask)


def make_cover(photo, title, subtitle, theme, radius, border):
    canvas = Image.new("RGB", (PAGE_W, PAGE_H), theme["bg"])
    d = ImageDraw.Draw(canvas)
    box = (MARGIN, 260, PAGE_W - 2 * MARGIN, 1350)
    paste_photo(canvas, photo, box, radius, max(border, 14), theme["border"])

    font = fit_font(d, title, PAGE_W - 2 * MARGIN, 140)
    d.text((PAGE_W / 2, 1700), title, font=font, fill=theme["fg"], anchor="mm")
    d.line((PAGE_W / 2 - 160, 1810, PAGE_W / 2 + 160, 1810), fill=theme["accent"], width=6)
    if subtitle:
        sfont = fit_font(d, subtitle, PAGE_W - 2 * MARGIN, 54, bold=False)
        d.text((PAGE_W / 2, 1890), subtitle, font=sfont, fill=theme["fg"], anchor="mm")
    return canvas


def make_page(photos, theme, page_no, gap, radius, border):
    canvas = Image.new("RGB", (PAGE_W, PAGE_H), theme["bg"])
    d = ImageDraw.Draw(canvas)
    cx, cy = MARGIN, MARGIN
    cw, ch = PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN - FOOTER

    for img, (fx, fy, fw, fh) in zip(photos, LAYOUTS[len(photos)]):
        box = (
            cx + fx * cw + gap / 2,
            cy + fy * ch + gap / 2,
            fw * cw - gap,
            fh * ch - gap,
        )
        paste_photo(canvas, img, box, radius, border, theme["border"])

    y = PAGE_H - MARGIN + 20
    d.line((PAGE_W / 2 - 60, y - 36, PAGE_W / 2 + 60, y - 36), fill=theme["accent"], width=4)
    d.text((PAGE_W / 2, y), str(page_no), font=get_font(36, bold=False), fill=theme["fg"], anchor="mm")
    return canvas


def build_album(images, title, subtitle, theme, per_page, radius, gap, border):
    pages = [make_cover(images[0], title, subtitle, theme, radius, border)]
    pattern = [3, 2, 4, 1] if per_page == "Auto mix" else [int(per_page)]
    i, k = 0, 0
    while i < len(images):
        n = min(pattern[k % len(pattern)], len(images) - i)
        pages.append(make_page(images[i:i + n], theme, len(pages), gap, radius, border))
        i += n
        k += 1
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


# ---------- UI ----------
st.set_page_config(page_title="Photo Album Maker", page_icon="📸", layout="wide")
st.title("📸 Photo Album Maker")
st.caption("Photos upload karo, ek sundar album ready ho jayega.")

with st.sidebar:
    st.header("Settings")
    title = st.text_input("Album ka naam (English me best dikhega)", "My Memories")
    subtitle = st.text_input("Subtitle", date.today().strftime("%B %Y"))
    theme_name = st.selectbox("Theme", list(THEMES.keys()))
    per_page = st.selectbox("Ek page par photos", ["Auto mix", "1", "2", "3", "4"])
    enhance = st.checkbox("Auto-enhance (colour + sharpness)", value=True)
    sort_names = st.checkbox("Photos ko file name se sort karo", value=True)
    radius = st.slider("Corner roundness", 0, 80, 28)
    gap = st.slider("Photos ke beech gap", 10, 80, 36)
    border = st.slider("Photo border", 0, 30, 0)

files = st.file_uploader(
    "Photos upload karo", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True
)

if files:
    st.write(f"{len(files)} photos select hui hain.")
    if st.button("✨ Album banao", type="primary"):
        with st.spinner("Album ban raha hai..."):
            ordered = sorted(files, key=lambda f: f.name.lower()) if sort_names else files
            images = [load_image(f, enhance) for f in ordered]
            pages = build_album(images, title, subtitle, THEMES[theme_name],
                                per_page, radius, gap, border)
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
