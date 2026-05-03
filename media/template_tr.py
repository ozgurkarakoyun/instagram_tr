"""
media/template_tr.py
Okunabilir Türkçe overlay'li gönderi, story ve carousel şablonları.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

NAVY = (8, 35, 61)
DEEP = (4, 18, 33)
TEAL = (29, 196, 185)
MINT = (122, 231, 211)
WHITE = (248, 253, 255)
SUB = (190, 225, 232)
FOOTER = (4, 20, 38, 250)
BOX = (3, 26, 48, 224)
DOCTOR_NAME = "Doç. Dr. Özgür Karakoyun"
WEBSITE = "www.ozgurkarakoyun.com"
PHONE = "0545 919 54 13"
SPECIALTY = "Ortopedi ve Travmatoloji"


def _font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _text_w(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    return draw.textbbox((0, 0), text, font=font)[2]


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
        alpha = int(35 + 105 * (y / h))
        d.line([(0, y), (w, y)], fill=(DEEP[0], DEEP[1], DEEP[2], alpha))
    d.rectangle([0, 0, w, int(h * 0.38)], fill=(4, 22, 42, 130))
    d.rectangle([0, int(h * 0.79), w, h], fill=FOOTER)
    return ov


def _draw_footer(draw, w: int, h: int, is_story: bool = False):
    y0 = int(h * 0.855) if is_story else int(h * 0.835)
    draw.rounded_rectangle([42, y0, w - 42, h - 38], radius=24, fill=(4, 20, 38, 235), outline=(29, 196, 185, 115), width=2)
    name_f = _font(32 if is_story else 28, True)
    info_f = _font(25 if is_story else 22, False)
    draw.text((70, y0 + 24), DOCTOR_NAME, font=name_f, fill=WHITE)
    draw.text((70, y0 + 64), f"{WEBSITE}  ·  Tel: {PHONE}", font=info_f, fill=SUB)


def _draw_accent(draw, x0, y, x1):
    for x in range(x0, x1):
        t = (x - x0) / max(1, x1 - x0 - 1)
        col = tuple(int(TEAL[i] * (1 - t) + MINT[i] * t) for i in range(3))
        draw.line([(x, y), (x, y + 4)], fill=col)


def build_turkish_asset(source_path: str, output_path: str, topic: str, hook: str, variant: str = "post") -> str:
    is_story = variant == "story"
    size = (1080, 1920) if is_story else (1080, 1350)
    w, h = size
    base = _cover_image(source_path, size)
    canvas = Image.alpha_composite(base, _gradient_overlay(size))
    draw = ImageDraw.Draw(canvas)
    margin = 54
    top = 70 if is_story else 54

    label_f = _font(27 if is_story else 23, True)
    spec_f = _font(21 if is_story else 18)
    draw.rounded_rectangle([margin, top, w - margin, top + 86], radius=22, fill=(4, 26, 48, 190), outline=(29, 196, 185, 135), width=2)
    draw.text((margin + 26, top + 17), SPECIALTY, font=label_f, fill=WHITE)
    draw.text((margin + 26, top + 51), "Güvenilir hasta bilgilendirme içeriği", font=spec_f, fill=SUB)

    title_f = _font(56 if is_story else 47, True)
    hook_f = _font(38 if is_story else 31, True)
    max_width = w - 2 * margin - 56
    title_lines = _wrap(draw, topic.upper(), title_f, max_width, 3)
    hook_lines = _wrap(draw, hook, hook_f, max_width, 3)
    line_gap = 8
    box_top = top + 124
    title_h = len(title_lines) * (title_f.size + line_gap)
    hook_h = len(hook_lines) * (hook_f.size + line_gap)
    box_h = 48 + title_h + 22 + hook_h + 42
    draw.rounded_rectangle([margin, box_top, w - margin, box_top + box_h], radius=28, fill=BOX, outline=(122, 231, 211, 95), width=2)
    y = box_top + 28
    for line in title_lines:
        draw.text((margin + 28, y), line, font=title_f, fill=WHITE)
        y += title_f.size + line_gap
    _draw_accent(draw, margin + 28, y + 6, margin + 230)
    y += 25
    for line in hook_lines:
        draw.text((margin + 28, y), line, font=hook_f, fill=MINT)
        y += hook_f.size + line_gap

    _draw_footer(draw, w, h, is_story)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, quality=94, optimize=True)
    logger.info("%s → %s", variant, output_path)
    return output_path


def build_carousel_slide(source_path: str, output_path: str, slide: dict, index: int, total: int) -> str:
    size = (1080, 1350)
    w, h = size
    bg = _cover_image(source_path, size).filter(ImageFilter.GaussianBlur(2))
    canvas = Image.alpha_composite(bg, _gradient_overlay(size))
    draw = ImageDraw.Draw(canvas)
    margin = 58

    # slide number pill
    pill = f"{index}/{total}"
    pill_f = _font(26, True)
    draw.rounded_rectangle([margin, 58, margin + 112, 108], radius=22, fill=(29, 196, 185, 215))
    draw.text((margin + 29, 70), pill, font=pill_f, fill=(4, 18, 33))
    draw.text((margin + 138, 72), SPECIALTY, font=_font(26, True), fill=WHITE)

    panel_top, panel_bottom = 190, 970
    draw.rounded_rectangle([margin, panel_top, w - margin, panel_bottom], radius=38, fill=(3, 26, 48, 232), outline=(122, 231, 211, 100), width=2)

    title = slide.get("title", "")
    body = slide.get("body", "")
    title_f = _font(61, True)
    body_f = _font(39, False)
    title_lines = _wrap(draw, title, title_f, w - 2 * margin - 70, 3)
    body_lines = _wrap(draw, body, body_f, w - 2 * margin - 70, 5)
    y = panel_top + 62
    for line in title_lines:
        draw.text((margin + 36, y), line, font=title_f, fill=WHITE)
        y += title_f.size + 10
    _draw_accent(draw, margin + 36, y + 12, margin + 270)
    y += 52
    for line in body_lines:
        draw.text((margin + 36, y), line, font=body_f, fill=SUB)
        y += body_f.size + 14

    _draw_footer(draw, w, h, False)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, quality=94, optimize=True)
    return output_path
