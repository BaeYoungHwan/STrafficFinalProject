"""
Naver Weather 날씨 스크래퍼 서비스

매일 오전 9시, https://weather.naver.com/today/09110615 에서
인천 강화군 날씨를 스크래핑해 weather_log 테이블에 저장합니다.
- 앱 시작 시 오늘 데이터가 없으면 즉시 1회 수집
- 이후 매일 오전 9시 자동 수집
"""

import asyncio
import logging
import re
import psycopg2
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from core.config import settings

logger = logging.getLogger(__name__)

WEATHER_URL = "https://weather.naver.com/today/09110615"
INTERSECTION_ID = 1
TARGET_HOUR = 9

# 풍향 한→영 변환 (길이 긴 것 먼저 매칭)
_WIND_DIR_MAP = {
    "북북동": "NNE", "북동": "NE", "동북동": "ENE",
    "동남동": "ESE", "남동": "SE", "남남동": "SSE",
    "남남서": "SSW", "남서": "SW", "서남서": "WSW",
    "서북서": "WNW", "북서": "NW", "북북서": "NNW",
    "북": "N", "동": "E", "남": "S", "서": "W",
}


# ── DB 연결 ────────────────────────────────────────────────────

def _get_db_conn():
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )


# ── 스케줄 유틸 ────────────────────────────────────────────────

def _seconds_until_next_9am() -> float:
    now = datetime.now()
    target = now.replace(hour=TARGET_HOUR, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return (target - now).total_seconds()


# ── 파싱 헬퍼 ──────────────────────────────────────────────────

def _parse_wind(raw: str) -> tuple:
    """"서 3.5m/s" → (3.5, "W")"""
    direction = None
    speed = None
    for kor, eng in _WIND_DIR_MAP.items():
        if kor in raw:
            direction = eng
            break
    m = re.search(r"(-?\d+\.?\d*)", raw)
    if m:
        speed = float(m.group(1))
    return speed, direction


def _parse_visibility(raw: str):
    """"13km" → 13000, "500m" → 500"""
    m = re.search(r"(\d+\.?\d*)\s*(km|m)", raw, re.IGNORECASE)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    return int(value * 1000 if unit == "km" else value)


def _parse_float(raw):
    if not raw:
        return None
    m = re.search(r"(\d+\.?\d*)", str(raw))
    return float(m.group(1)) if m else None


def _map_sky_condition(raw: str) -> str:
    """네이버 원문 → DB 저장값 (프론트 아이콘 연동)"""
    raw = raw.strip()
    if re.search(r"맑음|화창", raw):
        return "맑음"
    if re.search(r"구름많음", raw):
        return "구름많음"
    if re.search(r"흐림", raw):
        return "흐림"
    if re.search(r"비|소나기", raw):
        return "비"
    if re.search(r"눈", raw):
        return "눈"
    return raw


def _map_precip_type(sky: str, precip_mm: float) -> str:
    if precip_mm == 0:
        return "NONE"
    if re.search(r"눈", sky):
        return "SNOW"
    if re.search(r"진눈깨비", sky):
        return "SLEET"
    return "RAIN"


# ── DB 조회/저장 (blocking) ────────────────────────────────────

def _check_today_collected() -> bool:
    """오늘 이미 수집된 데이터가 있는지 확인."""
    try:
        conn = _get_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM weather_log WHERE collected_at >= CURRENT_DATE"
                )
                return cur.fetchone()[0] > 0
        finally:
            conn.close()
    except Exception as e:
        logger.error("[Weather] 오늘 데이터 확인 실패: %s", e)
        return False


def insert_weather_log(data: dict) -> None:
    """weather_log 테이블에 INSERT (blocking, asyncio.to_thread로 호출)."""
    conn = _get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO weather_log (
                    intersection_id, temperature, humidity, wind_speed,
                    wind_direction, precipitation, precipitation_type,
                    sky_condition, visibility, collected_at
                ) VALUES (
                    %(intersection_id)s, %(temperature)s, %(humidity)s, %(wind_speed)s,
                    %(wind_direction)s, %(precipitation)s, %(precipitation_type)s,
                    %(sky_condition)s, %(visibility)s, %(collected_at)s
                )
                """,
                data,
            )
        conn.commit()
        logger.info(
            "[Weather] 저장 완료 — 기온:%.1f°C 습도:%s%% 하늘:%s",
            data["temperature"],
            data.get("humidity", "-"),
            data.get("sky_condition", "-"),
        )
    except Exception as e:
        logger.error("[Weather] DB INSERT 실패: %s", e)
        conn.rollback()
        raise
    finally:
        conn.close()


# ── 셀렉터 추출 헬퍼 ──────────────────────────────────────────

async def _try_get_temperature(page) -> float | None:
    selectors = [
        ".temperature_text",
        ".current_temperature",
        ".today_temperature",
        "[class*='temperature']",
        "strong[class*='temp']",
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                raw = await el.inner_text()
                m = re.search(r"(-?\d+\.?\d*)", raw.replace("−", "-"))
                if m:
                    return float(m.group(1))
        except Exception:
            continue
    return None


async def _try_get_sky(page) -> str | None:
    selectors = [
        ".today_condition em",
        ".weather_main .blind",
        ".cndtn",
        "[class*='condition'] em",
        ".summary_area .weather",
        ".today_weather em",
        "[class*='weather_icon'] .blind",
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                raw = (await el.inner_text()).strip()
                if raw and len(raw) < 20:
                    return raw
        except Exception:
            continue
    return None


async def _try_get_details(page) -> tuple:
    """습도/풍속/강수량/시정 추출 — dt/dd 쌍 파싱."""
    humidity = wind_raw = precip_raw = visibility_raw = None
    try:
        dts = await page.locator("dt").all()
        dds = await page.locator("dd").all()
        pairs = {}
        for dt, dd in zip(dts, dds):
            try:
                key = (await dt.inner_text()).strip()
                val = (await dd.inner_text()).strip()
                if key and val:
                    pairs[key] = val
            except Exception:
                continue

        # 키 이름 기반 매칭
        hum_raw = pairs.get("습도") or pairs.get("현재습도")
        if hum_raw:
            m = re.search(r"(\d+)", hum_raw)
            if m:
                humidity = int(m.group(1))

        wind_raw = (
            pairs.get("바람") or pairs.get("풍속") or pairs.get("풍향·풍속")
        )
        precip_raw = pairs.get("강수량") or pairs.get("1시간 강수량")
        visibility_raw = pairs.get("시정") or pairs.get("가시거리")

        # 키 매칭 실패 시 값 패턴으로 fallback
        if wind_raw is None:
            for val in pairs.values():
                if re.search(r"\d+\.?\d*\s*m/s", val):
                    wind_raw = val
                    break
        if humidity is None:
            for val in pairs.values():
                m = re.search(r"^(\d+)\s*%$", val.strip())
                if m:
                    humidity = int(m.group(1))
                    break
        if precip_raw is None:
            for val in pairs.values():
                if re.search(r"^\d+\.?\d*\s*mm$", val.strip()):
                    precip_raw = val
                    break
    except Exception as e:
        logger.debug("[Weather] dt/dd 파싱 실패: %s", e)

    return humidity, wind_raw, precip_raw, visibility_raw


# ── 3차 fallback: 정규식 전체 텍스트 파싱 ─────────────────────

def _regex_temperature(text: str) -> float | None:
    for pat in [r"현재\s*온도\s*(-?\d+\.?\d*)°", r"(-?\d+\.?\d*)°[Cc]?"]:
        m = re.search(pat, text)
        if m:
            return float(m.group(1))
    return None


def _regex_sky(text: str) -> str | None:
    for cond in ["구름많음", "흐림", "소나기", "맑음", "비", "눈", "화창"]:
        if cond in text:
            return cond
    return None


def _regex_humidity(text: str) -> int | None:
    m = re.search(r"습도\s*(\d+)\s*%", text)
    return int(m.group(1)) if m else None


def _regex_wind(text: str) -> str | None:
    dirs = "|".join(_WIND_DIR_MAP.keys())
    # 방향+속도가 같은 줄에 있는 경우
    m = re.search(rf"({dirs}풍?)\s*(\d+\.?\d*)\s*m/s", text)
    if m:
        return f"{m.group(1)} {m.group(2)}m/s"
    # 방향과 속도가 인접 줄에 있는 경우 (네이버 날씨 구조)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        line = line.strip()
        if re.search(rf"^({dirs}풍?)$", line):
            # 다음 줄에 속도가 있는지 확인
            for j in range(i + 1, min(i + 4, len(lines))):
                next_line = lines[j].strip()
                sm = re.search(r"(\d+\.?\d*)\s*m/s", next_line)
                if sm:
                    return f"{line} {sm.group(1)}m/s"
    return None


def _regex_precip(text: str) -> str | None:
    m = re.search(r"강수량\s*(\d+\.?\d*)\s*mm", text)
    return f"{m.group(1)}mm" if m else "0mm"


def _regex_visibility(text: str) -> str | None:
    m = re.search(r"시정\s*(\d+\.?\d*)\s*(km|m)", text, re.IGNORECASE)
    return f"{m.group(1)}{m.group(2)}" if m else None


# ── 스크래핑 메인 ──────────────────────────────────────────────

async def _extract_weather_data(page) -> dict | None:
    """페이지에서 날씨 데이터 추출 (3단계 fallback)."""
    try:
        temperature = await _try_get_temperature(page)
        sky_condition = await _try_get_sky(page)
        humidity, wind_raw, precip_raw, visibility_raw = await _try_get_details(page)

        # 3차 fallback: 전체 텍스트 정규식 파싱
        if temperature is None or sky_condition is None:
            page_text = await page.inner_text("body")
            if temperature is None:
                temperature = _regex_temperature(page_text)
            if sky_condition is None:
                sky_condition = _regex_sky(page_text)
            if humidity is None:
                humidity = _regex_humidity(page_text)
            if wind_raw is None:
                wind_raw = _regex_wind(page_text)
            if precip_raw is None:
                precip_raw = _regex_precip(page_text)
            if visibility_raw is None:
                visibility_raw = _regex_visibility(page_text)

        if temperature is None:
            logger.error("[Weather] 기온 추출 실패 — 수집 건너뜀")
            return None

        wind_speed, wind_direction = _parse_wind(wind_raw or "")

        # 방향이 없으면 페이지 전체 텍스트에서 별도 추출
        if wind_direction is None:
            full_text = await page.inner_text("body")
            dirs = "|".join(_WIND_DIR_MAP.keys())
            dm = re.search(rf"({dirs})풍?", full_text)
            if dm:
                raw_dir = re.sub(r"풍$", "", dm.group(1))
                wind_direction = _WIND_DIR_MAP.get(raw_dir)

        precip_mm = _parse_float(precip_raw) or 0.0
        visibility = _parse_visibility(visibility_raw) if visibility_raw else None
        sky = _map_sky_condition(sky_condition or "")

        return {
            "intersection_id": INTERSECTION_ID,
            "temperature": temperature,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "precipitation": precip_mm,
            "precipitation_type": _map_precip_type(sky, precip_mm),
            "sky_condition": sky,
            "visibility": visibility,
            "collected_at": datetime.now(),
        }
    except Exception as e:
        logger.error("[Weather] 데이터 추출 실패: %s", e)
        return None


async def scrape_weather() -> dict | None:
    """playwright (headless Chromium)으로 Naver Weather 스크래핑."""
    try:
        async with async_playwright() as p:
            # 시스템 설치 Chrome 사용 (playwright 전용 Chromium 다운로드 불필요)
            browser = await p.chromium.launch(
                headless=True,
                channel="chrome",
            )
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "Accept-Language": "ko-KR,ko;q=0.9",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            })
            try:
                await page.goto(WEATHER_URL, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)  # JS 렌더링 추가 대기
                return await _extract_weather_data(page)
            finally:
                await browser.close()
    except Exception as e:
        logger.error("[Weather] playwright 실행 실패: %s", e)
        return None


# ── 진입점 ────────────────────────────────────────────────────

async def collect_once() -> bool:
    """스크래핑 + DB 저장 1회. 성공 시 True."""
    logger.info("[Weather] 수집 시작 — %s", WEATHER_URL)
    data = await scrape_weather()
    if data is None:
        logger.warning("[Weather] 스크래핑 실패 — 다음 스케줄에 재시도")
        return False
    await asyncio.to_thread(insert_weather_log, data)
    return True


async def start_weather_loop():
    """앱 시작 시 오늘 데이터 없으면 수집 → 매일 오전 9시 반복."""
    logger.info("[Weather] 날씨 업데이트 서비스 시작 (매일 %02d:00)", TARGET_HOUR)

    # 서버 안정화 대기 — Chromium 즉시 실행이 이벤트 루프를 압박하는 것 방지
    await asyncio.sleep(120)

    already = await asyncio.to_thread(_check_today_collected)
    if not already:
        logger.info("[Weather] 오늘 날씨 데이터 없음 — 즉시 수집")
        try:
            await collect_once()
        except Exception as e:
            logger.error("[Weather] 초기 수집 실패: %s", e)
    else:
        logger.info("[Weather] 오늘 날씨 데이터 이미 존재 — 즉시 수집 건너뜀")

    while True:
        wait_sec = _seconds_until_next_9am()
        logger.info("[Weather] 다음 수집까지 %.0f초 (%.1fh)", wait_sec, wait_sec / 3600)
        await asyncio.sleep(wait_sec)
        try:
            await collect_once()
        except Exception as e:
            logger.error("[Weather] 수집 예외 — 다음날 재시도: %s", e)
