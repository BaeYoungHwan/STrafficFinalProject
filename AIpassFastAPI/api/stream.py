import queue
import asyncio
import logging
from typing import AsyncGenerator
from collections import deque

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.vision import vision_engine
from services.aggregator import congestion_engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Stream"])

# 최근 과속 위반 목록 (메모리 캐시, 최대 100건)
_violation_cache: deque = deque(maxlen=100)


def push_violation(payload: dict):
    """speed_detector → webhook_client 경로에서 위반 발생 시 캐시에도 저장."""
    _violation_cache.appendleft(payload)


# ─────────────────────────────────────────────────────────────
# MJPEG 스트리밍
# ─────────────────────────────────────────────────────────────

async def _mjpeg_generator() -> AsyncGenerator[bytes, None]:
    """VisionEngine의 mjpeg_queue에서 JPEG 프레임을 꺼내 multipart 스트림으로 전송."""
    while True:
        try:
            frame_bytes: bytes = await asyncio.to_thread(
                vision_engine.mjpeg_queue.get, True, 1.0
            )
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame_bytes
                + b"\r\n"
            )
        except queue.Empty:
            # 프레임이 없으면 잠깐 대기 후 재시도
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning("[Stream] Generator error: %s", e)
            await asyncio.sleep(0.1)


@router.get(
    "/stream/video",
    summary="MJPEG 실시간 스트리밍",
    description="YOLO + 과속 감지가 적용된 영상을 MJPEG 포맷으로 스트리밍합니다. "
                "브라우저 `<img>` 태그의 `src`로 직접 사용 가능합니다.",
)
async def video_stream():
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ─────────────────────────────────────────────────────────────
# 소스 변경
# ─────────────────────────────────────────────────────────────

class StreamSourceRequest(BaseModel):
    url: str


@router.post(
    "/stream/source",
    summary="동영상 소스 변경",
    description="VisionEngine의 동영상 소스 URL을 변경하고 엔진을 재시작합니다. "
                "로컬 파일 경로, RTSP, HTTP URL 모두 지원합니다.",
)
async def change_stream_source(body: StreamSourceRequest):
    try:
        vision_engine.restart(body.url)
        logger.info("[Stream] Source changed to: %s", body.url)
        return {"success": True, "message": f"Stream source updated to: {body.url}"}
    except Exception as e:
        logger.error("[Stream] Failed to restart engine: %s", e)
        return {"success": False, "message": str(e)}


# ─────────────────────────────────────────────────────────────
# 상태 확인
# ─────────────────────────────────────────────────────────────

@router.get(
    "/stream/status",
    summary="스트리밍 엔진 상태 확인",
)
async def stream_status():
    reader_alive = (
        vision_engine.reader_process is not None
        and vision_engine.reader_process.is_alive()
    )
    ai_alive = (
        vision_engine.ai_process is not None
        and vision_engine.ai_process.is_alive()
    )
    congestion = await congestion_engine.get_status()

    return {
        "success": True,
        "data": {
            "video_source": vision_engine.rtsp_url,
            "reader_process": "running" if reader_alive else "stopped",
            "ai_process": "running" if ai_alive else "stopped",
            "mjpeg_queue_size": vision_engine.mjpeg_queue.qsize(),
            "congestion": congestion,
        },
    }


# ─────────────────────────────────────────────────────────────
# 과속 위반 목록
# ─────────────────────────────────────────────────────────────

@router.get(
    "/stream/violations",
    summary="최근 과속 위반 목록",
    description="메모리 캐시에 저장된 최근 과속 위반 이벤트 목록을 반환합니다 (최대 100건).",
)
async def get_violations(limit: int = 20):
    items = list(_violation_cache)[:limit]
    return {
        "success": True,
        "data": {
            "total": len(_violation_cache),
            "violations": items,
        },
    }
