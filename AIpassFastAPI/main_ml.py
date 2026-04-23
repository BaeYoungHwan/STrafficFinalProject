"""AIpass 예지보전 ML 전용 경량 FastAPI 앱.

이 파일은 OCR / YOLO / CCTV 스트리밍 / 날씨 스크래핑 없이
예지보전 시뮬레이터만 가동합니다. 학습 데이터 수집 단계 전용.

실행 (PowerShell):
  $env:SIMULATOR_ENABLED = "true"
  venv/Scripts/python.exe -m uvicorn main_ml:app --host 0.0.0.0 --port 8000
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.predictive.scheduler import start_simulator, stop_simulator
from api import predictive as predictive_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── START-UP ──────────────────────────────────────────────
    logger.info("Starting AIpass Simulator (ML-only mode) — OCR/YOLO/CCTV 비활성")
    try:
        await start_simulator()
        logger.info("[SUCCESS] Simulator running. Waiting END_TIME.")
        yield
    except Exception as e:
        logger.error("[CRITICAL] Simulator 시작 실패: %s", e)
        raise
    # ── SHUT-DOWN ─────────────────────────────────────────────
    finally:
        logger.info("Shutting down...")
        await stop_simulator()
        logger.info("[SUCCESS] Shutdown complete.")


app = FastAPI(
    title="AIpass Predictive Simulator (ML-only)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(predictive_router.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "mode": "ml-simulator"}
