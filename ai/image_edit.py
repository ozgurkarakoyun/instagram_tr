"""
ai/image_edit.py
Yüklenen görseli GPT Image edit ile konuya uygun post/story kaynak görsele dönüştürür.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Literal

from PIL import Image

logger = logging.getLogger(__name__)
OUTPUT_DIR = Path("generated/edited")
SUPPORTED_INPUT_EXT = {".jpg", ".jpeg", ".png", ".webp"}
FormatType = Literal["post", "story"]


def _prepare_image_for_api(input_path: str, job_id: str) -> Path:
    src = Path(input_path)
    if src.suffix.lower() not in SUPPORTED_INPUT_EXT:
        raise ValueError(f"Görsel düzenleme için JPG/PNG/WebP gerekir: {src.suffix!r}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prepared = OUTPUT_DIR / f"source_{job_id}.png"
    img = Image.open(src).convert("RGB")
    max_side = 2048
    w, h = img.size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    img.save(prepared, "PNG", optimize=True)
    return prepared


def edit_uploaded_image(input_path: str, job_id: str, topic: str, hook: str = "", target_format: FormatType = "post") -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key.startswith("sk-"):
        raise RuntimeError("OPENAI_API_KEY is not set.")
    model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2").strip() or "gpt-image-2"
    size = os.environ.get("OPENAI_IMAGE_SIZE", "1024x1536").strip() or "1024x1536"
    quality = os.environ.get("OPENAI_IMAGE_QUALITY", "medium").strip() or "medium"

    prompt = f"""
Edit the uploaded image for a orthopedic and traumatology Instagram {target_format}.
Topic: {topic}
Hook: {hook}

Goal:
- Transform the uploaded image into a clean, premium, trustworthy medical social media background.
- Preserve the clinically relevant main subject when it is an X-ray, implant image, clinic image, rehab image, or orthopedic educational image.
- Remove or obscure patient-identifying details such as names, dates, barcodes, QR codes, protocol numbers, phone numbers and faces when present.
- Use safe healthcare colors: dark navy, teal, mint, white, clean clinical blue.
- Leave clear space in the upper third for a readable title/hook overlay and a clean lower footer area.
- Do not add text, logos, watermarks, fake labels, numbers, signatures, or claims; the app will add text later.
- Avoid gore, blood, open wounds, fear-based content and unrealistic before/after claims.
""".strip()

    prepared = _prepare_image_for_api(input_path, job_id)
    out_path = OUTPUT_DIR / f"edited_{target_format}_{job_id}.png"
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    with prepared.open("rb") as image_file:
        response = client.images.edit(model=model, image=image_file, prompt=prompt, size=size, quality=quality, n=1, output_format="png")
    out_path.write_bytes(base64.b64decode(response.data[0].b64_json))
    logger.info("GPT image edit produced %s using %s", out_path, model)
    return str(out_path)
