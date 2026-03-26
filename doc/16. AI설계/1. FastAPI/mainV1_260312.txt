import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form
import numpy as np
import cv2

# Core 및 설정
from core.config import settings
from core.hardware import check_hardware_acceleration

# Services & Utils
from services.vision import vision_engine
from services.aggregator import start_aggregators, stop_aggregators
from services.ocr_storage import process_violation_task
from utils.http_client import http_client
from api import stream

# 기본 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ==========================================
    # [START-UP] 애플리케이션 시작 시퀀스
    # ==========================================
    try:
        logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
        
        # 1. 하드웨어 점검
        check_hardware_acceleration()
        
        # 2. 통신 클라이언트(Retry Queue) 켜기
        await http_client.start()
        
        # 3. 비전 엔진 프로세스 시작
        vision_engine.start()
        
        # 4. 비동기 추론 백그라운드 워커 등록
        async def inference_worker():
            while True:
                await vision_engine.process_inference_loop()
                await asyncio.sleep(0.001) # 컨텍스트 스위칭 최소 양보
                
        asyncio.create_task(inference_worker())
        
        # 5. 혼잡도 & 예지보전 센서 스케줄러 시작
        start_aggregators()
        
        logger.info("[SUCCESS] All core services initialized successfully. App is ready.")
        yield
        
    except Exception as e:
        logger.error(f"[CRITICAL] Failed to initialize core services: {e}")
        raise e
        
    # ==========================================
    # [SHUT-DOWN] 애플리케이션 종료 시퀀스
    # ==========================================
    finally:
        logger.info("Shutting down gracefully...")
        
        # 1. 스케줄러 태스크 안전 해제
        await stop_aggregators()
        
        # 2. 비전 엔진 해제
        vision_engine.stop()
        
        # 3. 통신 모듈 종료 및 큐 백업
        await http_client.stop()
        
        logger.info("[SUCCESS] Shutdown complete. All resources freed.")

# 단일 FastAPI 인스턴스 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# API 라우터 등록
app.include_router(stream.router, prefix="/api/v1")

# ------------------------------------------
# Endpoints
# ------------------------------------------

@app.get("/health", tags=["System"])
async def health_check():
    """서버 상태 확인용"""
    return {"status": "ok", "message": "AI-Pass Core is running"}

@app.post("/api/v1/test/trigger-violation", tags=["Test"])
async def test_trigger_violation(
    violation_type: str = Form(...),
    file: UploadFile = File(...)
):
    """[Postman 테스트용] 업로드된 이미지로 OCR 및 백엔드 전송을 강제 실행합니다."""
    # 1. 업로드된 이미지를 OpenCV 배열로 디코딩
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 2. 강제 위반 프로세스 태우기
    payload = await process_violation_task(frame, violation_type, 0.95)
    
    return {"status": "success", "payload_generated": payload}