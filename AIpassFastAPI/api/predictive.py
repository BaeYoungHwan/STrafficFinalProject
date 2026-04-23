"""
예지보전 판정 API 라우터

POST /api/v1/predict   — 단일 또는 배치 센서 데이터 판정
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.predictive.judge import judge
from services.predictive.scheduler import reset_equipment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["Predictive"])


# ─────────────────────────────────────────────────────────────
# 스키마
# ─────────────────────────────────────────────────────────────

class SensorInput(BaseModel):
    equipment_id: int = Field(..., description="장비 ID")
    vibration: float = Field(..., description="진동 RMS (g)")
    temperature: float = Field(..., description="설비 온도 (°C)")
    motor_current: float = Field(..., description="모터 전류 (A)")


class JudgeResult(BaseModel):
    equipment_id: int
    is_anomaly: bool
    anomaly_score: float
    fault_type: str
    risk_level: str


class PredictRequest(BaseModel):
    items: List[SensorInput] = Field(..., min_length=1, description="판정 요청 목록 (1개 이상)")


class PredictResponse(BaseModel):
    success: bool
    data: List[JudgeResult]
    message: str


# ─────────────────────────────────────────────────────────────
# 엔드포인트
# ─────────────────────────────────────────────────────────────

@router.post("", response_model=PredictResponse, summary="예지보전 판정 (배치 지원)")
async def predict(body: PredictRequest) -> PredictResponse:
    """
    센서 데이터를 받아 이상탐지·고장분류·위험등급을 반환한다.

    단일 요청도 items 배열로 감싸서 보내면 된다.
    기존 내부 judge() 함수는 그대로 유지되며 이 엔드포인트가 래퍼 역할만 한다.
    """
    results: List[JudgeResult] = []

    for item in body.items:
        try:
            is_anomaly, anomaly_score, fault_type, risk_level = judge(
                vibration=item.vibration,
                temperature=item.temperature,
                motor_current=item.motor_current,
            )
            results.append(
                JudgeResult(
                    equipment_id=item.equipment_id,
                    is_anomaly=is_anomaly,
                    anomaly_score=round(anomaly_score, 4),
                    fault_type=fault_type,
                    risk_level=risk_level,
                )
            )
        except Exception as e:
            logger.error("[Predict] equipment_id=%d 판정 실패: %s", item.equipment_id, e)
            raise

    return PredictResponse(
        success=True,
        data=results,
        message=f"{len(results)}건 판정 완료",
    )


@router.post("/simulator/reset/{equipment_id}", summary="시뮬레이터 장비 상태 리셋")
async def reset_simulator_equipment(equipment_id: int) -> dict:
    if not (1 <= equipment_id <= 12):
        return {"success": False, "message": f"유효하지 않은 equipment_id: {equipment_id}"}

    if reset_equipment(equipment_id):
        logger.info("[Predict] 시뮬레이터 장비 %d 리셋 완료", equipment_id)
        return {"success": True, "message": f"장비 {equipment_id} 리셋 완료"}
    else:
        return {"success": False, "message": "시뮬레이터 미실행 또는 장비 없음"}
