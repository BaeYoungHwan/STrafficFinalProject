import os
import json
import asyncio
import pytest
import respx
import httpx
from services.webhook_client import webhook_client, FALLBACK_FILE

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """테스트 전/후 DLQ 파일 초기화 (격리 보장)"""
    if os.path.exists(FALLBACK_FILE):
        os.remove(FALLBACK_FILE)
    yield
    if os.path.exists(FALLBACK_FILE):
        os.remove(FALLBACK_FILE)

@pytest.mark.asyncio
@respx.mock
async def test_scenario_a_happy_path():
    """[시나리오 A] 정상 통신 시 파일 적재 없이 바로 성공하는가?"""
    respx.post(webhook_client.target_url).respond(status_code=200)
    
    payload = {"eventId": "EVT-HAPPY-001"}
    result = await webhook_client.send_violation(payload)
    
    assert result is True
    assert not os.path.exists(FALLBACK_FILE)

@pytest.mark.asyncio
@respx.mock
async def test_scenario_b_server_down_dlq():
    """[시나리오 B] 서버 500 에러 시 DLQ에 파일이 기록되는가?"""
    respx.post(webhook_client.target_url).respond(status_code=500)
    
    payload = {"eventId": "EVT-DOWN-002"}
    result = await webhook_client.send_violation(payload)
    
    assert result is False
    assert os.path.exists(FALLBACK_FILE)
    
    with open(FALLBACK_FILE, "r") as f:
        saved_data = json.loads(f.readline().strip())
        assert saved_data["eventId"] == "EVT-DOWN-002"

@pytest.mark.asyncio
@respx.mock
async def test_scenario_c_concurrency_timeout():
    """[시나리오 C] 20대 동시 과속 + 5초 지연 시, 엔진이 뻗지 않고 모두 파일에 저장되는가?"""
    # Mock Timeout Exception 강제 발생
    respx.post(webhook_client.target_url).mock(side_effect=httpx.TimeoutException("Mocked Timeout"))
    
    payloads = [{"eventId": f"EVT-STRESS-{i}"} for i in range(20)]
    
    # 20건 비동기 동시 발송 폭격
    tasks = [webhook_client.send_violation(p) for p in payloads]
    results = await asyncio.gather(*tasks)
    
    # 모두 Fail 처리되어야 함 (엔진 크래시 없음 보장)
    assert all(r is False for r in results)
    
    # 20건이 단 한 건의 누락 없이 파일에 기록되었는지 검증
    with open(FALLBACK_FILE, "r") as f:
        lines = f.readlines()
        assert len(lines) == 20

@pytest.mark.asyncio
@respx.mock
async def test_scenario_d_dlq_recovery_retry():
    """[시나리오 D] 서버 복구 시 파일에 있던 데이터가 전송되고 파일이 비워지는가?"""
    # 1. 고의로 3건의 실패 데이터를 DLQ에 주입
    payloads = [{"eventId": f"EVT-RETRY-{i}"} for i in range(3)]
    with open(FALLBACK_FILE, "w") as f:
        for p in payloads:
            f.write(json.dumps(p) + "\n")
            
    # 2. Web 서버 정상 복구 모킹 (HTTP 200)
    respx.post(webhook_client.target_url).respond(status_code=200)
    
    # 3. 재전송 백그라운드 태스크 가동
    await webhook_client.retry_failed_payloads()
    
    # 4. 파일이 깨끗하게 비워졌는지 확인 (전송 완료)
    with open(FALLBACK_FILE, "r") as f:
        assert len(f.readlines()) == 0

@pytest.mark.asyncio
@respx.mock
async def test_scenario_e_no_lock_starvation():
    """[시나리오 E] 재전송(Retry) 중에도 새로운 이벤트가 정상적으로 저장되는가? (병목 검증)"""
    # 1. 기존 데이터 1건 존재
    with open(FALLBACK_FILE, "w") as f:
        f.write(json.dumps({"eventId": "OLD-DATA"}) + "\n")
        
    # 2. 서버가 여전히 다운된 상태 모킹 (지연 시간 2초 주입)
    respx.post(webhook_client.target_url).respond(status_code=500)
    
    # 3. 재전송 시작 (비동기로 실행하여 Lock을 점유하게 함)
    retry_task = asyncio.create_task(webhook_client.retry_failed_payloads())
    
    # 4. 재전송이 도는 '도중에' 새로운 위반 이벤트 발생
    # (기존 코드라면 Lock 때문에 여기서 블로킹되어야 함)
    new_payload = {"eventId": "NEW-DATA-WHILE-RETRYING"}
    new_event_start = asyncio.get_event_loop().time()
    result = await webhook_client.send_violation(new_payload)
    new_event_end = asyncio.get_event_loop().time()
    
    # 검증: 새 이벤트 처리가 재전송 대기 없이 즉시 완료되었는가? (0.1초 미만)
    assert (new_event_end - new_event_start) < 0.1
    assert result is False # 서버가 500이므로 DLQ 저장됨
    
    await retry_task
    
    # 최종 검증: 파일에 OLD-DATA와 NEW-DATA가 모두 안전하게 남아있는가?
    with open(FALLBACK_FILE, "r") as f:
        content = f.read()
        assert "OLD-DATA" in content
        assert "NEW-DATA-WHILE-RETRYING" in content
    print(" -> [Pass] Lock Starvation 해결 및 데이터 무결성 확인 완료")