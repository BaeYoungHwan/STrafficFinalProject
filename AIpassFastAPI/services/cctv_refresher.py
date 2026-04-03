"""
CCTV 스트림 URL 자동 갱신 서비스

ITS Open API에서 최신 CCTV 스트림 URL을 가져와 cctv_info DB 테이블을 갱신합니다.
- 앱 시작 시 1회 즉시 갱신
- 이후 4시간 주기로 자동 갱신 (ITS 토큰 만료 전 선제 갱신)
"""

import asyncio
import logging
import httpx
import psycopg2
from datetime import datetime
from core.config import settings

logger = logging.getLogger(__name__)

# 갱신 주기: 4시간 (ITS 토큰 유효시간 ~4~5h 이내)
REFRESH_INTERVAL_SEC = 4 * 60 * 60

# 모듈 레벨 상태 변수 — 마지막 갱신 시각 및 갱신 건수
_last_refresh_time: datetime | None = None
_last_refresh_count: int = 0


def _get_db_conn():
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )


async def fetch_its_cctv_urls() -> list[dict]:
    """ITS API 호출 → CCTV 목록 반환. 최대 3회 재시도."""
    url = settings.CCTV_INFO_URL.strip()
    if not url:
        logger.warning("[CCTVRefresh] CCTV_INFO_URL 미설정 — 갱신 건너뜀")
        return []

    retry_delays = [0, 1, 3]  # 초기 시도 후 1초, 3초 대기

    for attempt in range(1, 4):
        if attempt > 1:
            delay = retry_delays[attempt - 1]
            logger.warning("[CCTVRefresh] ITS API 재시도 %d/3...", attempt)
            await asyncio.sleep(delay)

        try:
            async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            logger.info("[CCTVRefresh] ITS API 원본: %s", str(data)[:300])

            # ITS API 응답 파싱: response.data (배열)
            try:
                items = data["response"]["data"]
                if not isinstance(items, list):
                    items = [items]
            except (KeyError, TypeError) as e:
                logger.error("[CCTVRefresh] 응답 파싱 실패: %s | 원본: %s", e, str(data)[:300])
                return []

            return items

        except Exception as e:
            logger.error("[CCTVRefresh] ITS API 호출 실패 (시도 %d/3): %s", attempt, e)
            if attempt == 3:
                logger.error("[CCTVRefresh] 3회 재시도 모두 실패 — 빈 목록 반환")
                return []

    return []


def upsert_cctv_urls(items: list[dict]) -> int:
    """DB cctv_info 테이블에 스트림 URL을 UPSERT."""
    if not items:
        return 0

    updated = 0
    conn = _get_db_conn()
    try:
        with conn.cursor() as cur:
            for item in items:
                stream_url = str(item.get("cctvurl") or item.get("cctvUrl") or "").strip()
                if not stream_url:
                    continue
                # cctvurl에서 ID 추출: http://cctvsec.ktict.co.kr/4700/TOKEN → "4700"
                try:
                    cctv_id_raw = stream_url.split("cctvsec.ktict.co.kr/")[1].split("/")[0]
                except (IndexError, AttributeError):
                    logger.warning("[CCTVRefresh] cctvurl에서 ID 추출 실패: %s", stream_url[:60])
                    continue

                db_cctv_id = cctv_id_raw  # DB cctv_id: "4700" (ITS_ 접두어 없음)
                cur.execute(
                    """
                    UPDATE cctv_info
                       SET stream_url = %s,
                           updated_at = NOW()
                     WHERE cctv_id = %s
                    """,
                    (stream_url, db_cctv_id),
                )
                if cur.rowcount > 0:
                    updated += 1
                    logger.info("[CCTVRefresh] %s 갱신 성공", db_cctv_id)
                else:
                    logger.warning("[CCTVRefresh] %s DB 미일치 (레코드 없음)", db_cctv_id)
        conn.commit()
    finally:
        conn.close()

    return updated


async def refresh_once() -> tuple[int, int]:
    """ITS API 호출 → DB 갱신 1회 실행. (갱신 건수, 전체 항목 수) 튜플 반환."""
    global _last_refresh_time, _last_refresh_count
    try:
        items = await fetch_its_cctv_urls()
        if not items:
            return (0, 0)
        count = await asyncio.to_thread(upsert_cctv_urls, items)
        logger.info("[CCTVRefresh] 갱신 완료: %d/%d 건", count, len(items))
        _last_refresh_time = datetime.now()
        _last_refresh_count = count
        return (count, len(items))
    except Exception as e:
        logger.error("[CCTVRefresh] 갱신 실패: %s", e)
        return (0, 0)


async def start_cctv_refresh_loop():
    """앱 시작 시 즉시 1회 갱신 후, 4시간 주기로 반복."""
    logger.info("[CCTVRefresh] URL 갱신 서비스 시작 (주기: %dh)", REFRESH_INTERVAL_SEC // 3600)
    await refresh_once()
    while True:
        await asyncio.sleep(REFRESH_INTERVAL_SEC)
        await refresh_once()


async def start_cctv_refresh_loop_only():
    """초기 갱신 없이 4시간 주기 반복만 실행 (lifespan에서 이미 갱신한 경우 사용)."""
    while True:
        await asyncio.sleep(REFRESH_INTERVAL_SEC)
        await refresh_once()
