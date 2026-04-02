import os
import queue
import asyncio
import logging
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from core.config import settings
from services.vision import vision_engine
from services.aggregator import congestion_engine
from services.webhook_client import webhook_client
import services.violation_cache as vcache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Stream"])


# ─────────────────────────────────────────────────────────────
# MJPEG 스트리밍
# ─────────────────────────────────────────────────────────────

async def _mjpeg_generator() -> AsyncGenerator[bytes, None]:
    """VisionEngine의 mjpeg_queue에서 JPEG 프레임을 꺼내 multipart 스트림으로 전송."""
    while True:
        try:
            frame_bytes: bytes = vision_engine.mjpeg_queue.get_nowait()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame_bytes
                + b"\r\n"
            )
            await asyncio.sleep(0)  # 이벤트 루프 양보
        except queue.Empty:
            await asyncio.sleep(1 / 30)  # 30fps 폴링 — 스레드풀 미사용
        except Exception as e:
            logger.warning("[Stream] Generator error: %s", e)
            await asyncio.sleep(0.1)


@router.get("/stream/video", summary="MJPEG 실시간 스트리밍")
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


@router.post("/stream/source", summary="동영상 소스 변경")
async def change_stream_source(body: StreamSourceRequest):
    try:
        first_start = vision_engine.reader_process is None
        await asyncio.to_thread(vision_engine.restart, body.url)
        if first_start:
            asyncio.create_task(vision_engine.process_event_loop())
        logger.info("[Stream] Source changed to: %s", body.url)
        return {"success": True, "message": f"Stream source updated to: {body.url}"}
    except Exception as e:
        logger.error("[Stream] Failed to restart engine: %s", e)
        return {"success": False, "message": str(e)}


# ─────────────────────────────────────────────────────────────
# 상태 확인
# ─────────────────────────────────────────────────────────────

@router.get("/stream/status", summary="스트리밍 엔진 상태 확인")
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

@router.get("/stream/violations", summary="최근 과속 위반 목록")
async def get_violations(limit: int = 20):
    return {
        "success": True,
        "data": {
            "total": vcache.total(),
            "violations": vcache.get_recent(limit),
        },
    }


# ─────────────────────────────────────────────────────────────
# DLQ 수동 재전송
# ─────────────────────────────────────────────────────────────

@router.post("/stream/retry-dlq", summary="DLQ 실패 이벤트 즉시 재전송")
async def retry_dlq():
    """data/fallback_queue.jsonl에 쌓인 전송 실패 이벤트를 Spring Boot로 즉시 재전송.
    Spring Boot 재시작 후 호출하여 누락 단속내역을 복구할 때 사용."""
    dlq_path = "data/fallback_queue.jsonl"
    if not os.path.exists(dlq_path):
        return {"success": True, "message": "DLQ 파일 없음 (재전송할 항목 없음)", "pending": 0}
    try:
        with open(dlq_path, "r", encoding="utf-8") as f:
            pending = sum(1 for line in f if line.strip())
    except Exception:
        pending = -1
    await webhook_client.retry_failed_payloads()
    return {"success": True, "message": "DLQ 재전송 완료", "pending": pending}
