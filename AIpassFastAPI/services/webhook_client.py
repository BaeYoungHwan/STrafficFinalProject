import os
import json
import httpx
import logging
import asyncio
import aiofiles
from core.config import settings

logger = logging.getLogger(__name__)

os.makedirs("data", exist_ok=True)
FALLBACK_FILE = "data/fallback_queue.jsonl"

class WebhookClient:
    def __init__(self):
        self.target_url = getattr(settings, "WEBHOOK_URL", "http://localhost:8080/api/violations")
        self.timeout = 3.0
        self._lock = asyncio.Lock()  # 파일 I/O 정합성 보장용

    async def _save_to_dlq(self, payload: dict):
        """[DLQ] 전송 실패 시 파일 끝에 추가 (Thread-safe)"""
        async with self._lock:
            async with aiofiles.open(FALLBACK_FILE, mode='a', encoding='utf-8') as f:
                await f.write(json.dumps(payload) + '\n')
        logger.warning(f"⚠️ [DLQ] 로컬 보관 완료: {payload['eventId']}")

    async def send_violation(self, payload: dict) -> bool:
        """비동기 발송 루틴 (메인 루프 논블로킹 보장)"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.target_url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                logger.info(f"🟢 [Webhook] 발송 성공: {payload['eventId']}")
                return True
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                logger.error(f"🔴 [Webhook] 통신 실패: {e}")
                await self._save_to_dlq(payload)
                return False

    async def retry_failed_payloads(self):
        """[DLQ Retry] 성능 최적화 버전 (Read-Clear-Append 패턴)"""
        if not os.path.exists(FALLBACK_FILE):
            return
            
        # 1️⃣ [Lock 구간] 데이터 추출 후 즉시 비우기 (새 이벤트 수용 공간 마련)
        async with self._lock:
            async with aiofiles.open(FALLBACK_FILE, mode='r', encoding='utf-8') as f:
                lines = await f.readlines()
            
            if not lines:
                return
                
            # 파일 내용 즉시 비우기 (다른 프로세스가 Append 할 수 있도록 Lock 해제 전 수행)
            async with aiofiles.open(FALLBACK_FILE, mode='w', encoding='utf-8') as f:
                pass 

        logger.info(f"🔄 [DLQ] 미전송 데이터 {len(lines)}건 재전송 시작 (Lock 해제 상태)...")
        remaining_lines = []
        
        # 2️⃣ [No-Lock 구간] 메인 루프와 별개로 네트워크 통신 수행 (시스템 블로킹 방지)
        async with httpx.AsyncClient() as client:
            for line in lines:
                payload = json.loads(line.strip())
                try:
                    response = await client.post(self.target_url, json=payload, timeout=self.timeout)
                    response.raise_for_status()
                    logger.info(f"🟢 [DLQ Retry] 복구 성공: {payload['eventId']}")
                    await asyncio.sleep(0.05)  # 서버 부하 조절
                except (httpx.RequestError, httpx.HTTPStatusError):
                    remaining_lines.append(line)
        
        # 3️⃣ [Lock 구간] 여전히 실패한 건이 있다면 'Append' 모드로 복구
        if remaining_lines:
            async with self._lock:
                async with aiofiles.open(FALLBACK_FILE, mode='a', encoding='utf-8') as f:
                    # 통신 중 새롭게 추가된 데이터 뒤에 안전하게 붙임
                    await f.writelines(remaining_lines)
            logger.warning(f"🟡 [DLQ] {len(remaining_lines)}건 재전송 실패로 재보관.")

webhook_client = WebhookClient()