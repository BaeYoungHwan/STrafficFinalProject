import logging
import asyncio
import time
import math
from collections import deque
from core.config import settings
from utils.http_client import http_client

logger = logging.getLogger(__name__)

class TrafficAggregator:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.vehicle_count = 0

    async def add_vehicle(self, count: int = 1):
        async with self.lock:
            self.vehicle_count += count

    async def flush_and_reset(self) -> int:
        async with self.lock:
            current_count = self.vehicle_count
            self.vehicle_count = 0
        return current_count

class SensorAggregator:
    def __init__(self, max_records=120):
        self.lock = asyncio.Lock()
        self.vibration_data = deque(maxlen=max_records)
        self.temperature_data = deque(maxlen=max_records)
        self.VIBE_THRESHOLD = 5.0
        self.TEMP_THRESHOLD = 70.0

    async def add_sensor_reading(self, vibe, temp):
        # [QA 반영 2.3] 통신 노이즈에 의한 불량 데이터(None, NaN, 문자열) 방어 로직
        try:
            v_val = float(vibe)
            t_val = float(temp)
            if math.isnan(v_val) or math.isnan(t_val):
                raise ValueError("NaN value is not allowed.")
        except (ValueError, TypeError) as e:
            logger.warning(f"[Aggregator] Invalid sensor data dropped: vibe={vibe}, temp={temp} ({e})")
            return

        async with self.lock:
            self.vibration_data.append(v_val)
            self.temperature_data.append(t_val)

    async def analyze_and_flush(self):
        async with self.lock:
            if not self.vibration_data:
                return None
            
            avg_vibe = sum(self.vibration_data) / len(self.vibration_data)
            avg_temp = sum(self.temperature_data) / len(self.temperature_data)

            self.vibration_data.clear()
            self.temperature_data.clear()

        is_warning = avg_vibe > self.VIBE_THRESHOLD or avg_temp > self.TEMP_THRESHOLD
        
        return {
            "avg_vibration": round(avg_vibe, 2),
            "avg_temperature": round(avg_temp, 2),
            "is_warning": is_warning,
            "timestamp": int(time.time())
        }

traffic_aggregator = TrafficAggregator()
sensor_aggregator = SensorAggregator()

# [QA 반영 2.2] 백그라운드 태스크 고아 현상을 막기 위한 추적 리스트
active_tasks = []

async def traffic_scheduler_task():
    """[Flow A] 2분 단위 차량 혼잡도 전송 스케줄러"""
    interval = 120
    next_time = time.time() + interval
    
    while True:
        try:
            # [QA 반영 2.1] 절대 시간을 이용한 Time Drift 방지
            await asyncio.sleep(max(0, next_time - time.time()))
            next_time += interval
            
            count = await traffic_aggregator.flush_and_reset()
            if count > 0:
                payload = {"vehicle_count": count, "timestamp": int(time.time())}
                logger.info(f"[Aggregator] Flow A: Traffic count {count}. Queueing payload.")
                # TODO: utils/http_client.py 의 Retry Queue 연동
                await http_client.send_payload("/api/v1/traffic/counts", payload)
                
                
        except asyncio.CancelledError:
            logger.info("[Aggregator] Traffic scheduler task cancelled gracefully.")
            break
        except Exception as e:
            logger.error(f"[Aggregator] Traffic scheduler error: {e}")

async def sensor_scheduler_task():
    """[예지보전] 1분 단위 센서 이동평균 분석 스케줄러"""
    interval = 60
    next_time = time.time() + interval
    
    while True:
        try:
            await asyncio.sleep(max(0, next_time - time.time()))
            next_time += interval
            
            data = await sensor_aggregator.analyze_and_flush()
            if data:
                if data['is_warning']:
                    logger.warning(f"[Aggregator] PREDICTIVE MAINTENANCE WARNING! {data}")
                else:
                    logger.info(f"[Aggregator] Sensor normal. Vibe: {data['avg_vibration']}, Temp: {data['avg_temperature']}")
                    
        except asyncio.CancelledError:
            logger.info("[Aggregator] Sensor scheduler task cancelled gracefully.")
            break
        except Exception as e:
            logger.error(f"[Aggregator] Sensor scheduler error: {e}")

def start_aggregators():
    """스케줄러 시작 및 리스트 등록 (main.py lifespan startup에서 호출)"""
    t_task = asyncio.create_task(traffic_scheduler_task())
    s_task = asyncio.create_task(sensor_scheduler_task())
    active_tasks.extend([t_task, s_task])
    logger.info("[Aggregator] Background schedulers started.")

async def stop_aggregators():
    """스케줄러 안전 종료 (main.py lifespan shutdown에서 호출)"""
    logger.info("[Aggregator] Stopping background schedulers...")
    for task in active_tasks:
        task.cancel()
    
    # 태스크들이 취소 처리를 완료할 때까지 안전하게 대기
    await asyncio.gather(*active_tasks, return_exceptions=True)
    active_tasks.clear()
    logger.info("[Aggregator] All background schedulers stopped.")