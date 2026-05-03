"""
ai/image_generate.py
Konu bazlı GPT Image üretimi ve fallback görsel.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)
SAFE_PALETTE = "deep navy, teal, soft turquoise, white, clean medical blue, subtle green accents"


def _fallback_artwork(path: str, topic: str, variant: str) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    w, h = (1024, 1536)
    img = Image.new("RGB", (w, h), (7, 28, 50))
    draw = ImageDraw.Draw(img, "RGBA")
    for y in range(h):
        r = int(7 + y / h * 18)
        g = int(28 + y / h * 50)
        b = int(50 + y / h * 70)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
    draw.ellipse((-220, -170, 560, 560), outline=(29, 196, 185, 115), width=48)
    draw.ellipse((540, 990, 1280, 1720), outline=(122, 231, 211, 100), width=40)
    draw.rounded_rectangle((150, 470, 874, 990), radius=54, fill=(255, 255, 255, 24), outline=(122, 231, 211, 105), width=3)
    draw.line((250, 670, 774, 670), fill=(122, 231, 211, 180), width=18)
    draw.line((512, 535, 512, 875), fill=(88, 198, 255, 160), width=14)
    draw.ellipse((430, 590, 594, 754), outline=(248, 253, 255, 170), width=10)
    img.save(path, quality=95)
    return path


def build_medical_image_prompt(topic: str, hook: str, variant: str) -> str:
    return f"""
Create a premium healthcare social media background image for an orthopedic and traumatology educational Instagram {variant}.
Topic: {topic}
Hook idea: {hook}
Style: trustworthy, safe, modern medical, orthopedic clinic aesthetic, {SAFE_PALETTE}.
Visual direction: clean orthopedic illustration or realistic medical editorial scene related to the topic; bone, joint, spine, trauma care, rehabilitation, operating-room planning, diagnostic concept, or physiotherapy when relevant.
Composition: vertical portrait, mobile-first, enough negative space in upper third for title/hook overlay, clean lower footer area.
Important: do NOT write any text, letters, logos, numbers, watermarks, signatures, captions, labels, or UI elements inside the image. No gore, no blood, no open wounds. Professional patient-education tone.
""".strip()


def generate_topic_image(topic: str, hook: str, rid: str, variant: str = "post") -> str:
    Path("generated").mkdir(exist_ok=True)
    out_path = f"generated/{variant}_{rid}.png"
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key.startswith("sk-"):
        logger.warning("OPENAI_API_KEY missing; using fallback artwork.")
        return _fallback_artwork(out_path, topic, variant)

    model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2").strip() or "gpt-image-2"
    quality = os.environ.get("OPENAI_IMAGE_QUALITY", "medium").strip() or "medium"
    size = os.environ.get("OPENAI_IMAGE_SIZE", "1024x1536").strip() or "1024x1536"

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    prompt = build_medical_image_prompt(topic, hook, variant)
    try:
        logger.info("GPT Image generation starting: model=%s size=%s quality=%s variant=%s", model, size, quality, variant)
        result = client.images.generate(model=model, prompt=prompt, size=size, quality=quality, n=1)
        image_base64 = result.data[0].b64_json
        Path(out_path).write_bytes(base64.b64decode(image_base64))
        logger.info("GPT Image generation successful: %s", out_path)
        return out_path
    except Exception as exc:
        logger.warning("GPT Image generation failed (%s); using fallback artwork.", exc)
        return _fallback_artwork(out_path, topic, variant)
