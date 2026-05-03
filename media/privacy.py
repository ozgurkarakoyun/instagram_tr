"""
media/privacy.py
Basit hasta bilgisi maskeleme: EXIF temizleme, kenar/bant maskeleme ve görseli API'ye güvenli hazırlama.
Not: OCR tabanlı kesin anonimleştirme değildir; nihai kontrol kullanıcı sorumluluğundadır.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

logger = logging.getLogger(__name__)


def mask_patient_info(input_path: str, job_id: str, enabled: bool = True) -> str:
    Path("uploads/masked").mkdir(parents=True, exist_ok=True)
    out_path = f"uploads/masked/masked_{job_id}.png"
    img = Image.open(input_path).convert("RGB")
    # EXIF stripped by saving as new PNG.
    if not enabled:
        img.save(out_path, "PNG")
        return out_path

    w, h = img.size
    draw = ImageDraw.Draw(img, "RGBA")
    # X-ray / clinical screenshots often place identifiers on borders. Mask conservative bands.
    top = int(h * 0.115)
    bottom = int(h * 0.10)
    side = int(w * 0.055)
    fill = (3, 20, 38, 238)
    draw.rectangle([0, 0, w, top], fill=fill)
    draw.rectangle([0, h - bottom, w, h], fill=fill)
    draw.rectangle([0, 0, side, h], fill=(3, 20, 38, 168))
    draw.rectangle([w - side, 0, w, h], fill=(3, 20, 38, 168))

    # Extra blur in common corner labels/QR/barcode zones.
    zones = [
        (0, 0, int(w * .42), int(h * .18)),
        (int(w * .58), 0, w, int(h * .18)),
        (0, int(h * .82), int(w * .45), h),
        (int(w * .55), int(h * .82), w, h),
    ]
    for box in zones:
        crop = img.crop(box).filter(ImageFilter.GaussianBlur(8))
        img.paste(crop, box[:2])
        ImageDraw.Draw(img, "RGBA").rectangle(box, fill=(3, 20, 38, 110))

    img.save(out_path, "PNG", optimize=True)
    logger.info("Masked possible PHI zones: %s", out_path)
    return out_path
