"""
ai/image_generate.py
Generate source artwork from a topic using OpenAI GPT Image models.
The final title, hook, and footer are rendered by Pillow templates for readability.
"""

import base64
import logging
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

SAFE_PALETTE = "deep navy, teal, soft turquoise, white, clean medical blue, subtle green accents"


def _fallback_artwork(path: str, topic: str, variant: str) -> str:
    """Create a simple non-AI fallback image if GPT Image is unavailable."""
    w, h = (1024, 1536)
    img = Image.new("RGB", (w, h), (10, 34, 58))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        r = int(10 + y / h * 10)
        g = int(34 + y / h * 45)
        b = int(58 + y / h * 55)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    # soft clinical shapes
    draw.ellipse((-180, -160, 520, 520), outline=(34, 211, 198), width=42)
    draw.ellipse((520, 980, 1260, 1720), outline=(88, 198, 255), width=36)
    # abstract orthopedic/medical background; final text is rendered by the template
    draw.rounded_rectangle((120, 470, 904, 1000), radius=54, fill=(255, 255, 255, 20), outline=(99, 230, 218), width=3)
    draw.line((210, 680, 814, 680), fill=(122, 231, 211), width=18)
    draw.line((500, 520, 500, 910), fill=(88, 198, 255), width=14)
    draw.ellipse((420, 600, 580, 760), outline=(248, 253, 255), width=10)
    img.save(path, quality=95)
    return path


def build_medical_image_prompt(topic: str, hook: str, variant: str) -> str:
    aspect = "vertical Instagram post/story composition, 9:16 portrait"
    return f"""
Create a premium Turkish healthcare social media background image for an orthopedic and traumatology educational Instagram {variant}.
Topic: {topic}
Hook idea: {hook}
Style: trustworthy, safe, modern medical, orthopedic clinic aesthetic, {SAFE_PALETTE}.
Visual direction: clean orthopedic illustration or realistic medical editorial scene related to the topic; bone, joint, spine, trauma care, rehabilitation, operating-room planning, or diagnostic concept when relevant.
Composition: {aspect}; leave clear empty space in the upper third for a Turkish title and hook overlay, and leave a clean lower footer area.
Important: do NOT write any text, letters, logos, numbers, watermarks, signatures, captions, labels, or UI elements inside the image. No frightening gore, no blood, no open wounds. Professional patient-education tone.
""".strip()


def generate_topic_image(topic: str, hook: str, rid: str, variant: str = "post") -> str:
    """Generate a source image from text. Returns a local file path."""
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
        result = client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )
        image_base64 = result.data[0].b64_json
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(image_base64))
        logger.info("GPT Image generation successful: %s", out_path)
        return out_path
    except Exception as exc:
        logger.warning("GPT Image generation failed (%s); using fallback artwork.", exc)
        return _fallback_artwork(out_path, topic, variant)
