"""
CCTV 갱신 API 라우터

POST /api/v1/cctv/refresh       — ITS API 즉시 갱신
GET  /api/v1/cctv/refresh/status — 마지막 갱신 상태 조회
"""

import logging
from fastapi import APIRouter
from services.cctv_refresher import refresh_once, _last_refresh_time, _last_refresh_count
import services.cctv_refresher as cctv_refresher_module

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cctv", tags=["CCTV"])


@router.post("/refresh")
async def trigger_refresh():
    """ITS API를 즉시 호출하여 DB CCTV URL을 갱신합니다."""
    count, total = await refresh_once()
    return {
        "success": total > 0 or count >= 0,
        "updated": count,
        "total": total,
    }


@router.get("/refresh/status")
async def get_refresh_status():
    """마지막 CCTV URL 갱신 시각과 갱신 건수를 반환합니다."""
    last_time = cctv_refresher_module._last_refresh_time
    last_count = cctv_refresher_module._last_refresh_count
    return {
        "last_refresh": last_time.isoformat() if last_time is not None else None,
        "last_count": last_count,
    }
