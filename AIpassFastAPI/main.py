import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import logging
import asyncio
import httpx
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import numpy as np
import cv2

from core.config import settings
from core.hardware import check_hardware_acceleration
from services.vision import vision_engine
from services.aggregator import start_aggregators, stop_aggregators
from services.webhook_client import webhook_client
from services.ocr_storage import process_violation_task
from utils.http_client import http_client
from api import stream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── START-UP ──────────────────────────────────────────────
    try:
        logger.info("Starting %s v%s", settings.PROJECT_NAME, settings.VERSION)

        os.makedirs("data/numberplate", exist_ok=True)
        os.makedirs("data/carnumber", exist_ok=True)

        check_hardware_acceleration()
        await http_client.start()
        await webhook_client.start()

        # Spring Boot에서 AI 대상 CCTV URL 동적 적용 (실패 시 .env fallback)
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                resp = await c.get(f"{settings.BACKEND_URL}/api/cctv/ai-target")
                data = resp.json()
                if data.get("success") and data.get("data", {}).get("url"):
                    vision_engine.rtsp_url = data["data"]["url"]
                    logger.info("[AI-Target] CCTV URL: %s", vision_engine.rtsp_url)
                else:
                    logger.warning("[AI-Target] 응답 파싱 실패 — fallback URL 사용")
        except Exception as e:
            logger.warning("[AI-Target] Spring Boot 미연결 — fallback URL 사용: %s", e)

        vision_engine.start()

        # 이벤트 처리 루프 (Process C) — process_event_loop 자체가 내부 루프를 가짐
        asyncio.create_task(vision_engine.process_event_loop())

        start_aggregators()

        logger.info("[SUCCESS] All services initialized. App is ready.")
        yield

    except Exception as e:
        logger.error("[CRITICAL] Failed to initialize: %s", e)
        raise

    # ── SHUT-DOWN ─────────────────────────────────────────────
    finally:
        logger.info("Shutting down gracefully...")
        await stop_aggregators()
        vision_engine.stop()
        await webhook_client.stop()
        await http_client.stop()
        logger.info("[SUCCESS] Shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stream.router, prefix="/api/v1")
app.mount("/demo", StaticFiles(directory="static", html=True), name="demo")
app.mount("/images", StaticFiles(directory="data"), name="images")


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "message": "AI-Pass Core is running"}


@app.post("/api/v1/test/trigger-violation", tags=["Test"])
async def test_trigger_violation(
    violation_type: str = Form(...),
    file: UploadFile = File(...),
):
    """[Postman 테스트용] 업로드된 이미지로 OCR 및 백엔드 전송을 강제 실행합니다."""
    contents = await file.read()
    frame = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    payload = await process_violation_task(frame, violation_type, 0.95)
    return {"status": "success", "payload_generated": payload}
