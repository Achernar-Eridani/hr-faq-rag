from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Optional

import redis


@lru_cache(maxsize=1)
def get_redis() -> Optional[redis.Redis]:
    url = os.getenv("REDIS_URL", "")
    if not url:
        return None
    # 0.2秒没反应直接放弃
    try:
        r = redis.Redis.from_url(url, decode_responses=True, socket_timeout=0.2)
        r.ping()
        return r
    except Exception:
        return None


def cache_get(key: str) -> Optional[dict]:
    r = get_redis()
    if not r:
        return None
    try:
        val = r.get(key)
        # 取出来string还原成json
        return json.loads(val) if val else None
    except Exception:
        return None


def cache_set(key: str, value: dict, ttl: int = 3600) -> None:
    r = get_redis()
    if not r:
        return
    try:
        # ensure_ascii=False 保证存进 Redis 的是中文，而不是 \uXXXX 乱码，方便调试查看
        r.setex(key, ttl, json.dumps(value, ensure_ascii=False))
    except Exception:
        return
