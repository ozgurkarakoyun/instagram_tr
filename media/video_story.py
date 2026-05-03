"""
media/video_story.py
Yüklenen videoyu kırpmadan 1080x1920 Instagram Story şablonuna yerleştirir.

Kural:
- Video asla crop edilmez.
- Aspect ratio korunur.
- Video, şablonun orta güvenli alanına contain-fit ile küçültülür/büyütülür.
- Header, okunabilir başlık/hook ve footer şablon olarak eklenir.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# Pillow 10+ removed Image.ANTIALIAS, but MoviePy 1.0.3 still references it
# during clip.resize(). This compatibility shim prevents video Story rendering
# from failing with: module 'PIL.Image' has no attribute 'ANTIALIAS'.
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from media.template_tr import (
    LANG_LABELS,
    WEBSITE,
    PHONE,
    WHITE,
    SUB,
    MINT,
    TEAL,
    BOX,
    DEEP,
    _font,
    _lang,
    _shape_text,
    _wrap,
    _fit_font,
    _draw_text,
    _draw_footer,
    _draw_accent,
)

logger = logging.getLogger(__name__)

W, H = 1080, 1920
MAX_DURATION = 60
FPS = 30


def is_video_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}


def _render_story_background(topic: str, hook: str, language: str = "tr") -> Image.Image:
    lang = _lang(language)
    labels = LANG_LABELS[lang]

    canvas = Image.new("RGBA", (W, H), (7, 24, 42, 255))
    d = ImageDraw.Draw(canvas, "RGBA")

    # soft clinical gradient
    for y in range(H):
        alpha = y / H
        r = int(7 + 8 * alpha)
        g = int(24 + 32 * alpha)
        b = int(42 + 45 * alpha)
        d.line([(0, y), (W, y)], fill=(r, g, b, 255))

    # decorative circles
    d.ellipse((-180, -170, 460, 470), outline=(29, 196, 185, 80), width=32)
    d.ellipse((720, 1240, 1320, 1840), outline=(122, 231, 211, 55), width=28)

    margin = 48
    top = 54

    # Header
    header_h = 102
    d.rounded_rectangle([margin, top, W - margin, top + header_h], radius=24, fill=(4, 26, 48, 210), outline=(29, 196, 185, 135), width=2)
    _draw_text(d, (margin + 26, top + 16), labels["specialty"], font=_font(34, True), fill=WHITE, language=lang)
    _draw_text(d, (margin + 26, top + 56), labels["subline"], font=_font(24), fill=SUB, language=lang)

    # Title / hook block
    max_width = W - 2 * margin - 64
    display_title = topic if lang == "ar" else topic.upper()
    title_f = _fit_font(d, display_title, 56, max_width, True, min_size=30, language=lang)
    hook_f = _fit_font(d, hook, 36, max_width, True, min_size=22, language=lang)
    title_lines = _wrap(d, display_title, title_f, max_width, 2, language=lang)
    hook_lines = _wrap(d, hook, hook_f, max_width, 2, language=lang)
    line_gap = 8
    box_top = top + header_h + 20
    title_h = len(title_lines) * (title_f.size + line_gap)
    hook_h = len(hook_lines) * (hook_f.size + line_gap)
    box_h = 40 + title_h + 20 + hook_h + 30
    d.rounded_rectangle([margin, box_top, W - margin, box_top + box_h], radius=28, fill=BOX, outline=(122, 231, 211, 90), width=2)
    y = box_top + 24
    for line in title_lines:
        _draw_text(d, (margin + 28, y), line, font=title_f, fill=WHITE, stroke_width=2, language=lang)
        y += title_f.size + line_gap
    _draw_accent(d, margin + 28, y + 6, min(W - margin - 28, margin + 300))
    y += 24
    for line in hook_lines:
        _draw_text(d, (margin + 28, y), line, font=hook_f, fill=MINT, stroke_width=1, language=lang)
        y += hook_f.size + line_gap

    # Video placeholder / frame
    frame = _video_box()
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    sx1, sy1, sx2, sy2 = frame
    sd.rounded_rectangle([sx1 + 8, sy1 + 10, sx2 + 8, sy2 + 10], radius=34, fill=(0, 0, 0, 130))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    canvas = Image.alpha_composite(canvas, shadow)
    d = ImageDraw.Draw(canvas, "RGBA")
    d.rounded_rectangle(frame, radius=34, fill=(3, 18, 33, 185), outline=(122, 231, 211, 120), width=3)

    # Footer
    _draw_footer(d, W, H, True, language=lang)
    return canvas


def _video_box() -> tuple[int, int, int, int]:
    # Header/title area üstte, footer altta kalacak şekilde güvenli alan.
    return (54, 430, 1026, 1600)


def _contain_size(src_w: int, src_h: int, max_w: int, max_h: int) -> tuple[int, int]:
    scale = min(max_w / src_w, max_h / src_h)
    return max(2, int(src_w * scale)), max(2, int(src_h * scale))


def build_story_video(
    input_path: str,
    output_path: str,
    topic: str,
    hook: str = "",
    language: str = "tr",
) -> str:
    try:
        from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
    except ImportError as exc:
        raise RuntimeError("MoviePy kurulmamış. requirements.txt içinde moviepy bulunmalı.") from exc

    src = Path(input_path)
    if not is_video_file(src):
        raise ValueError("Story video için MP4, MOV, M4V, WebM, AVI veya MKV dosyası gerekir.")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    clip = VideoFileClip(str(src), audio=True)
    duration = min(float(clip.duration or 0), MAX_DURATION)
    if duration <= 0:
        clip.close()
        raise ValueError("Video süresi okunamadı.")
    clip = clip.subclip(0, duration)

    frame = _video_box()
    x1, y1, x2, y2 = frame
    box_w, box_h = x2 - x1, y2 - y1
    new_w, new_h = _contain_size(int(clip.w), int(clip.h), box_w, box_h)

    # ASLA crop yok: yalnızca resize + center placement.
    resized = clip.resize((new_w, new_h))
    pos = (x1 + (box_w - new_w) // 2, y1 + (box_h - new_h) // 2)

    bg_img = _render_story_background(topic, hook, language=language).convert("RGB")
    bg_clip = ImageClip(np.array(bg_img)).set_duration(duration)
    video_layer = resized.set_position(pos)
    final = CompositeVideoClip([bg_clip, video_layer], size=(W, H)).set_duration(duration)

    if clip.audio:
        final = final.set_audio(clip.audio)

    final.write_videofile(
        str(out),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=2,
        logger=None,
    )

    clip.close()
    resized.close()
    final.close()
    bg_clip.close()

    logger.info("Story video contain-fit %sx%s inside %sx%s → %s", new_w, new_h, box_w, box_h, out)
    return str(out)
