import cv2
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from services.vision import vision_engine
from core.config import settings

router = APIRouter()

async def generate_mjpeg_stream():
    sleep_time = 1.0 / settings.STREAM_FPS_LIMIT
    
    while True:
        frame = vision_engine.latest_annotated_frame
        if frame is not None:
            # [QA 해결 3.1] CPU 바운드 이미지 인코딩을 비동기 스레드로 오프로딩
            ret, buffer = await asyncio.to_thread(
                cv2.imencode, '.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            )
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        await asyncio.sleep(sleep_time)

@router.get("/stream", tags=["Streaming"])
async def video_stream():
    return StreamingResponse(
        generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )