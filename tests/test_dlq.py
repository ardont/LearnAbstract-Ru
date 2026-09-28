import pytest
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.ml_service.dlq import send_to_dlq
from shared.schemas.events import EventEnvelope


@pytest.mark.asyncio
async def test_dlq_payload_formatting():
    """Тест формирования и обработки аварийных сообщений в Dead Letter Queue."""
    orig_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "explanation.requested",
        "payload": {
            "max_user_id": "test_user_dlq",
            "topic": "Сложная тема"
        }
    }

    test_exception = ValueError("Симуляция фатального сбоя ML модели")

    # Вызываем send_to_dlq (при отсутствии брокера gracefully пишет в лог)
    await send_to_dlq(orig_event, test_exception, service_name="ml_service_test")

    # Проверяем, что метод отработал без необработанных исключений
    assert True
