"""
진동 신호에서 통계/주파수 피처를 추출하는 모듈
- 시간 도메인 피처: RMS, Peak, Kurtosis, Skewness, Crest Factor 등
- 주파수 도메인 피처: FFT 기반 주파수 에너지, 밴드 에너지 등
"""
import numpy as np
from scipy import stats
from scipy.fft import fft


def time_domain_features(signal: np.ndarray) -> dict:
    """시간 도메인 통계 피처 추출"""
    n = len(signal)
    if n == 0:
        return {k: 0.0 for k in [
            "mean", "std", "rms", "peak", "peak_to_peak",
            "skewness", "kurtosis", "crest_factor", "shape_factor",
            "impulse_factor", "clearance_factor"
        ]}

    mean_val = np.mean(signal)
    std_val = np.std(signal)
    rms = np.sqrt(np.mean(signal ** 2))
    peak = np.max(np.abs(signal))
    peak_to_peak = np.max(signal) - np.min(signal)
    skewness = stats.skew(signal)
    kurtosis = stats.kurtosis(signal)

    # 무차원 지표
    abs_mean = np.mean(np.abs(signal))
    crest_factor = peak / rms if rms > 0 else 0
    shape_factor = rms / abs_mean if abs_mean > 0 else 0
    impulse_factor = peak / abs_mean if abs_mean > 0 else 0
    sqrt_mean = np.mean(np.sqrt(np.abs(signal))) ** 2
    clearance_factor = peak / sqrt_mean if sqrt_mean > 0 else 0

    return {
        "mean": mean_val,
        "std": std_val,
        "rms": rms,
        "peak": peak,
        "peak_to_peak": peak_to_peak,
        "skewness": skewness,
        "kurtosis": kurtosis,
        "crest_factor": crest_factor,
        "shape_factor": shape_factor,
        "impulse_factor": impulse_factor,
        "clearance_factor": clearance_factor,
    }


def frequency_domain_features(signal: np.ndarray, sampling_rate: int) -> dict:
    """주파수 도메인 피처 추출 (FFT 기반)"""
    n = len(signal)
    if n == 0:
        return {k: 0.0 for k in [
            "freq_mean", "freq_std", "freq_peak", "freq_peak_freq",
            "band_energy_low", "band_energy_mid", "band_energy_high",
            "spectral_centroid", "spectral_spread"
        ]}

    # FFT 계산 (양의 주파수만)
    fft_vals = fft(signal)
    magnitude = np.abs(fft_vals[:n // 2])
    freqs = np.fft.fftfreq(n, d=1.0 / sampling_rate)[:n // 2]

    # 파워 스펙트럼
    power = magnitude ** 2

    freq_mean = np.mean(magnitude)
    freq_std = np.std(magnitude)
    freq_peak = np.max(magnitude)
    freq_peak_idx = np.argmax(magnitude)
    freq_peak_freq = freqs[freq_peak_idx] if freq_peak_idx < len(freqs) else 0

    # 밴드별 에너지 (저/중/고주파)
    total_power = np.sum(power) + 1e-10
    low_mask = freqs < sampling_rate / 8
    mid_mask = (freqs >= sampling_rate / 8) & (freqs < sampling_rate / 4)
    high_mask = freqs >= sampling_rate / 4

    band_energy_low = np.sum(power[low_mask]) / total_power
    band_energy_mid = np.sum(power[mid_mask]) / total_power
    band_energy_high = np.sum(power[high_mask]) / total_power

    # 스펙트럴 중심 주파수
    power_sum = np.sum(power) + 1e-10
    spectral_centroid = np.sum(freqs * power) / power_sum
    spectral_spread = np.sqrt(np.sum(((freqs - spectral_centroid) ** 2) * power) / power_sum)

    return {
        "freq_mean": freq_mean,
        "freq_std": freq_std,
        "freq_peak": freq_peak,
        "freq_peak_freq": freq_peak_freq,
        "band_energy_low": band_energy_low,
        "band_energy_mid": band_energy_mid,
        "band_energy_high": band_energy_high,
        "spectral_centroid": spectral_centroid,
        "spectral_spread": spectral_spread,
    }


def extract_features(signal_h: np.ndarray, signal_v: np.ndarray,
                     sampling_rate: int, temperature: float = None,
                     ambient_temp: float = None) -> dict:
    """
    수평/수직 진동 신호에서 전체 피처 추출

    Args:
        signal_h: 수평 진동 신호
        signal_v: 수직 진동 신호
        sampling_rate: 샘플링 주파수
        temperature: 기기 온도 (있을 경우)
        ambient_temp: 외기 온도 (있을 경우)

    Returns:
        dict: 추출된 피처 딕셔너리
    """
    features = {}

    # 수평 진동 피처
    td_h = time_domain_features(signal_h)
    fd_h = frequency_domain_features(signal_h, sampling_rate)
    for k, v in td_h.items():
        features[f"h_{k}"] = v
    for k, v in fd_h.items():
        features[f"h_{k}"] = v

    # 수직 진동 피처
    td_v = time_domain_features(signal_v)
    fd_v = frequency_domain_features(signal_v, sampling_rate)
    for k, v in td_v.items():
        features[f"v_{k}"] = v
    for k, v in fd_v.items():
        features[f"v_{k}"] = v

    # 결합 피처
    combined_rms = np.sqrt(td_h["rms"] ** 2 + td_v["rms"] ** 2)
    features["combined_rms"] = combined_rms
    features["combined_peak"] = max(td_h["peak"], td_v["peak"])
    features["combined_kurtosis"] = (td_h["kurtosis"] + td_v["kurtosis"]) / 2

    # 온도 관련 피처 (Mendeley KAIST 데이터 전용)
    if temperature is not None:
        features["temperature"] = temperature
    if ambient_temp is not None:
        features["ambient_temp"] = ambient_temp
    if temperature is not None and ambient_temp is not None:
        features["temp_diff"] = temperature - ambient_temp

    return features


def extract_features_from_segment(signal_h: np.ndarray, signal_v: np.ndarray,
                                  sampling_rate: int, segment_size: int = 2560,
                                  temperature: float = None,
                                  ambient_temp: float = None) -> list[dict]:
    """
    긴 신호를 segment_size 크기로 나누어 피처 추출

    Args:
        signal_h: 수평 진동 신호
        signal_v: 수직 진동 신호
        sampling_rate: 샘플링 주파수
        segment_size: 세그먼트 크기
        temperature: 기기 온도
        ambient_temp: 외기 온도

    Returns:
        list[dict]: 세그먼트별 피처 딕셔너리 리스트
    """
    n_segments = len(signal_h) // segment_size
    if n_segments == 0:
        return [extract_features(signal_h, signal_v, sampling_rate,
                                 temperature, ambient_temp)]

    results = []
    for i in range(n_segments):
        start = i * segment_size
        end = start + segment_size
        seg_h = signal_h[start:end]
        seg_v = signal_v[start:end]
        feat = extract_features(seg_h, seg_v, sampling_rate,
                                temperature, ambient_temp)
        results.append(feat)
    return results
