"""
3개 데이터셋 로딩 및 전처리 모듈
1. Mendeley KAIST Ball Bearing → RUL 학습 (메인) + 온도 보정
2. FEMTO / PRONOSTIA (IEEE PHM 2012) → RUL 패턴 학습 보조
3. XJTU-SY Bearing Dataset → 고장모드 분류 학습
"""
import os
import re
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from tqdm import tqdm

from . import config
from .feature_engineering import extract_features, extract_features_from_segment


# ────────────────────────────────────────────────────────────
# 1. Mendeley KAIST Ball Bearing
# ────────────────────────────────────────────────────────────

def _parse_kaist_filename(filename: str) -> datetime | None:
    """LogFile_YYYY-MM-DD-HH-MM-SS.csv → datetime"""
    match = re.search(r"LogFile_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})", filename)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d-%H-%M-%S")
    return None


def load_kaist_dataset(max_files: int = None) -> pd.DataFrame:
    """
    Mendeley KAIST Ball Bearing 데이터 로딩

    CSV 형식 (헤더 없음): vibration_h, vibration_v, temperature, ambient_temp
    파일 하나 = 1시간 간격 기록, 내부에 여러 샘플

    Returns:
        DataFrame: 파일별 통계 피처 + RUL(일)
    """
    print("[KAIST] 데이터 로딩 중...")
    data_dir = config.KAIST_DIR

    csv_files = sorted(data_dir.glob("LogFile_*.csv"))
    if max_files:
        csv_files = csv_files[:max_files]

    # 파일명에서 타임스탬프 추출 후 정렬
    file_info = []
    for f in csv_files:
        ts = _parse_kaist_filename(f.name)
        if ts:
            file_info.append((f, ts))
    file_info.sort(key=lambda x: x[1])

    if not file_info:
        print("[KAIST] 파일을 찾을 수 없습니다.")
        return pd.DataFrame()

    # 전체 수명 (첫 파일 ~ 마지막 파일)
    start_time = file_info[0][1]
    end_time = file_info[-1][1]
    total_life_days = (end_time - start_time).total_seconds() / 86400

    rows = []
    for filepath, timestamp in tqdm(file_info, desc="KAIST 피처 추출"):
        try:
            df = pd.read_csv(filepath, header=None,
                             names=["vib_h", "vib_v", "temp", "ambient_temp"])
        except Exception as e:
            print(f"  [WARN] {filepath.name} 읽기 실패: {e}")
            continue

        signal_h = df["vib_h"].values
        signal_v = df["vib_v"].values
        temperature = df["temp"].mean()
        ambient_temp = df["ambient_temp"].mean()

        # 파일 전체에서 피처 추출
        feat = extract_features(
            signal_h, signal_v,
            config.KAIST_SAMPLING_RATE,
            temperature=temperature,
            ambient_temp=ambient_temp,
        )

        # RUL 계산 (일 단위)
        elapsed_days = (timestamp - start_time).total_seconds() / 86400
        rul_days = max(0, total_life_days - elapsed_days)

        feat["rul_days"] = rul_days
        feat["timestamp"] = timestamp
        feat["source"] = "kaist"
        rows.append(feat)

    result = pd.DataFrame(rows)
    print(f"[KAIST] {len(result)}개 샘플 로딩 완료 (총 수명: {total_life_days:.1f}일)")
    return result


# ────────────────────────────────────────────────────────────
# 2. FEMTO / PRONOSTIA (IEEE PHM 2012)
# ────────────────────────────────────────────────────────────

def _load_femto_bearing(bearing_dir: Path, max_files: int = None) -> pd.DataFrame:
    """단일 FEMTO 베어링 디렉토리 로딩"""
    acc_files = sorted(bearing_dir.glob("acc_*.csv"))
    if max_files:
        acc_files = acc_files[:max_files]

    total_files = len(acc_files)
    if total_files == 0:
        return pd.DataFrame()

    bearing_name = bearing_dir.name
    rows = []
    for idx, filepath in enumerate(tqdm(acc_files, desc=f"  FEMTO {bearing_name}", leave=False)):
        try:
            # FEMTO 형식: hour, min, sec, microsec, horiz_accel, vert_accel
            df = pd.read_csv(filepath, header=None,
                             names=["hour", "min", "sec", "microsec",
                                    "accel_h", "accel_v"])
        except Exception:
            continue

        signal_h = df["accel_h"].values
        signal_v = df["accel_v"].values

        feat = extract_features(signal_h, signal_v, config.FEMTO_SAMPLING_RATE)

        # RUL 비율 기반 계산 (마지막 파일 = RUL 0)
        # FEMTO는 가속 수명 시험이므로 일 단위 변환 필요
        # 실험 시간 기준으로 비율 계산 후 프로젝트 스케일에 맞게 변환
        remaining_ratio = (total_files - idx - 1) / total_files
        # 일반 베어링 수명 ~30-60일로 스케일링
        rul_days = remaining_ratio * 45  # 45일 기준

        feat["rul_days"] = rul_days
        feat["file_idx"] = idx
        rows.append(feat)

    return pd.DataFrame(rows)


def load_femto_dataset(max_files_per_bearing: int = None) -> pd.DataFrame:
    """
    FEMTO/PRONOSTIA 데이터 로딩 (Learning_set + Full_Test_Set)

    Returns:
        DataFrame: 파일별 피처 + RUL(일)
    """
    print("[FEMTO] 데이터 로딩 중...")
    all_dfs = []

    for subset in ["Learning_set", "Full_Test_Set"]:
        subset_dir = config.FEMTO_DIR / subset
        if not subset_dir.exists():
            continue

        bearing_dirs = [d for d in sorted(subset_dir.iterdir())
                        if d.is_dir() and d.name.startswith("Bearing")]
        for bearing_dir in tqdm(bearing_dirs, desc=f"FEMTO {subset}", leave=True):
            df = _load_femto_bearing(bearing_dir, max_files=max_files_per_bearing)
            if not df.empty:
                df["bearing_id"] = bearing_dir.name
                df["subset"] = subset
                df["source"] = "femto"
                all_dfs.append(df)

    if not all_dfs:
        print("[FEMTO] 데이터를 찾을 수 없습니다.")
        return pd.DataFrame()

    result = pd.concat(all_dfs, ignore_index=True)
    print(f"[FEMTO] {len(result)}개 샘플 로딩 완료")
    return result


# ────────────────────────────────────────────────────────────
# 3. XJTU-SY Bearing Dataset
# ────────────────────────────────────────────────────────────

def _load_xjtu_bearing(bearing_dir: Path, max_files: int = None) -> pd.DataFrame:
    """단일 XJTU-SY 베어링 디렉토리 로딩"""
    csv_files = sorted(bearing_dir.glob("*.csv"),
                       key=lambda f: int(f.stem) if f.stem.isdigit() else 0)
    if max_files:
        csv_files = csv_files[:max_files]

    total_files = len(csv_files)
    if total_files == 0:
        return pd.DataFrame()

    bearing_name = bearing_dir.name
    rows = []
    for idx, filepath in enumerate(tqdm(csv_files, desc=f"  XJTU {bearing_name}", leave=False)):
        try:
            df = pd.read_csv(filepath)
            col_h = df.columns[0]  # Horizontal_vibration_signals
            col_v = df.columns[1]  # Vertical_vibration_signals
            signal_h = df[col_h].values
            signal_v = df[col_v].values
        except Exception:
            continue

        # 긴 신호는 세그먼트로 나누어 평균 피처 산출
        segments = extract_features_from_segment(
            signal_h, signal_v, config.XJTU_SAMPLING_RATE
        )
        # 세그먼트 피처 평균
        feat = {}
        for key in segments[0]:
            feat[key] = np.mean([s[key] for s in segments])

        # RUL 비율 기반
        remaining_ratio = (total_files - idx - 1) / total_files
        rul_days = remaining_ratio * 45

        feat["rul_days"] = rul_days
        feat["file_idx"] = idx
        rows.append(feat)

    return pd.DataFrame(rows)


def load_xjtu_dataset(max_files_per_bearing: int = None) -> pd.DataFrame:
    """
    XJTU-SY Bearing 데이터 로딩 (고장모드 라벨 포함)

    Returns:
        DataFrame: 피처 + failure_mode 라벨 + RUL
    """
    print("[XJTU-SY] 데이터 로딩 중...")
    all_dfs = []

    for condition_name, bearings in config.XJTU_FAILURE_MODES.items():
        condition_dir = config.XJTU_DIR / condition_name
        if not condition_dir.exists():
            print(f"  [WARN] {condition_dir} 없음, 건너뜀")
            continue

        bearing_items = [(name, mode) for name, mode in bearings.items()
                         if (condition_dir / name).exists()]
        for bearing_name, raw_mode in tqdm(bearing_items, desc=f"XJTU {condition_name}", leave=True):
            bearing_dir = condition_dir / bearing_name
            df = _load_xjtu_bearing(bearing_dir, max_files=max_files_per_bearing)
            if df.empty:
                continue

            # 고장모드 라벨
            df["failure_mode_raw"] = raw_mode
            df["failure_mode"] = config.FAILURE_MODE_MAPPING.get(
                raw_mode, "bearing_wear"
            )
            df["bearing_id"] = bearing_name
            df["condition"] = condition_name
            df["source"] = "xjtu"
            all_dfs.append(df)

    if not all_dfs:
        print("[XJTU-SY] 데이터를 찾을 수 없습니다.")
        return pd.DataFrame()

    result = pd.concat(all_dfs, ignore_index=True)
    print(f"[XJTU-SY] {len(result)}개 샘플 로딩 완료")
    print(f"  고장모드 분포:\n{result['failure_mode'].value_counts().to_string()}")
    return result


# ────────────────────────────────────────────────────────────
# 통합 로딩
# ────────────────────────────────────────────────────────────

def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """피처 컬럼만 추출 (메타 컬럼 제외)"""
    exclude = {
        "rul_days", "timestamp", "source", "bearing_id", "subset",
        "file_idx", "failure_mode", "failure_mode_raw", "condition",
    }
    return [c for c in df.columns if c not in exclude]


def load_rul_dataset(max_kaist: int = None,
                     max_femto_per_bearing: int = None) -> pd.DataFrame:
    """
    RUL 예측용 통합 데이터셋 로딩 (KAIST + FEMTO)

    Returns:
        DataFrame: 통합 피처 + rul_days
    """
    df_kaist = load_kaist_dataset(max_files=max_kaist)
    df_femto = load_femto_dataset(max_files_per_bearing=max_femto_per_bearing)

    # 공통 피처 컬럼만 사용
    if df_kaist.empty and df_femto.empty:
        raise ValueError("RUL 학습 데이터를 불러올 수 없습니다.")

    dfs = [d for d in [df_kaist, df_femto] if not d.empty]
    # 공통 컬럼 찾기
    common_cols = set(dfs[0].columns)
    for d in dfs[1:]:
        common_cols &= set(d.columns)

    combined = pd.concat([d[list(common_cols)] for d in dfs], ignore_index=True)
    print(f"\n[통합 RUL] 총 {len(combined)}개 샘플")
    return combined


def load_failure_mode_dataset(max_files_per_bearing: int = None) -> pd.DataFrame:
    """
    고장모드 분류용 데이터셋 로딩 (XJTU-SY)

    Returns:
        DataFrame: 피처 + failure_mode 라벨
    """
    return load_xjtu_dataset(max_files_per_bearing=max_files_per_bearing)
