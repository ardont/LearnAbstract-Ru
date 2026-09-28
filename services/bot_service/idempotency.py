import hashlib
import os
import time
from typing import Optional, Dict
import redis.asyncio as aioredis
from shared.utils.logger import setup_logger

logger = setup_logger("bot_service.idempotency")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis_client: Optional[aioredis.Redis] = None
_redis_checked = False
_local_cache: Dict[str, float] = {}


async def get_redis_client() -> Optional[aioredis.Redis]:
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client

    _redis_checked = True
    try:
        client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        await client.ping()
        _redis_client = client
        logger.info("Дедупликация подключена к Redis")
    except Exception as e:
        logger.warning(f"Redis недоступен для идемпотентности ({e}). Используется локальный in-memory кэш.")
        _redis_client = None
    return _redis_client


async def is_duplicate_message(
    message_id: Optional[str],
    user_id: str,
    text: str
) -> bool:
    """
    Защита от дублей входящих сообщений (Улучшенная):
    - Если MAX присылает message_id: ключ ingress_msg:{message_id}, TTL: 3600 сек (1 час).
    - Если message_id отсутствует: ключ ingress_msg:{sha256(user_id + text + timestamp_sec)}, TTL: 60 сек.
    Возвращает True, если сообщение дубликат (уже обрабатывалось).
    """
    now = time.time()

    if message_id:
        key = f"ingress_msg:{message_id}"
        ttl = 3600
    else:
        sec = int(now)
        hash_val = hashlib.sha256(f"{user_id}_{text}_{sec}".encode("utf-8")).hexdigest()[:16]
        key = f"ingress_msg:{hash_val}"
        ttl = 60

    client = await get_redis_client()
    if client:
        try:
            # SET NX возвращает True только если ключа не было
            is_new = await client.set(key, "1", ex=ttl, nx=True)
            return not bool(is_new)
        except Exception as e:
            logger.warning(f"Ошибка Redis в идемпотентности: {e}")

    # Локальный in-memory fallback
    # Очистка устаревших ключей
    expired_keys = [k for k, exp in _local_cache.items() if exp < now]
    for k in expired_keys:
        del _local_cache[k]

    if key in _local_cache:
        return True

    _local_cache[key] = now + ttl
    return False
