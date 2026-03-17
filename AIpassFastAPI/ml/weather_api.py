"""
기상청 API Hub 종관기상관측(ASOS) 연동 모듈

- 학습 시: KAIST 파일 날짜 → 과거 기상 데이터 매핑 (kma_sfctm2.php)
- 운영 시: 실시간 기상 데이터 조회 - 대시보드 연동 (kma_sfctm3.php)

API Hub: https://apihub.kma.go.kr
"""
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

import requests

from . import config


# ── API Hub 엔드포인트 ──
# 과거 데이터 (학습용)
ASOS_HISTORICAL_ENDPOINT = (
    "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm2.php"
)
# 실시간/최근 데이터 (대시보드용)
ASOS_REALTIME_ENDPOINT = (
    "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php"
)

DEFAULT_STN_ID = config.WEATHER_STN_ID  # "112" 인천

# 캐시 파일 (API 호출 최소화)
WEATHER_CACHE_PATH = config.PREPROCESSED_DIR / "weather_cache.json"


def _load_api_key() -> str:
    """API 키 로드 (ml/models/weather_api_key.txt)"""
    key_path = config.MODEL_DIR / "weather_api_key.txt"
    if not key_path.exists():
        raise FileNotFoundError(
            f"기상청 API 키 파일이 없습니다: {key_path}\n"
            f"  → weather_api_key.txt 파일에 API 키를 저장해주세요."
        )
    return key_path.read_text(encoding="utf-8").strip()


def _load_cache() -> dict:
    """캐시 로드"""
    if WEATHER_CACHE_PATH.exists():
        with open(WEATHER_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict):
    """캐시 저장"""
    WEATHER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(WEATHER_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _parse_api_hub_response(text: str) -> list[dict]:
    """
    기상청 API Hub 텍스트 응답 파싱

    응답 형식 (공백 구분 고정폭):
      #START7777
      YYYYMMDDHHMM STN ... WS ... TA HM ...
      #7777END

    컬럼 인덱스 (공백 split 기준):
      0: YYYYMMDDHHMM (관측시각)
      1: STN (지점번호)
      3: WS (풍속 m/s)
      11: TA (기온 °C)
      13: HM (습도 %)
    """
    results = []
    in_data = False

    for line in text.strip().splitlines():
        line = line.strip()

        if line.startswith("#START7777"):
            in_data = True
            continue
        if line.startswith("#7777END"):
            break
        if not in_data:
            continue
        # 주석/헤더 행 건너뛰기
        if line.startswith("#") or not line:
            continue

        cols = line.split()
        if len(cols) < 14:
            continue

        try:
            results.append({
                "tm": cols[0],                          # 관측시각
                "stn": cols[1],                         # 지점번호
                "wind_speed": _safe_float(cols[3]),     # WS 풍속
                "ambient_temp": _safe_float(cols[11]),  # TA 기온
                "humidity": _safe_float(cols[13]),       # HM 습도
            })
        except (IndexError, ValueError):
            continue

    return results


def fetch_hourly_weather(
    date_str: str,
    hour_str: str = "12",
    stn_id: str = DEFAULT_STN_ID,
    api_key: str = None,
    realtime: bool = False,
) -> dict | None:
    """
    특정 날짜/시간의 기상 데이터 조회

    Args:
        date_str: "20220620" 형식
        hour_str: "00"~"23" (2자리)
        stn_id: 관측소 지점번호
        api_key: 기상청 API Hub 인증키
        realtime: True면 kma_sfctm3 (실시간), False면 kma_sfctm2 (과거)

    Returns:
        {"ambient_temp": float, "wind_speed": float, "humidity": float}
        or None (실패 시)
    """
    if api_key is None:
        api_key = _load_api_key()

    endpoint = ASOS_REALTIME_ENDPOINT if realtime else ASOS_HISTORICAL_ENDPOINT

    # tm 파라미터: YYYYMMDDHHMM
    tm = f"{date_str}{hour_str.zfill(2)}00"

    params = {
        "tm": tm,
        "stn": stn_id,
        "help": "0",
        "authKey": api_key,
    }

    try:
        resp = requests.get(endpoint, params=params, timeout=15)
        resp.raise_for_status()

        records = _parse_api_hub_response(resp.text)
        if not records:
            return None

        # 첫 번째 레코드 반환
        rec = records[0]
        return {
            "ambient_temp": rec["ambient_temp"],
            "wind_speed": rec["wind_speed"],
            "humidity": rec["humidity"],
        }
    except Exception as e:
        print(f"  [WARN] 기상 API 호출 실패 ({date_str} {hour_str}시): {e}")
        return None


def fetch_weather_for_dates(
    dates: list[datetime],
    stn_id: str = DEFAULT_STN_ID,
    use_cache: bool = True,
) -> dict[str, dict]:
    """
    여러 날짜의 기상 데이터를 일괄 조회 (캐시 활용)

    Args:
        dates: datetime 리스트
        stn_id: 관측소 지점번호
        use_cache: 캐시 사용 여부

    Returns:
        {"20220620": {"ambient_temp": 24.7, "wind_speed": 2.6, "humidity": 78.0}, ...}
    """
    api_key = _load_api_key()

    # 캐시 로드
    cache = _load_cache() if use_cache else {}

    # 고유 날짜 추출 (날짜별 대표 시간 = 12시)
    unique_dates = sorted(set(d.strftime("%Y%m%d") for d in dates))
    print(f"[기상청 API Hub] 조회할 날짜: {len(unique_dates)}일")

    results = {}
    api_calls = 0

    for date_str in unique_dates:
        cache_key = f"{stn_id}_{date_str}"

        # 캐시 확인
        if cache_key in cache:
            results[date_str] = cache[cache_key]
            continue

        # API 호출 (12시 기준 일 대표값, 과거 데이터)
        weather = fetch_hourly_weather(date_str, "12", stn_id, api_key, realtime=False)
        if weather is None:
            # 12시 데이터 없으면 다른 시간 시도
            for fallback_hour in ["09", "15", "06", "18"]:
                weather = fetch_hourly_weather(
                    date_str, fallback_hour, stn_id, api_key, realtime=False
                )
                if weather is not None:
                    break

        if weather is not None:
            results[date_str] = weather
            cache[cache_key] = weather
        else:
            print(f"  [WARN] {date_str} 기상 데이터 없음 → 기본값 사용")
            default = {"ambient_temp": 15.0, "wind_speed": 3.0, "humidity": 60.0}
            results[date_str] = default
            cache[cache_key] = default

        api_calls += 1

        # API 속도 제한 방지
        if api_calls % 10 == 0:
            time.sleep(1.0)

    # 캐시 저장
    if api_calls > 0 and use_cache:
        _save_cache(cache)
        print(f"[기상청 API Hub] {api_calls}건 호출, 캐시 저장 완료")

    return results


def fetch_realtime_weather(
    stn_id: str = DEFAULT_STN_ID,
) -> dict | None:
    """
    실시간 기상 데이터 조회 (대시보드용)

    kma_sfctm3.php 사용 - 최근/현재 시각 데이터 반환

    Returns:
        {"ambient_temp": float, "wind_speed": float, "humidity": float}
        or None
    """
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    hour_str = now.strftime("%H")

    return fetch_hourly_weather(
        date_str, hour_str, stn_id, realtime=True
    )


def get_season(dt: datetime) -> int:
    """
    날짜 → 계절 변환

    Returns:
        0: 봄 (3~5월), 1: 여름 (6~8월), 2: 가을 (9~11월), 3: 겨울 (12~2월)
    """
    month = dt.month
    if month in (3, 4, 5):
        return 0
    elif month in (6, 7, 8):
        return 1
    elif month in (9, 10, 11):
        return 2
    else:
        return 3


def _safe_float(val, default=0.0) -> float:
    """안전한 float 변환 (-9는 결측치로 처리)"""
    if val is None or val == "" or val == " ":
        return default
    try:
        f = float(val)
        # 기상청 API Hub에서 -9는 결측치를 의미
        if f == -9 or f == -9.0:
            return default
        return f
    except (ValueError, TypeError):
        return default
