import asyncio
import queue
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from services.vision import vision_engine

logger = logging.getLogger(__name__)
router = APIRouter()

async def mjpeg_generator():
    logger.info("🟢 [Stream] 웹 브라우저가 실시간 영상에 접속했습니다!")
    frame_count = 0
    
    while True:
        try:
            # 1. 큐에서 비동기로 프레임 꺼내기
            frame_bytes = await asyncio.to_thread(vision_engine.mjpeg_queue.get, True, 1.0)
            frame_count += 1
            
            # 30프레임마다 터미널에 생존 신고 (정상 송출 확인용)
            if frame_count % 30 == 0:
                logger.info(f"🟢 [Stream] 정상 송출 중... (누적 {frame_count} 프레임 전달 완료)")
                
            # 2. 브라우저 스트리밍 규격(더블 CRLF)에 맞게 송출
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')
                   
        except queue.Empty:
            # 큐가 비어있으면 아주 잠깐 대기 후 다시 시도
            await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"🔴 [Stream] 연결 종료 또는 에러 발생: {e}")
            break

@router.get("/video_feed", tags=["Streaming"])
async def video_feed():
    """[Web Demo] 실시간 교차로 AI 분석 영상 스트리밍"""
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive" # 연결 유지 명시
        }
    )