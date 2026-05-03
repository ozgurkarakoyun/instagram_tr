"""
AI Instagram Agent TR
Doç. Dr. Özgür Karakoyun için Türkçe ortopedi/travmatoloji içerik sistemi.

Yeni akış:
- Resim yüklenmez.
- Konuya göre GPT Image ile kaynak görsel üretilir.
- Sadece gönderi ve story çıktısı alınır.
- Başlık/hook/footer okunabilir şekilde sonradan şablona basılır.
- Güncel ortopedi konu önerileri sayfası/endpoint'i vardır.
"""

import logging
import os
import time
import uuid
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from ai.image_generate import generate_topic_image
from ai.tr_content import (
    DISCLAIMER,
    generate_turkish_caption,
    generate_turkish_hashtags,
    generate_turkish_hook,
    suggest_current_topics,
)
from media.template_tr import build_turkish_asset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("instagram-agent-tr")

app = FastAPI(
    title="Türkçe AI Instagram Agent",
    description="Doç. Dr. Özgür Karakoyun için Türkçe ortopedi/travmatoloji gönderi ve story üretimi",
    version="3.0.0-tr",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for d in ("output", "static", "generated"):
    Path(d).mkdir(exist_ok=True)

app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/generated", StaticFiles(directory="generated"), name="generated")
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
    if ui_path.exists():
        return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))
    return {"status": "running", "version": "3.0.0-tr"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "3.0.0-tr",
        "openai_text_model": os.environ.get("OPENAI_TEXT_MODEL", "gpt-4o-mini"),
        "openai_image_model": os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2"),
        "timestamp": time.time(),
    }


@app.get("/suggest-topics")
async def suggest_topics():
    """Return current/trending orthopedic and traumatology topic suggestions."""
    topics = suggest_current_topics()
    return JSONResponse(content={
        "topics": topics,
        "count": len(topics),
        "note": "PubMed/internet erişimi başarısız olursa kürasyon listesi kullanılır.",
    })


@app.post("/create-post")
async def create_post(
    request: Request,
    topic: str = Form(...),
    tone: str = Form(default="professional"),
):
    rid = getattr(request.state, "request_id", uuid.uuid4().hex[:8])
    topic = (topic or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Konu boş olamaz.")

    logger.info("[%s] Turkish generation topic=%r tone=%s", rid, topic, tone)

    try:
        hook = generate_turkish_hook(topic)
        caption = generate_turkish_caption(topic=topic, hook=hook, tone=tone)
        hashtags = generate_turkish_hashtags(topic)
    except Exception as exc:
        logger.error("[%s] AI text generation failed: %s", rid, exc)
        raise HTTPException(status_code=500, detail=f"Metin üretimi başarısız: {exc}")

    hashtag_str = " ".join(hashtags)
    full_caption = f"{caption}\n\n{hashtag_str}".strip()

    try:
        source_post = generate_topic_image(topic=topic, hook=hook, rid=rid, variant="post")
        source_story = generate_topic_image(topic=topic, hook=hook, rid=rid, variant="story")

        post_path = f"output/post_{rid}.jpg"
        story_path = f"output/story_{rid}.jpg"
        build_turkish_asset(source_post, post_path, topic, hook, "post")
        build_turkish_asset(source_story, story_path, topic, hook, "story")
    except Exception as exc:
        logger.error("[%s] Media generation failed: %s", rid, exc)
        raise HTTPException(status_code=500, detail=f"Görsel üretimi başarısız: {exc}")

    logger.info("[%s] Done -> post + story", rid)
    return JSONResponse(content={
        "job_id": rid,
        "topic": topic,
        "hook": hook,
        "generated_caption": caption,
        "generated_hashtags": hashtags,
        "full_caption": full_caption,
        "medical_disclaimer": DISCLAIMER,
        "outputs": {
            "post": f"/{post_path}",
            "story": f"/{story_path}",
        },
        "generated_sources": {
            "post_source": f"/{source_post}",
            "story_source": f"/{source_story}",
        },
        "preview_status": "ready",
        "publish_ready": False,
        "next_step": "Gönderi ve story görsellerini indirip Instagram'da paylaşabilirsiniz.",
    })


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
