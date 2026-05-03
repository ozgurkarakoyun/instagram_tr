"""
AI Instagram Agent TR Klinik İçerik Sistemi
Özellikler:
1. Konudan gönderi + story üretimi
2. Yüklenen görseli GPT Image ile gönderi/story tasarımına dönüştürme
3. Okunabilir başlık/hook bindirme
4. Güncel konu önerileri
5. Caption + hashtag üretimi
6. Carousel üretimi
7. Basit hasta bilgisi maskeleme
8. İçerik arşivi
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from ai.image_edit import edit_uploaded_image
from ai.image_generate import generate_topic_image
from ai.tr_content import (
    DISCLAIMER,
    generate_carousel_slides,
    generate_turkish_caption,
    generate_turkish_hashtags,
    generate_turkish_hook,
    suggest_current_topics,
)
from archive_store import add_archive, get_archive, list_archive
from media.privacy import mask_patient_info
from media.template_tr import build_carousel_slide, build_turkish_asset

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
logger = logging.getLogger("instagram-agent-tr")

app = FastAPI(title="Türkçe AI Instagram Agent", description="Ortopedi ve travmatoloji için klinik sosyal medya içerik üretim sistemi", version="4.0.0-tr-clinic")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

for d in ("output", "static", "generated", "uploads", "archive"):
    Path(d).mkdir(exist_ok=True)

app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/generated", StaticFiles(directory="generated"), name="generated")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    request.state.request_id = rid
    start = time.time()
    response = await call_next(request)
    ms = round((time.time() - start) * 1000)
    response.headers["X-Request-ID"] = rid
    response.headers["X-Duration-Ms"] = str(ms)
    logger.info("[%s] %s %s %s (%sms)", rid, request.method, request.url.path, response.status_code, ms)
    return response


@app.get("/")
async def root():
    ui_path = Path("static/index.html")
    return HTMLResponse(content=ui_path.read_text(encoding="utf-8")) if ui_path.exists() else {"status": "running"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "4.0.0-tr-clinic",
        "openai_text_model": os.environ.get("OPENAI_TEXT_MODEL", "gpt-4o-mini"),
        "openai_image_model": os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2"),
        "timestamp": time.time(),
    }


@app.get("/suggest-topics")
async def suggest_topics():
    topics = suggest_current_topics()
    return JSONResponse(content={"topics": topics, "count": len(topics), "note": "PubMed/internet erişimi yoksa kürasyon listesi kullanılır."})


@app.get("/archive")
async def archive_list(limit: int = 50):
    return JSONResponse(content={"items": list_archive(limit=limit)})


@app.get("/archive/{job_id}")
async def archive_detail(job_id: str):
    item = get_archive(job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Arşiv kaydı bulunamadı.")
    return JSONResponse(content=item)


async def _save_upload(upload: UploadFile, rid: str) -> str:
    suffix = Path(upload.filename or "upload.png").suffix.lower() or ".png"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Sadece JPG, PNG veya WebP görsel yüklenebilir.")
    out = Path("uploads") / f"{rid}{suffix}"
    data = await upload.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Görsel boyutu 15 MB altında olmalıdır.")
    out.write_bytes(data)
    return str(out)


def _make_sources(mode: str, rid: str, topic: str, hook: str, image_path: str | None, mask_phi: bool) -> tuple[str, str, str | None]:
    masked_path = None
    if mode == "image":
        if not image_path:
            raise HTTPException(status_code=400, detail="Görsel modu için dosya yüklenmelidir.")
        masked_path = mask_patient_info(image_path, rid, enabled=mask_phi)
        post_source = masked_path
        story_source = masked_path
        try:
            post_source = edit_uploaded_image(masked_path, rid, topic, hook, "post")
            logger.info("[%s] GPT image edit post successful", rid)
        except Exception as exc:
            logger.warning("[%s] GPT image edit post failed, using masked upload: %s", rid, exc)
        try:
            story_source = edit_uploaded_image(masked_path, rid, topic, hook, "story")
            logger.info("[%s] GPT image edit story successful", rid)
        except Exception as exc:
            logger.warning("[%s] GPT image edit story failed, using masked upload: %s", rid, exc)
        return post_source, story_source, masked_path

    post_source = generate_topic_image(topic=topic, hook=hook, rid=rid, variant="post")
    story_source = generate_topic_image(topic=topic, hook=hook, rid=rid, variant="story")
    return post_source, story_source, masked_path


@app.post("/create-content")
async def create_content(
    request: Request,
    mode: str = Form(default="topic"),
    topic: str = Form(...),
    tone: str = Form(default="professional"),
    carousel_count: int = Form(default=5),
    mask_phi: bool = Form(default=True),
    upload: UploadFile | None = File(default=None),
):
    rid = getattr(request.state, "request_id", uuid.uuid4().hex[:8])
    mode = (mode or "topic").strip().lower()
    topic = (topic or "").strip()
    if mode not in {"topic", "image"}:
        raise HTTPException(status_code=400, detail="mode 'topic' veya 'image' olmalıdır.")
    if not topic:
        raise HTTPException(status_code=400, detail="Konu boş olamaz.")

    logger.info("[%s] create-content mode=%s topic=%r tone=%s", rid, mode, topic, tone)
    uploaded_path = await _save_upload(upload, rid) if upload else None

    hook = generate_turkish_hook(topic)
    caption = generate_turkish_caption(topic=topic, hook=hook, tone=tone)
    hashtags = generate_turkish_hashtags(topic)
    slides = generate_carousel_slides(topic=topic, hook=hook, count=carousel_count)
    full_caption = f"{caption}\n\n{' '.join(hashtags)}".strip()

    try:
        post_source, story_source, masked_path = _make_sources(mode, rid, topic, hook, uploaded_path, mask_phi)
        post_path = f"output/post_{rid}.jpg"
        story_path = f"output/story_{rid}.jpg"
        build_turkish_asset(post_source, post_path, topic, hook, "post")
        build_turkish_asset(story_source, story_path, topic, hook, "story")

        carousel_paths = []
        for i, slide in enumerate(slides, start=1):
            cpath = f"output/carousel_{rid}_{i}.jpg"
            build_carousel_slide(post_source, cpath, slide, i, len(slides))
            carousel_paths.append(cpath)
    except Exception as exc:
        logger.exception("[%s] Media generation failed", rid)
        raise HTTPException(status_code=500, detail=f"Görsel üretimi başarısız: {exc}")

    record = add_archive({
        "job_id": rid,
        "mode": mode,
        "topic": topic,
        "tone": tone,
        "hook": hook,
        "caption": caption,
        "hashtags": hashtags,
        "full_caption": full_caption,
        "slides": slides,
        "outputs": {"post": f"/{post_path}", "story": f"/{story_path}", "carousel": [f"/{p}" for p in carousel_paths]},
        "sources": {"uploaded": f"/{uploaded_path}" if uploaded_path else None, "masked": f"/{masked_path}" if masked_path else None, "post_source": f"/{post_source}", "story_source": f"/{story_source}"},
        "medical_disclaimer": DISCLAIMER,
    })

    return JSONResponse(content={**record, "preview_status": "ready", "publish_ready": False})


# Eski endpoint uyumluluğu: /create-post aynı işi konu modu ile yapar.
@app.post("/create-post")
async def create_post_compat(request: Request, topic: str = Form(...), tone: str = Form(default="professional")):
    return await create_content(request=request, mode="topic", topic=topic, tone=tone, carousel_count=5, mask_phi=True, upload=None)


@app.get("/preview/{filename}")
async def preview_file(filename: str):
    safe_name = Path(filename).name
    path = Path("output") / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    return FileResponse(str(path))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
