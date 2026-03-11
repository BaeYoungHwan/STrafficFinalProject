import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.config import settings
from core.hardware import check_hardware_acceleration
from services.vision import vision_engine
from api import stream
import asyncio


# 기본 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # [수정 완료] 예외 처리 및 안전한 자원 해제 구조 도입
    try:
        logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
        
        # 1. 하드웨어 점검
        check_hardware_acceleration()
        
        # TODO: AI 모델 로드, multiprocessing 큐 초기화 등
        logger.info("All core services initialized successfully.")
        
        yield
        
    except Exception as e:
        logger.error(f"[CRITICAL] Failed to initialize core services: {e}")
        raise e  # 서버 구동 중단
        
    finally:
        logger.info("Shutting down gracefully...")
        # TODO: 자원 해제, Fallback 큐 데이터 SQLite 저장 등
        logger.info("Shutdown complete.")

# FastAPI 인스턴스 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "AI-Pass Core is running"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
        check_hardware_acceleration()
        
        vision_engine.start()
        
        async def inference_worker():
            while True:
                # [QA 반영] 이제 process_inference_loop 자체가 awaitable 비동기 함수입니다.
                await vision_engine.process_inference_loop()
                await asyncio.sleep(0.001) # 컨텍스트 스위칭 최소 양보
                
        # 워커를 백그라운드 태스크로 등록
        asyncio.create_task(inference_worker())
        
        logger.info("All core services initialized successfully.")
        yield
        
    except Exception as e:
        logger.error(f"[CRITICAL] Failed to initialize core services: {e}")
        raise e
    finally:
        logger.info("Shutting down gracefully...")
        vision_engine.stop()
        logger.info("Shutdown complete.")

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)
app.include_router(stream.router, prefix="/api/v1")