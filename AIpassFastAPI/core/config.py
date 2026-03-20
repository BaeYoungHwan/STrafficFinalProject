from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "AI-Pass FastAPI Core"
    VERSION: str = "1.0.0"
    
    # Backend Comm & Queue Settings
    BACKEND_URL: str = "http://localhost:9000"  # Spring Boot 실제 포트
    QUEUE_MAXSIZE: int = 1000  # OOM 방지용 메모리 큐 최대 크기
    
    # Streaming Settings
    STREAM_MAX_WIDTH: int = 640
    STREAM_MAX_HEIGHT: int = 480
    STREAM_FPS_LIMIT: int = 25
    
    # OCR Concurrency
    OCR_MAX_CONCURRENT_TASKS: int = 3 # Semaphore 동시성 제한

    # [수정 완료] Pydantic v2 권장 방식
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # [V2 추가] Vision Engine Settings
    YOLO_MODEL: str = "yolo26n.pt"  # V2 요구사항 모델
    INFERENCE_IMGSZ: int = 640
    CONF_THRESHOLD: float = 0.3
    TARGET_CLASSES: list = [2, 3, 5, 7] # 승용차, 이륜차, 버스, 화물차
    CAMERA_ID: str = "CAM_INTERSECTION_MAIN"
    SPEED_SCALE_FACTOR: float = 1.0  # 호모그래피 스케일 보정 (.env에서 덮어쓰기 가능)
    
    # [V2 추가] 동영상 소스 URL (.env의 VIDEO_SOURCE_URL로 덮어쓰기 가능)
    # 지원 형식: 로컬 파일 (C:/path/video.mp4), RTSP (rtsp://...), HTTP (http://...)
    VIDEO_SOURCE_URL: str = "rtsp://localhost:8554/korea_intersection_01"

    # [Flow C] Emergency Classes
    EMERGENCY_CLASSES: list = [9, 10]  # 구급차, 소방차 등 (커스텀 모델 기준)
    
    
settings = Settings()