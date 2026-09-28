import os
import time
import asyncio
from collections import defaultdict, deque
from typing import Tuple, Optional
import redis.asyncio as aioredis
from shared.utils.logger import setup_logger

logger = setup_logger("core_service.rate_limiter")

RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "10"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Локальное in-memory скользящее окно (Fallback при отсутствии Redis)
_memory_windows = defaultdict(deque)
_memory_lock = asyncio.Lock()

_redis_client: Optional[aioredis.Redis] = None
_redis_checked = False


async def get_redis_client() -> Optional[aioredis.Redis]:
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client

    _redis_checked = True
    try:
        client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        await client.ping()
        _redis_client = client
        logger.info("Rate Limiter подключен к Redis")
    except Exception as e:
        logger.warning(f"Redis недоступен для Rate Limiter ({e}). Используется локальный in-memory fallback.")
        _redis_client = None
    return _redis_client


async def check_rate_limit(user_id: str, limit_rpm: int = RATE_LIMIT_RPM) -> Tuple[bool, int]:
    """
    Проверяет лимит запросов пользователя через скользящее окно (60 секунд).
    Возвращает (is_limited, retry_after_seconds).
    Если is_limited == True, запрос должен быть вежливо отклонен.
    """
    now = time.time()
    window_start = now - 60.0

    client = await get_redis_client()
    if client:
        try:
            key = f"rate_limit:{user_id}"
            pipe = client.pipeline()
            # Удаляем запросы старше 60 секунд
            pipe.zremrangebyscore(key, 0, window_start)
            # Считаем оставшиеся
            pipe.zcard(key)
            # Добавляем текущий
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, 65)
            results = await pipe.execute()

            current_count = results[1]
            if current_count >= limit_rpm:
                # Находим самый старый запрос в окне для точного retry_after
                oldest = await client.zrange(key, 0, 0, withscores=True)
                retry_after = int(60 - (now - oldest[0][1])) if oldest else 30
                return True, max(1, retry_after)
            return False, 0
        except Exception as e:
            logger.warning(f"Ошибка Redis в Rate Limiter: {e}. Переключение на локальный fallback.")

    # Локальный in-memory fallback
    async with _memory_lock:
        window = _memory_windows[user_id]
        while window and window[0] < window_start:
            window.popleft()

        if len(window) >= limit_rpm:
            oldest_time = window[0]
            retry_after = int(60 - (now - oldest_time))
            return True, max(1, retry_after)

        window.append(now)
        return False, 0
