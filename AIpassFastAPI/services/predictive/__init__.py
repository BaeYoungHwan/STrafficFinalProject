"""AIpass 예지보전 시뮬레이터

12대 장비에 대해 15초 주기로 센서값을 생성하고
Spring Boot /api/sensor/ingest 로 배치 전송한다.
ML 판정은 /api/v1/predict 엔드포인트에서 별도 수행.
"""
