"""
media/template_tr.py
Turkish Instagram post/story templates with guaranteed readable overlay text.
"""

import logging
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

NAVY = (8, 35, 61)
DEEP = (4, 18, 33)
TEAL = (29, 196, 185)
MINT = (122, 231, 211)
WHITE = (248, 253, 255)
SUB = (190, 225, 232)
FOOTER = (4, 20, 38, 255)
BOX = (3, 26, 48, 218)

DOCTOR_NAME = "Doç. Dr. Özgür Karakoyun"
WEBSITE = "www.ozgurkarakoyun.com"
PHONE = "0545 919 54 13"
SPECIALTY = "Ortopedi ve Travmatoloji"


def _font(size: int, bold: bool = False):
    candidates = [
        "static/fonts/Bold.ttf" if bold else "static/fonts/Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        try:
            if Path(p).exists():
                return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _text_w(draw, text, font):
    return draw.textbbox((0, 0), text, font=font)[2]


def _wrap(draw, text, font, max_width, max_lines):
    words = str(text).split()
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
    return lines[:max_lines]


def _cover_image(path, size):
    w, h = size
    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return img.crop((left, top, left + w, top + h)).convert("RGBA")


def _gradient_overlay(size):
    w, h = size
    ov = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(h):
        alpha = int(40 + 80 * (y / h))
        d.line([(0, y), (w, y)], fill=(DEEP[0], DEEP[1], DEEP[2], alpha))
    # readable top and footer zones
    d.rectangle([0, 0, w, int(h * 0.35)], fill=(4, 22, 42, 112))
    d.rectangle([0, int(h * 0.78), w, h], fill=FOOTER)
    return ov


def _draw_accent(draw, w, y):
    for x in range(w):
        t = x / max(1, w - 1)
        col = tuple(int(TEAL[i] * (1 - t) + MINT[i] * t) for i in range(3))
        draw.point((x, y), fill=col)
        draw.point((x, y + 1), fill=col)
        draw.point((x, y + 2), fill=col)


def _draw_text_block(canvas, topic, hook, is_story=False):
    w, h = canvas.size
    draw = ImageDraw.Draw(canvas)
    margin = 58 if is_story else 52
    top = 76 if is_story else 58

    # Doctor/specialty label
    label_f = _font(28 if is_story else 24, bold=True)
    spec_f = _font(22 if is_story else 18)
    draw.rounded_rectangle([margin, top, w - margin, top + 88], radius=22, fill=(4, 26, 48, 185), outline=(29, 196, 185, 140), width=2)
    draw.text((margin + 28, top + 18), SPECIALTY, font=label_f, fill=WHITE)
    draw.text((margin + 28, top + 52), "Güvenilir hasta bilgilendirme içeriği", font=spec_f, fill=SUB)

    title_f = _font(58 if is_story else 48, bold=True)
    hook_f = _font(39 if is_story else 32, bold=True)
    max_width = w - 2 * margin - 56

    title_lines = _wrap(draw, topic.upper(), title_f, max_width, 3)
    hook_lines = _wrap(draw, hook, hook_f, max_width, 3)
    line_gap = 8
    title_h = len(title_lines) * (title_f.size + line_gap)
    hook_h = len(hook_lines) * (hook_f.size + line_gap)
    box_top = top + 130
    box_h = 50 + title_h + 26 + hook_h + 42
    draw.rounded_rectangle([margin, box_top, w - margin, box_top + box_h], radius=28, fill=BOX, outline=(122, 231, 211, 95), width=2)

    y = box_top + 30
    for line in title_lines:
        draw.text((margin + 28, y), line, font=title_f, fill=WHITE)
        y += title_f.size + line_gap
    y += 18
    for line in hook_lines:
        draw.text((margin + 28, y), line, font=hook_f, fill=MINT)
        y += hook_f.size + line_gap


def _draw_footer(canvas, is_story=False):
    w, h = canvas.size
    draw = ImageDraw.Draw(canvas)
    footer_h = 240 if is_story else 190
    fy = h - footer_h
    draw.rounded_rectangle([36, fy + 22, w - 36, h - 42], radius=26, fill=(3, 20, 37, 255), outline=(29, 196, 185, 125), width=2)

    name_f = _font(42 if is_story else 34, bold=True)
    info_f = _font(30 if is_story else 24)
    name_y = fy + (70 if is_story else 58)
    line_y = name_y + (58 if is_story else 48)
    draw.text(((w - _text_w(draw, DOCTOR_NAME, name_f)) // 2, name_y), DOCTOR_NAME, font=name_f, fill=WHITE)
    line = f"{WEBSITE}  •  Tel: {PHONE}"
    draw.text(((w - _text_w(draw, line, info_f)) // 2, line_y), line, font=info_f, fill=SUB)


def build_turkish_asset(input_path: str, output_path: str, topic: str, hook: str, variant: str):
    if variant == "post":
        size = (1080, 1350)  # Instagram feed portrait 4:5
        is_story = False
    else:
        size = (1080, 1920)  # Story 9:16
        is_story = True

    try:
        canvas = _cover_image(input_path, size)
    except Exception as exc:
        logger.error("Background image load failed: %s", exc)
        canvas = Image.new("RGBA", size, NAVY + (255,))

    # soften busy backgrounds slightly for text readability
    bg = canvas.filter(ImageFilter.GaussianBlur(radius=0.4))
    bg = Image.alpha_composite(bg, _gradient_overlay(size))
    _draw_text_block(bg, topic, hook, is_story=is_story)
    _draw_footer(bg, is_story=is_story)

    Path(output_path).parent.mkdir(exist_ok=True)
    bg.convert("RGB").save(output_path, quality=96, optimize=True)
    logger.info("Turkish %s → %s", variant, output_path)
    return output_path
