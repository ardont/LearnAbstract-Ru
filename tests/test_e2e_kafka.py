import pytest
import os
import sys
import asyncio
import json
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


async def is_kafka_available() -> bool:
    try:
        p = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP, request_timeout_ms=1000)
        await p.start()
        await p.stop()
        return True
    except Exception:
        return False


@pytest.mark.asyncio
async def test_full_kafka_e2e_pipeline():
    """Сквозной тест через топик Kafka (пропускается, если брокер оффлайн в среде тестирования)."""
    if not await is_kafka_available():
        pytest.skip("Kafka брокер не запущен — пропускаем прямой сетевой тест.")

    corr_id = f"test-e2e-{uuid.uuid4().hex[:6]}"
    topic = "education.events"

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=f"test_group_{uuid.uuid4().hex[:6]}",
        auto_offset_reset="earliest",
        value_deserializer=lambda x: json.loads(x.decode("utf-8"))
    )

    await producer.start()
    await consumer.start()
    await asyncio.sleep(1.0)

    test_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "bot.command.received",
        "correlation_id": corr_id,
        "producer": "test",
        "payload": {
            "max_user_id": "12345",
            "text": "Объясни теорему Пифагора"
        }
    }

    try:
        await producer.send_and_wait(topic, test_event)
        received = None
        for _ in range(10):
            try:
                msg = await asyncio.wait_for(consumer.getone(), timeout=1.0)
                if msg.value.get("correlation_id") == corr_id:
                    received = msg.value
                    break
            except asyncio.TimeoutError:
                pass

        assert received is not None
        assert received["event_type"] == "bot.command.received"
    finally:
        await producer.stop()
        await consumer.stop()
