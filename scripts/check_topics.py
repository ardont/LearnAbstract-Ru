import asyncio
import os
import sys
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


async def main():
    print("🔍 Проверка топиков Kafka...")
    try:
        from aiokafka import AIOKafkaConsumer
        consumer = AIOKafkaConsumer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            request_timeout_ms=3000
        )
        await consumer.start()
        topics = await consumer.topics()
        await consumer.stop()

        print(f"✅ Подключение к Kafka ({KAFKA_BOOTSTRAP}) успешно!")
        print("📋 Обнаруженные топики:")
        for t in sorted(topics):
            print(f"  • {t}")

        expected = ["education.events", "education.events.dlq"]
        for exp in expected:
            if exp in topics:
                print(f"  🟢 Топик {exp}: активен")
            else:
                print(f"  🟡 Топик {exp}: ещё не создан (будет создан при первом сообщении или kafka-init)")

    except Exception as e:
        print(f"⚠️ Не удалось подключиться к брокеру Kafka по адресу {KAFKA_BOOTSTRAP}: {e}")
        print("Подсказка: Запустите брокер через: docker compose up -d kafka kafka-init")


if __name__ == "__main__":
    asyncio.run(main())
