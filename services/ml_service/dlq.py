import os
import json
import traceback
from typing import Dict, Any, Optional
from aiokafka import AIOKafkaProducer
from shared.schemas.events import EventEnvelope, DLQPayload
from shared.utils.logger import setup_logger

logger = setup_logger("ml_service.dlq")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DLQ_TOPIC = os.getenv("KAFKA_TOPIC_DLQ", "education.events.dlq")

_producer: Optional[AIOKafkaProducer] = None


async def get_dlq_producer() -> Optional[AIOKafkaProducer]:
    global _producer
    if _producer is None:
        try:
            p = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            await p.start()
            _producer = p
        except Exception as e:
            logger.warning(f"Kafka DLQ Producer недоступен: {e}")
            _producer = None
    return _producer


async def send_to_dlq(original_event: Dict[str, Any], exc: Exception, service_name: str = "ml_service") -> None:
    """
    Отправляет необрабатываемое или сбойное событие в Dead Letter Queue (education.events.dlq).
    """
    error_str = str(exc)
    stack = traceback.format_exc()

    dlq_payload = DLQPayload(
        original_event=original_event,
        error=error_str,
        stack_trace=stack,
        service=service_name
    )

    envelope = EventEnvelope(
        event_type="education.events.dlq",
        producer=service_name,
        payload=dlq_payload.model_dump()
    )

    logger.error(f"Отправка сбойного события в DLQ: {error_str}")

    producer = await get_dlq_producer()
    if producer:
        try:
            await producer.send_and_wait(DLQ_TOPIC, envelope.model_dump())
            logger.info("Событие успешно опубликовано в топик DLQ.")
        except Exception as send_err:
            logger.critical(f"Не удалось записать событие в Kafka DLQ: {send_err}")
    else:
        logger.warning("DLQ топик сохранен в локальный лог аварийных событий.")
