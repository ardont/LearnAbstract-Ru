import asyncio
import json
import os
import signal
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI
from pydantic import BaseModel
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from services.ml_service.llm_client import generate_explanation, DEMO_MODE
from services.ml_service.dlq import send_to_dlq
from services.ml_service.metrics import get_rag_metrics_summary
from shared.schemas.events import EventEnvelope
from shared.utils.logger import setup_logger

logger = setup_logger("ml_service.main")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_EVENTS = os.getenv("KAFKA_TOPIC_EVENTS", "education.events")
CONSUMER_GROUP_ID = "ml_service_group"

consumer_task: Optional[asyncio.Task] = None
kafka_producer: Optional[AIOKafkaProducer] = None
kafka_consumer: Optional[AIOKafkaConsumer] = None
is_running = True


def on_rebalance_revoked(revoked):
    logger.info(f"Kafka rebalance: revoked partitions: {revoked}")


def on_rebalance_assigned(assigned):
    logger.info(f"Kafka rebalance: assigned partitions: {assigned}")


async def kafka_worker():
    global kafka_producer, kafka_consumer, is_running
    try:
        kafka_consumer = AIOKafkaConsumer(
            KAFKA_TOPIC_EVENTS,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP_ID,
            enable_auto_commit=False,
            auto_offset_reset="latest",
            value_deserializer=lambda x: json.loads(x.decode("utf-8"))
        )
        kafka_producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await kafka_consumer.start()
        await kafka_producer.start()
        logger.info(f"ML Service Kafka Worker запущен (топик: {KAFKA_TOPIC_EVENTS}, группа: {CONSUMER_GROUP_ID})")

        while is_running:
            try:
                msg = await asyncio.wait_for(kafka_consumer.getone(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            event = msg.value
            event_type = event.get("event_type")

            # Обрабатываем запросы explanation.requested
            if event_type in ("explanation.requested", "bot.command.received"):
                payload = event.get("payload", {})
                user_id = payload.get("max_user_id")
                topic = payload.get("topic") or payload.get("text", "")
                interest = payload.get("interest", "Футбол")
                grade = payload.get("grade", 7)
                subject = payload.get("subject", "algebra")

                if not user_id or not topic:
                    await kafka_consumer.commit()
                    continue

                logger.info(f"Получен запрос для {user_id}: тема «{topic}», интерес «{interest}», предмет «{subject}»")

                try:
                    # Тестовый хук для симуляции сбоя и тестирования DLQ
                    if os.getenv("SIMULATE_FAILURE") == "true":
                        raise ValueError("Симуляция фатальной ошибки для теста DLQ")

                    result = await generate_explanation(
                        topic=topic,
                        interest=interest,
                        grade=grade,
                        subject=subject,
                        user_query=payload.get("user_query")
                    )

                    reply_envelope = EventEnvelope(
                        event_type="explanation.ready",
                        correlation_id=event.get("correlation_id"),
                        causation_id=event.get("event_id"),
                        producer="ml-service",
                        payload={
                            "max_user_id": str(user_id),
                            "text": result["text"],
                            "topic": topic,
                            "source": result["source"],
                            "latency_ms": result["latency_ms"],
                            "quiz": result.get("quiz")
                        }
                    )

                    await kafka_producer.send_and_wait(KAFKA_TOPIC_EVENTS, reply_envelope.model_dump())
                    logger.info(f"Ответ explanation.ready отправлен в Kafka для {user_id} (источник: {result['source']})")

                    # Ручной коммит смещения после успешной обработки
                    await kafka_consumer.commit()

                except Exception as proc_err:
                    logger.error(f"Ошибка при обработке запроса: {proc_err}")
                    # Отправляем в DLQ с контекстом и затем коммитим offset
                    await send_to_dlq(event, proc_err, service_name="ml_service")
                    await kafka_consumer.commit()

    except Exception as e:
        logger.warning(f"Kafka брокер недоступен для ML Service: {e}. Работа в автономном HTTP режиме.")
    finally:
        if kafka_consumer:
            await kafka_consumer.stop()
        if kafka_producer:
            await kafka_producer.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer_task, is_running
    logger.info(f"Запуск ML Service (DEMO_MODE={DEMO_MODE})...")
    is_running = True
    consumer_task = asyncio.create_task(kafka_worker())

    def handle_signal(sig, frame):
        global is_running
        logger.info(f"ML Service получил сигнал {sig}. Graceful shutdown...")
        is_running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    yield

    is_running = False
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    logger.info("ML Service успешно остановлен.")


app = FastAPI(
    title="Твой Путь: ML Service",
    version="5.2.0",
    description="3-уровневый генератор аналогий, RAG, OutputGuardrails и интеграция с LLM",
    lifespan=lifespan
)


class GenerateRequest(BaseModel):
    topic: str
    interest: str = "Футбол"
    grade: int = 7
    subject: Optional[str] = "algebra"
    user_query: Optional[str] = None


@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Healthcheck для Docker Compose."""
    rag_metrics = get_rag_metrics_summary()
    return {
        "status": "ok",
        "service": "ml_service",
        "demo_mode": DEMO_MODE,
        "fallback_tiers": 3,
        "rag": rag_metrics
    }


@app.post("/api/generate", tags=["Generation"])
async def api_generate(req: GenerateRequest):
    """Прямой HTTP-эндпоинт генерации аналогии (для тестов и локального демо)."""
    result = await generate_explanation(
        topic=req.topic,
        interest=req.interest,
        grade=req.grade,
        subject=req.subject,
        user_query=req.user_query
    )
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.ml_service.main:app", host="0.0.0.0", port=8002, reload=False)
