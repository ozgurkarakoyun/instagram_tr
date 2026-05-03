"""
media/template_tr.py
Okunabilir Türkçe overlay'li gönderi, story ve carousel şablonları.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

DEEP = (4, 18, 33)
TEAL = (29, 196, 185)
MINT = (122, 231, 211)
WHITE = (248, 253, 255)
SUB = (190, 225, 232)
FOOTER = (4, 20, 38, 250)
BOX = (3, 26, 48, 228)
DOCTOR_NAME = "Doç. Dr. Özgür Karakoyun"
WEBSITE = "www.ozgurkarakoyun.com"
PHONE = "0545 919 54 13"
SPECIALTY = "Ortopedi ve Travmatoloji"

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_FONT_REGULAR = BASE_DIR / "static" / "fonts" / "DejaVuSans.ttf"
PROJECT_FONT_BOLD = BASE_DIR / "static" / "fonts" / "DejaVuSans-Bold.ttf"


def _font(size: int, bold: bool = False):
    candidates = [
        str(PROJECT_FONT_BOLD if bold else PROJECT_FONT_REGULAR),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _text_w(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    return draw.textbbox((0, 0), text, font=font, stroke_width=0)[2]


def _fit_font(draw, text: str, start_size: int, max_width: int, bold: bool, min_size: int = 20):
    size = start_size
    while size > min_size:
        font = _font(size, bold)
        if _text_w(draw, text, font) <= max_width:
            return font
        size -= 2
    return _font(min_size, bold)


def _wrap(draw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    words = str(text or "").replace("\n", " ").split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if _text_w(draw, trial, font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(words)) > len(" ".join(lines)):
        lines[-1] = lines[-1].rstrip(".,;: ") + "…"
    return lines[:max_lines]


def _cover_image(path: str, size: tuple[int, int]) -> Image.Image:
    w, h = size
    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h)).convert("RGBA")


def _gradient_overlay(size: tuple[int, int]) -> Image.Image:
    w, h = size
    ov = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(h):
        alpha = int(44 + 112 * (y / h))
        d.line([(0, y), (w, y)], fill=(DEEP[0], DEEP[1], DEEP[2], alpha))
    d.rectangle([0, 0, w, int(h * 0.43)], fill=(4, 22, 42, 142))
    d.rectangle([0, int(h * 0.80), w, h], fill=FOOTER)
    return ov


def _draw_text(draw, xy, text, font, fill, stroke_fill=(3, 18, 33), stroke_width=1):
    draw.text(xy, text, font=font, fill=fill, stroke_fill=stroke_fill, stroke_width=stroke_width)


def _draw_footer(draw, w: int, h: int, is_story: bool = False):
    y0 = int(h * 0.847) if is_story else int(h * 0.825)
    draw.rounded_rectangle([34, y0, w - 34, h - 26], radius=28, fill=(4, 20, 38, 238), outline=(29, 196, 185, 125), width=2)
    name_f = _font(40 if is_story else 34, True)
    info_f = _font(29 if is_story else 25, False)
    _draw_text(draw, (58, y0 + 22), DOCTOR_NAME, font=name_f, fill=WHITE)
    _draw_text(draw, (58, y0 + 72), f"{WEBSITE}  ·  Tel: {PHONE}", font=info_f, fill=SUB)


def _draw_accent(draw, x0, y, x1):
    for x in range(x0, x1):
        t = (x - x0) / max(1, x1 - x0 - 1)
        col = tuple(int(TEAL[i] * (1 - t) + MINT[i] * t) for i in range(3))
        draw.line([(x, y), (x, y + 5)], fill=col)


def build_turkish_asset(source_path: str, output_path: str, topic: str, hook: str, variant: str = "post") -> str:
    is_story = variant == "story"
    size = (1080, 1920) if is_story else (1080, 1350)
    w, h = size
    base = _cover_image(source_path, size)
    canvas = Image.alpha_composite(base, _gradient_overlay(size))
    draw = ImageDraw.Draw(canvas)
    margin = 48
    top = 64 if is_story else 48

    header_h = 102 if is_story else 92
    draw.rounded_rectangle([margin, top, w - margin, top + header_h], radius=24, fill=(4, 26, 48, 194), outline=(29, 196, 185, 140), width=2)
    label_f = _font(34 if is_story else 28, True)
    spec_f = _font(24 if is_story else 20)
    _draw_text(draw, (margin + 26, top + 16), SPECIALTY, font=label_f, fill=WHITE)
    _draw_text(draw, (margin + 26, top + 56), "Güvenilir hasta bilgilendirme içeriği", font=spec_f, fill=SUB)

    max_width = w - 2 * margin - 64
    title_f = _fit_font(draw, topic.upper(), 70 if is_story else 58, max_width, True, min_size=34)
    hook_f = _fit_font(draw, hook, 46 if is_story else 38, max_width, True, min_size=24)
    title_lines = _wrap(draw, topic.upper(), title_f, max_width, 3)
    hook_lines = _wrap(draw, hook, hook_f, max_width, 3)
    line_gap = 10
    box_top = top + header_h + 26
    title_h = len(title_lines) * (title_f.size + line_gap)
    hook_h = len(hook_lines) * (hook_f.size + line_gap)
    box_h = 56 + title_h + 26 + hook_h + 44
    draw.rounded_rectangle([margin, box_top, w - margin, box_top + box_h], radius=30, fill=BOX, outline=(122, 231, 211, 105), width=2)
    y = box_top + 34
    for line in title_lines:
        _draw_text(draw, (margin + 30, y), line, font=title_f, fill=WHITE, stroke_width=2)
        y += title_f.size + line_gap
    _draw_accent(draw, margin + 30, y + 8, min(w - margin - 30, margin + 320))
    y += 30
    for line in hook_lines:
        _draw_text(draw, (margin + 30, y), line, font=hook_f, fill=MINT, stroke_width=1)
        y += hook_f.size + line_gap

    _draw_footer(draw, w, h, is_story)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, quality=95, optimize=True)
    logger.info("%s → %s", variant, output_path)
    return output_path


def build_carousel_slide(source_path: str, output_path: str, slide: dict, index: int, total: int) -> str:
    size = (1080, 1350)
    w, h = size
    bg = _cover_image(source_path, size).filter(ImageFilter.GaussianBlur(2))
    canvas = Image.alpha_composite(bg, _gradient_overlay(size))
    draw = ImageDraw.Draw(canvas)
    margin = 54

    pill = f"{index}/{total}"
    pill_f = _font(30, True)
    draw.rounded_rectangle([margin, 56, margin + 126, 114], radius=22, fill=(29, 196, 185, 220))
    _draw_text(draw, (margin + 29, 69), pill, font=pill_f, fill=(4, 18, 33), stroke_fill=(29, 196, 185), stroke_width=0)
    _draw_text(draw, (margin + 150, 68), SPECIALTY, font=_font(30, True), fill=WHITE)

    panel_top, panel_bottom = 170, 980
    draw.rounded_rectangle([margin, panel_top, w - margin, panel_bottom], radius=38, fill=(3, 26, 48, 235), outline=(122, 231, 211, 100), width=2)

    title = slide.get("title", "")
    body = slide.get("body", "")
    title_f = _fit_font(draw, title, 68, w - 2 * margin - 76, True, min_size=34)
    body_f = _fit_font(draw, body, 43, w - 2 * margin - 76, False, min_size=24)
    title_lines = _wrap(draw, title, title_f, w - 2 * margin - 76, 3)
    body_lines = _wrap(draw, body, body_f, w - 2 * margin - 76, 6)
    y = panel_top + 58
    for line in title_lines:
        _draw_text(draw, (margin + 38, y), line, font=title_f, fill=WHITE, stroke_width=2)
        y += title_f.size + 10
    _draw_accent(draw, margin + 38, y + 12, margin + 300)
    y += 54
    for line in body_lines:
        _draw_text(draw, (margin + 38, y), line, font=body_f, fill=SUB, stroke_width=1)
        y += body_f.size + 14

    _draw_footer(draw, w, h, False)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, quality=95, optimize=True)
    return output_path
