from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "AI-Pass FastAPI Core"
    VERSION: str = "1.0.0"
    
    # Backend Comm & Queue Settings
    BACKEND_URL: str = "http://localhost:8080" # 백엔드 서버 주소
    QUEUE_MAXSIZE: int = 1000  # OOM 방지용 메모리 큐 최대 크기
    
    # Streaming Settings
    STREAM_MAX_WIDTH: int = 640
    STREAM_MAX_HEIGHT: int = 480
    STREAM_FPS_LIMIT: int = 10
    
    # OCR Concurrency
    OCR_MAX_CONCURRENT_TASKS: int = 3 # Semaphore 동시성 제한

    # [수정 완료] Pydantic v2 권장 방식
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()