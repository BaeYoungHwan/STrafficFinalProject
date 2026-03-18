import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from services.vision import vision_engine
from services.webhook_client import webhook_client

logger = logging.getLogger(__name__)

async def retry_scheduler():
    """1분마다 미전송 위반 데이터 복구 시도"""
    logger.info("🔄 [Scheduler] DLQ 재전송 스케줄러 가동 시작")
    while True:
        try:
            await webhook_client.retry_failed_payloads()
        except Exception as e:
            logger.error(f"🔴 [Scheduler] 재전송 중 예외 발생: {e}")
        
        # 60초 대기
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- [Startup: 서버 기동 시] ---
    try:
        # 1. AI 분석 엔진 시작 (강화대교 1채널 Headless)
        vision_engine.start()
        
        # 2. [V4.1 신규] 무결성 재전송 스케줄러 백그라운드 실행
        asyncio.create_task(retry_scheduler())
        
        logger.info("🚀 AI-Pass Headless Engine & Recovery Worker Started.")
        yield
        
    finally:
        # --- [Shutdown: 서버 종료 시] ---
        vision_engine.stop()
        logger.info("🛑 AI-Pass Engine Shut down.")

app = FastAPI(lifespan=lifespan)