from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "AI-Pass FastAPI Core"
    VERSION: str = "1.0.0"
    
    # Backend Comm & Queue Settings
    BACKEND_URL: str = "http://localhost:9000"  # Spring Boot 실제 포트
    FASTAPI_URL: str = "http://localhost:8000"  # FastAPI 자기 자신 URL (이미지 서빙용, .env로 덮어쓰기 가능)
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
    INFERENCE_IMGSZ: int = 416
    CONF_THRESHOLD: float = 0.4
    TARGET_CLASSES: list = [2, 3, 5, 7] # 승용차, 이륜차, 버스, 화물차
    CAMERA_ID: str = "CAM_INTERSECTION_MAIN"
    SPEED_SCALE_FACTOR: float = 1.0  # 호모그래피 스케일 보정 (.env에서 덮어쓰기 가능)
    
    # [V2 추가] 동영상 소스 URL (.env의 VIDEO_SOURCE_URL로 덮어쓰기 가능)
    # 지원 형식: 로컬 파일 (C:/path/video.mp4), RTSP (rtsp://...), HTTP (http://...)
    VIDEO_SOURCE_URL: str = ""

    # ITS Open API — CCTV 스트림 URL 갱신용
    CCTV_INFO_URL: str = ""  # .env의 CCTV_info_URL 값으로 덮어쓰기

    # DB 직접 연결 (CCTV URL 갱신용)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "aipass"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "1234"

    # [Flow C] Emergency Classes
    EMERGENCY_CLASSES: list = [9, 10]  # 구급차, 소방차 등 (커스텀 모델 기준)

    # Speed Detection Constants
    SPEED_LIMIT_KMH: float = 70.0
    MAX_PLAUSIBLE_SPEED_KMH: float = 100.0
    EMA_ALPHA: float = 0.3
    CONSECUTIVE_OVER_THRESHOLD: int = 5

    # 기능 모드 분기
    FEATURE_MODE: str = "SPEED"            # "SPEED" | "LINE_CROSSING"

    # 실선 좌표 (640x480 기준 픽셀, LINE_CROSSING 모드에서만 사용)
    LINE_X1: int = 320
    LINE_Y1: int = 0
    LINE_X2: int = 320
    LINE_Y2: int = 480
    LINE_CROSSING_COOLDOWN: float = 3.0    # 동일 차량 재단속 방지 쿨다운(초)
    CAMERA_LOCATION_LINE: str = "강화대교_실선_01"


settings = Settings()