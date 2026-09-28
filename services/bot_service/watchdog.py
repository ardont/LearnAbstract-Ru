import asyncio
import os
from typing import Dict, Optional
import redis.asyncio as aioredis
from shared.utils.logger import setup_logger

logger = setup_logger("bot_service.watchdog")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis_client: Optional[aioredis.Redis] = None
_redis_checked = False
_active_tasks: Dict[str, asyncio.Task] = {}


async def get_redis_client() -> Optional[aioredis.Redis]:
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client

    _redis_checked = True
    try:
        client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        await client.ping()
        _redis_client = client
        logger.info("Watchdog подключен к Redis")
    except Exception as e:
        logger.warning(f"Redis недоступен для Watchdog ({e}). Используются локальные asyncio.Tasks.")
        _redis_client = None
    return _redis_client


async def _watchdog_timer(correlation_id: str, user_id: int, bot, timeout_sec: int):
    try:
        await asyncio.sleep(timeout_sec)
        # Если время истекло и таймер не был отменен:
        logger.info(f"Watchdog сработал для corr_id={correlation_id}, user_id={user_id}")
        reassurance = (
            "⏳ Генерация подробного объяснения и квиза требует чуть больше времени. "
            "Пожалуйста, подожди ещё несколько секунд, ответ уже формируется! 🧠"
        )
        try:
            await bot.send_message(chat_id=user_id, text=reassurance)
        except Exception as send_err:
            logger.warning(f"Ошибка отправки Watchdog-сообщения: {send_err}")
    except asyncio.CancelledError:
        logger.info(f"Watchdog успешно отменён для corr_id={correlation_id} (ответ доставлен вовремя)")
    finally:
        _active_tasks.pop(correlation_id, None)


async def register_watchdog(correlation_id: str, user_id: int, bot, timeout_sec: int = 45):
    """
    Регистрация Watchdog-таймера:
    - Создается локальная фоновая задача asyncio.Task
    - Дублируется в Redis: SET active_watchdog:{corr_id} {user_id} EX 45
    """
    task = asyncio.create_task(_watchdog_timer(correlation_id, user_id, bot, timeout_sec))
    _active_tasks[correlation_id] = task

    client = await get_redis_client()
    if client:
        try:
            await client.set(f"active_watchdog:{correlation_id}", str(user_id), ex=timeout_sec)
        except Exception as e:
            logger.warning(f"Ошибка записи Watchdog в Redis: {e}")


async def cancel_watchdog(correlation_id: str):
    """
    Отмена Watchdog-таймера при штатной доставке ответа:
    - Локальный asyncio.Task отменяется
    - Ключ удаляется из Redis
    """
    task = _active_tasks.pop(correlation_id, None)
    if task and not task.done():
        task.cancel()

    client = await get_redis_client()
    if client:
        try:
            await client.delete(f"active_watchdog:{correlation_id}")
        except Exception as e:
            logger.warning(f"Ошибка удаления Watchdog из Redis: {e}")
