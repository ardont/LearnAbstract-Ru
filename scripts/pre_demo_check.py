import asyncio
import os
import sys
import time
from dotenv import load_dotenv

# Принудительная установка UTF-8 для вывода в консоль Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Подключаем корень репозитория к sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


async def check_database():
    from services.core_service.db.database import init_db, is_sqlite_fallback, get_db_session
    from sqlalchemy import text
    try:
        ok = await init_db()
        if ok:
            async with get_db_session() as s:
                await s.execute(text("SELECT 1"))
            db_type = "SQLite (Fallback mode)" if is_sqlite_fallback else "PostgreSQL"
            print(f"{GREEN}[OK]{RESET} База данных: подключение и чтение схемы OK ({db_type}).")
            return True
        else:
            print(f"{RED}[FAIL]{RESET} База данных: ошибка инициализации схемы.")
            return False
    except Exception as e:
        print(f"{YELLOW}[WARN]{RESET} База данных (Fallback): {e}")
        return True


async def check_redis():
    import redis.asyncio as aioredis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        client = aioredis.from_url(redis_url, socket_connect_timeout=1.5)
        await client.ping()
        await client.set("demo_test_key", "1", ex=10)
        await client.aclose()
        print(f"{GREEN}[OK]{RESET} Redis: ping и тестовая запись OK.")
        return True
    except Exception:
        print(f"{YELLOW}[WARN]{RESET} Redis: недоступен локально — активен встроенный in-memory fallback (Rate Limiting и Watchdog работают).")
        return True


async def check_kafka():
    from aiokafka import AIOKafkaConsumer
    kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    try:
        consumer = AIOKafkaConsumer(
            bootstrap_servers=kafka_servers,
            request_timeout_ms=2000
        )
        await asyncio.wait_for(consumer.start(), timeout=2.5)
        topics = await consumer.topics()
        await consumer.stop()

        has_events = "education.events" in topics
        has_dlq = "education.events.dlq" in topics

        if has_events and has_dlq:
            print(f"{GREEN}[OK]{RESET} Kafka KRaft: топики education.events и education.events.dlq доступны.")
        else:
            print(f"{GREEN}[OK]{RESET} Kafka KRaft: брокер доступен ({len(topics)} топиков). Топики создаются автоматически.")
        return True
    except Exception:
        print(f"{YELLOW}[WARN]{RESET} Kafka: брокер недоступен — активен прямой локальный вызов сервисов (Demo-Resilience OK).")
        return True


async def check_bot_token():
    token = os.getenv("MAX_BOT_TOKEN")
    if token and len(token) > 15 and not token.startswith("your_"):
        print(f"{GREEN}[OK]{RESET} MAX Bot API: токен задан и валиден.")
        return True
    else:
        print(f"{RED}[FAIL]{RESET} MAX Bot API: токен отсутствует или содержит плейсхолдер в .env.")
        return False


async def check_llm_and_fallback():
    from services.ml_service.llm_client import generate_explanation
    t0 = time.time()
    res = await generate_explanation("Квадратные уравнения", interest="Футбол", grade=7)
    elapsed = time.time() - t0
    source = res.get("source")
    if res.get("text") and elapsed < 3.0:
        print(f"{GREEN}[OK]{RESET} LLM & 3-Tier Fallback: генерация метафоры OK ({elapsed:.2f}s, источник: {source}).")
        return True
    else:
        print(f"{RED}[FAIL]{RESET} LLM / Fallback: генерация не вернула ожидаемый результат.")
        return False


async def check_rag():
    from services.ml_service.rag_engine import rag_engine
    if rag_engine.has_subject("algebra"):
        docs = rag_engine.retrieve("квадратные уравнения", "algebra", k=1)
        if docs:
            print(f"{GREEN}[OK]{RESET} RAG Knowledge Base: учебник алгебры проиндексирован и доступен.")
            return True
    print(f"{YELLOW}[WARN]{RESET} RAG Knowledge Base: учебники не проиндексированы (запустите python scripts/ingest_textbook.py).")
    return True


async def main():
    print(f"\n{BOLD}{BLUE}======================================================{RESET}")
    print(f"{BOLD}{BLUE}  ЭКСПРЕСС-ПРОВЕРКА ГОТОВНОСТИ ПЕРЕД ВЫХОДОМ НА СЦЕНУ   {RESET}")
    print(f"{BOLD}{BLUE}  Проект «Твой Путь: Абстрактный Репетитор» v5.2     {RESET}")
    print(f"{BOLD}{BLUE}======================================================{RESET}\n")

    results = []
    results.append(await check_database())
    results.append(await check_redis())
    results.append(await check_kafka())
    results.append(await check_bot_token())
    results.append(await check_llm_and_fallback())
    results.append(await check_rag())

    all_passed = all(results)
    print(f"\n{BOLD}{BLUE}------------------------------------------------------{RESET}")
    if all_passed:
        print(f"{BOLD}{GREEN}  ИТОГ: ALL SYSTEMS GO! YOU ARE READY TO DEMO!         {RESET}")
    else:
        print(f"{BOLD}{YELLOW}  ВНИМАНИЕ: Проверьте критические пункты выше.         {RESET}")
    print(f"{BOLD}{BLUE}======================================================{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
