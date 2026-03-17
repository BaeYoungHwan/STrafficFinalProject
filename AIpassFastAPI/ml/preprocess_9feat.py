"""
9개 센서 피처 전처리 파이프라인 (v2)

기존 43개 원시신호 피처 → DB 스키마와 일치하는 9개 센서 피처로 변경
학습/운영 동일 피처: vibration_rms, temperature, temp_residual, motor_current,
                   operating_hours, ambient_temp, wind_speed, humidity, season

데이터 소스:
  - KAIST: vibration_rms(계산), temperature(원본), 기상청API(ambient_temp/wind_speed/humidity)
           → RUL 예측 학습 (단독)
  - XJTU-SY: vibration_rms(계산), 나머지 더미 → 고장모드 분류 학습
  - 사용자 더미 CSV: 9피처 직접 입력 (DB 형식)

실행: python -m ml.preprocess_9feat [옵션]
"""
import argparse
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from . import config
from .weather_api import fetch_weather_for_dates, get_season


# ────────────────────────────────────────────────────────────
# 유틸리티
# ────────────────────────────────────────────────────────────

def _calc_rms(signal: np.ndarray) -> float:
    """신호의 RMS 계산 (NaN 제거)"""
    clean = signal[~np.isnan(signal)]
    if len(clean) == 0:
        return 0.0
    return float(np.sqrt(np.mean(clean ** 2)))


def _generate_motor_current(vibration_rms: float, noise_std: float = 0.05) -> float:
    """
    모터 전류 더미 생성 (진동과 상관관계)

    정상: ~1.0A, 열화 시 진동 증가에 따라 전류도 증가
    motor_current ≈ 0.8 + 0.3 * vibration_rms + noise
    """
    base = 0.8 + 0.3 * vibration_rms
    noise = np.random.normal(0, noise_std)
    return max(0.5, base + noise)


def _calc_temp_residual(
    temperature: float,
    ambient_temp: float,
    avg_heat: float = None,
) -> float:
    """
    온도 잔차 계산

    ExpectedTemp = ambient_temp + 장비평균발열값
    temp_residual = temperature - ExpectedTemp
    """
    if avg_heat is None:
        avg_heat = config.AVG_HEAT_GENERATION
    expected_temp = ambient_temp + avg_heat
    return temperature - expected_temp


def _parse_kaist_filename(filename: str) -> datetime | None:
    """LogFile_YYYY-MM-DD-HH-MM-SS.csv → datetime"""
    match = re.search(r"LogFile_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})", filename)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d-%H-%M-%S")
    return None


# ────────────────────────────────────────────────────────────
# 1. KAIST → 9피처 전처리 (RUL 학습용 - 단독)
# ────────────────────────────────────────────────────────────

def preprocess_kaist_9feat(max_files: int = None) -> pd.DataFrame:
    """
    KAIST 원시 데이터 → 9개 피처 DataFrame

    CSV 형식: vib_h, vib_v, temp, ambient_temp (헤더 없음)
    파일 하나 = 1시간 간격 기록

    KAIST 단독 사용 이유:
    - 실제 온도 데이터 보유 (FEMTO는 더미)
    - 기상청 API로 실제 기상 매핑 가능 (FEMTO는 프랑스 실험실 데이터)
    - 진동 스케일이 FEMTO와 달라 합치면 모델 혼란 발생
      (KAIST 정상→고장: 0.70→2.10g / FEMTO: 0.71→7.59g)
    """
    print("[KAIST] 9피처 전처리 시작...")
    data_dir = config.KAIST_DIR

    csv_files = sorted(data_dir.glob("LogFile_*.csv"))
    if max_files:
        csv_files = csv_files[:max_files]

    # 파일명에서 타임스탬프 추출
    file_info = []
    for f in csv_files:
        ts = _parse_kaist_filename(f.name)
        if ts:
            file_info.append((f, ts))
    file_info.sort(key=lambda x: x[1])

    if not file_info:
        print("[KAIST] 파일을 찾을 수 없습니다.")
        return pd.DataFrame()

    # 전체 수명 (첫 ~ 마지막)
    start_time = file_info[0][1]
    end_time = file_info[-1][1]
    total_life_days = (end_time - start_time).total_seconds() / 86400

    # ── 기상청 API 호출 (날짜별 일괄) ──
    all_dates = [ts for _, ts in file_info]
    print("[KAIST] 기상청 과거 API 호출 중...")
    weather_data = fetch_weather_for_dates(
        all_dates, stn_id=config.WEATHER_STN_ID
    )

    # ── 장비 평균 발열값 산출 (1차 패스) ──
    print("[KAIST] 장비 평균 발열값 산출 중...")
    temp_diffs = []
    sample_count = min(50, len(file_info))  # 최대 50개 파일 샘플링
    sample_indices = np.linspace(0, len(file_info) - 1, sample_count, dtype=int)

    for idx in sample_indices:
        filepath, timestamp = file_info[idx]
        try:
            df = pd.read_csv(filepath, header=None,
                             names=["vib_h", "vib_v", "temp", "ambient_temp"])
            equip_temp = df["temp"].mean()
            date_key = timestamp.strftime("%Y%m%d")
            w = weather_data.get(date_key, {})
            amb = w.get("ambient_temp", df["ambient_temp"].mean())
            temp_diffs.append(equip_temp - amb)
        except Exception:
            continue

    if temp_diffs:
        avg_heat = float(np.mean(temp_diffs))
        print(f"  장비 평균 발열값: {avg_heat:.1f}°C")
    else:
        avg_heat = config.AVG_HEAT_GENERATION
        print(f"  장비 평균 발열값 (기본값): {avg_heat:.1f}°C")

    # ── 2차 패스: 9피처 추출 ──
    rows = []
    for filepath, timestamp in tqdm(file_info, desc="KAIST 9피처"):
        try:
            df = pd.read_csv(filepath, header=None,
                             names=["vib_h", "vib_v", "temp", "ambient_temp"])
        except Exception as e:
            print(f"  [WARN] {filepath.name}: {e}")
            continue

        # vibration_rms: 수평/수직 합산 RMS
        rms_h = _calc_rms(df["vib_h"].values)
        rms_v = _calc_rms(df["vib_v"].values)
        vibration_rms = float(np.sqrt(rms_h ** 2 + rms_v ** 2))

        # temperature: 파일 내 기기온도 평균
        temperature = float(df["temp"].mean())

        # 기상 데이터
        date_key = timestamp.strftime("%Y%m%d")
        w = weather_data.get(date_key, {})
        ambient_temp = w.get("ambient_temp", 15.0)
        wind_speed = w.get("wind_speed", 3.0)
        humidity = w.get("humidity", 60.0)

        # temp_residual
        temp_residual = _calc_temp_residual(temperature, ambient_temp, avg_heat)

        # motor_current (더미)
        motor_current = _generate_motor_current(vibration_rms)

        # operating_hours: 첫 파일부터 누적 시간
        elapsed_hours = (timestamp - start_time).total_seconds() / 3600
        operating_hours = float(elapsed_hours)

        # season
        season = get_season(timestamp)

        # RUL (일)
        elapsed_days = (timestamp - start_time).total_seconds() / 86400
        rul_days = max(0, total_life_days - elapsed_days)

        rows.append({
            "vibration_rms": vibration_rms,
            "temperature": temperature,
            "temp_residual": temp_residual,
            "motor_current": motor_current,
            "operating_hours": operating_hours,
            "ambient_temp": ambient_temp,
            "wind_speed": wind_speed,
            "humidity": humidity,
            "season": season,
            "rul_days": rul_days,
            "timestamp": timestamp,
            "source": "kaist",
        })

    result = pd.DataFrame(rows)
    print(f"[KAIST] {len(result)}개 샘플 생성 (총 수명: {total_life_days:.1f}일)")
    return result


# ────────────────────────────────────────────────────────────
# 2. XJTU-SY → 9피처 전처리 (고장모드 분류용)
# ────────────────────────────────────────────────────────────

def _preprocess_xjtu_bearing(
    bearing_dir: Path, max_files: int = None
) -> pd.DataFrame:
    """단일 XJTU-SY 베어링 → 9피처"""
    csv_files = sorted(bearing_dir.glob("*.csv"),
                       key=lambda f: int(f.stem) if f.stem.isdigit() else 0)
    if max_files:
        csv_files = csv_files[:max_files]

    total_files = len(csv_files)
    if total_files == 0:
        return pd.DataFrame()

    rows = []
    for idx, filepath in enumerate(
        tqdm(csv_files, desc=f"  XJTU {bearing_dir.name}", leave=False)
    ):
        try:
            df = pd.read_csv(filepath)
            signal_h = df.iloc[:, 0].values
            signal_v = df.iloc[:, 1].values
        except Exception:
            continue

        # vibration_rms
        rms_h = _calc_rms(signal_h)
        rms_v = _calc_rms(signal_v)
        vibration_rms = float(np.sqrt(rms_h ** 2 + rms_v ** 2))

        degradation_ratio = idx / total_files

        temperature = 45.0 + 20.0 * degradation_ratio + np.random.normal(0, 1.5)
        ambient_temp = 15.0 + 10.0 * np.random.random()
        temp_residual = _calc_temp_residual(
            temperature, ambient_temp, config.AVG_HEAT_GENERATION
        )
        motor_current = _generate_motor_current(vibration_rms)
        operating_hours = idx * 10.0 / 3600
        wind_speed = 2.0 + 4.0 * np.random.random()
        humidity = 40.0 + 40.0 * np.random.random()
        season = np.random.randint(0, 4)

        remaining_ratio = (total_files - idx - 1) / total_files
        rul_days = remaining_ratio * 45

        rows.append({
            "vibration_rms": vibration_rms,
            "temperature": temperature,
            "temp_residual": temp_residual,
            "motor_current": motor_current,
            "operating_hours": operating_hours,
            "ambient_temp": ambient_temp,
            "wind_speed": wind_speed,
            "humidity": humidity,
            "season": season,
            "rul_days": rul_days,
            "file_idx": idx,
        })

    return pd.DataFrame(rows)


def preprocess_xjtu_9feat(max_files_per_bearing: int = None) -> pd.DataFrame:
    """XJTU-SY 전체 → 9피처 + 고장모드 라벨"""
    print("[XJTU-SY] 9피처 전처리 시작...")
    all_dfs = []

    for condition_name, bearings in config.XJTU_FAILURE_MODES.items():
        condition_dir = config.XJTU_DIR / condition_name
        if not condition_dir.exists():
            print(f"  [WARN] {condition_dir} 없음")
            continue

        bearing_items = [(name, mode) for name, mode in bearings.items()
                         if (condition_dir / name).exists()]

        for bearing_name, raw_mode in tqdm(
            bearing_items, desc=f"XJTU {condition_name}"
        ):
            bearing_dir = condition_dir / bearing_name
            df = _preprocess_xjtu_bearing(
                bearing_dir, max_files=max_files_per_bearing
            )
            if df.empty:
                continue

            df["failure_mode_raw"] = raw_mode
            df["failure_mode"] = config.FAILURE_MODE_MAPPING.get(
                raw_mode, "bearing_wear"
            )
            df["bearing_id"] = bearing_name
            df["condition"] = condition_name
            df["source"] = "xjtu"
            all_dfs.append(df)

    if not all_dfs:
        print("[XJTU-SY] 데이터 없음")
        return pd.DataFrame()

    result = pd.concat(all_dfs, ignore_index=True)
    print(f"[XJTU-SY] {len(result)}개 샘플 생성")
    print(f"  고장모드 분포:\n{result['failure_mode'].value_counts().to_string()}")
    return result


# ────────────────────────────────────────────────────────────
# 3. 사용자 더미 CSV 로딩
# ────────────────────────────────────────────────────────────

def load_dummy_csv(csv_path: str | Path) -> pd.DataFrame:
    """
    사용자가 만든 더미 CSV 로딩 (DB 스키마 형식)

    필수 컬럼: vibration_rms, temperature, temp_residual, motor_current,
             operating_hours, ambient_temp, wind_speed, humidity, season
    선택 컬럼: rul_days, failure_mode, equipment_id, timestamp
    """
    df = pd.read_csv(csv_path)
    print(f"[더미 CSV] {csv_path} → {len(df)}행 로딩")

    # 필수 컬럼 확인
    missing = set(config.FEATURE_COLUMNS_9) - set(df.columns)
    if missing:
        raise ValueError(f"필수 컬럼 누락: {missing}")

    print(f"  컬럼: {list(df.columns)}")
    return df


# ────────────────────────────────────────────────────────────
# 통합 전처리
# ────────────────────────────────────────────────────────────

def preprocess_rul_9feat(
    max_kaist: int = None,
    dummy_csv: str = None,
) -> pd.DataFrame:
    """
    RUL 예측용 9피처 전처리 (KAIST 단독 + 선택적 더미 CSV)

    Returns:
        DataFrame: 9피처 + rul_days
    """
    dfs = []

    # KAIST (단독 - 실제 온도/기상 데이터 보유)
    df_kaist = preprocess_kaist_9feat(max_files=max_kaist)
    if not df_kaist.empty:
        dfs.append(df_kaist)

    # 더미 CSV (선택)
    if dummy_csv:
        df_dummy = load_dummy_csv(dummy_csv)
        if "rul_days" in df_dummy.columns:
            dfs.append(df_dummy)
        else:
            print("  [WARN] 더미 CSV에 rul_days 없음 → RUL 학습에서 제외")

    if not dfs:
        raise ValueError("RUL 학습 데이터를 불러올 수 없습니다.")

    # 공통 컬럼으로 통합
    feature_cols = config.FEATURE_COLUMNS_9 + ["rul_days"]
    combined_dfs = []
    for df in dfs:
        available = [c for c in feature_cols if c in df.columns]
        combined_dfs.append(df[available])

    combined = pd.concat(combined_dfs, ignore_index=True)

    # NaN/Inf 처리
    numeric_cols = combined.select_dtypes(include=[np.number]).columns
    combined[numeric_cols] = combined[numeric_cols].replace(
        [np.inf, -np.inf], np.nan
    ).fillna(0)

    # CSV 저장
    config.PREPROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(config.RUL_CSV_V2_PATH, index=False, encoding="utf-8-sig")
    print(f"\n[RUL] {len(combined)}개 샘플 → {config.RUL_CSV_V2_PATH}")

    return combined


def preprocess_fm_9feat(
    max_files_per_bearing: int = None,
    dummy_csv: str = None,
) -> pd.DataFrame:
    """
    고장모드 분류용 9피처 전처리 (XJTU-SY + 선택적 더미 CSV)

    Returns:
        DataFrame: 9피처 + failure_mode
    """
    dfs = []

    # XJTU-SY
    df_xjtu = preprocess_xjtu_9feat(max_files_per_bearing=max_files_per_bearing)
    if not df_xjtu.empty:
        dfs.append(df_xjtu)

    # 더미 CSV (선택)
    if dummy_csv:
        df_dummy = load_dummy_csv(dummy_csv)
        if "failure_mode" in df_dummy.columns:
            dfs.append(df_dummy)
        else:
            print("  [WARN] 더미 CSV에 failure_mode 없음 → 분류 학습에서 제외")

    if not dfs:
        raise ValueError("고장모드 분류 학습 데이터를 불러올 수 없습니다.")

    # 공통 컬럼
    feature_cols = config.FEATURE_COLUMNS_9 + ["failure_mode"]
    combined_dfs = []
    for df in dfs:
        available = [c for c in feature_cols if c in df.columns]
        combined_dfs.append(df[available])

    combined = pd.concat(combined_dfs, ignore_index=True)

    # NaN/Inf 처리
    numeric_cols = combined.select_dtypes(include=[np.number]).columns
    combined[numeric_cols] = combined[numeric_cols].replace(
        [np.inf, -np.inf], np.nan
    ).fillna(0)

    # CSV 저장
    config.PREPROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(config.FM_CSV_V2_PATH, index=False, encoding="utf-8-sig")
    print(f"\n[FM] {len(combined)}개 샘플 → {config.FM_CSV_V2_PATH}")

    return combined


# ────────────────────────────────────────────────────────────
# CLI 실행
# ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="9피처 전처리 파이프라인")
    parser.add_argument("--quick", action="store_true",
                        help="빠른 테스트 (데이터 일부만)")
    parser.add_argument("--rul-only", action="store_true",
                        help="RUL 전처리만")
    parser.add_argument("--fm-only", action="store_true",
                        help="고장모드 전처리만")
    parser.add_argument("--max-kaist", type=int, default=None)
    parser.add_argument("--max-xjtu", type=int, default=None)
    parser.add_argument("--dummy-csv", type=str, default=None,
                        help="추가 더미 CSV 경로")
    args = parser.parse_args()

    if args.quick:
        args.max_kaist = args.max_kaist or 30
        args.max_xjtu = args.max_xjtu or 50
        print("[Quick 모드] 데이터 일부만 사용")

    print("\n" + "█" * 60)
    print("  9피처 전처리 파이프라인")
    print("  RUL: KAIST 단독 | FM: XJTU-SY")
    print("█" * 60)

    if not args.fm_only:
        print("\n── RUL 전처리 (KAIST) ──")
        preprocess_rul_9feat(
            max_kaist=args.max_kaist,
            dummy_csv=args.dummy_csv,
        )

    if not args.rul_only:
        print("\n── 고장모드 전처리 (XJTU-SY) ──")
        preprocess_fm_9feat(
            max_files_per_bearing=args.max_xjtu,
            dummy_csv=args.dummy_csv,
        )

    print("\n전처리 완료!")


if __name__ == "__main__":
    main()
