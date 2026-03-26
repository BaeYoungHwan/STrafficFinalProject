"""
순환 임포트 방지를 위해 위반 이벤트 캐시를 독립 모듈로 분리.
webhook_client → (push) ← stream.py 양쪽이 이 모듈만 참조한다.
"""
from collections import deque

_cache: deque = deque(maxlen=100)


def push(payload: dict) -> None:
    _cache.appendleft(payload)


def get_recent(limit: int = 20) -> list:
    return list(_cache)[:limit]


def total() -> int:
    return len(_cache)
