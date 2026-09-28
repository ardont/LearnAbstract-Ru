import pytest
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.bot_service.idempotency import is_duplicate_message


@pytest.mark.asyncio
async def test_idempotency_with_message_id():
    user_id = f"user_{uuid.uuid4().hex[:6]}"
    msg_id = f"msg_{uuid.uuid4().hex[:8]}"

    # Первое сообщение — не дубликат
    is_dup1 = await is_duplicate_message(msg_id, user_id, "Привет")
    assert is_dup1 is False

    # Повтор с тем же message_id — дубликат!
    is_dup2 = await is_duplicate_message(msg_id, user_id, "Привет")
    assert is_dup2 is True


@pytest.mark.asyncio
async def test_idempotency_without_message_id():
    user_id = f"user_{uuid.uuid4().hex[:6]}"
    text = "Объясни теорему Пифагора"

    # Первое сообщение — не дубликат
    is_dup1 = await is_duplicate_message(None, user_id, text)
    assert is_dup1 is False

    # Повтор того же текста в ту же секунду — дубликат
    is_dup2 = await is_duplicate_message(None, user_id, text)
    assert is_dup2 is True

    # Другой текст — не дубликат
    is_dup3 = await is_duplicate_message(None, user_id, "Другой вопрос")
    assert is_dup3 is False
