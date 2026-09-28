import pytest
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.core_service.db.database import init_db
from services.core_service.fsm import (
    get_or_create_user, set_consent, set_interest,
    register_quiz, verify_quiz_answer
)
from services.ml_service.llm_client import generate_explanation


@pytest.mark.asyncio
async def test_complete_e2e_pipeline():
    """Сквозной E2E тест образовательного диалога репетитора."""
    await init_db()
    user_id = f"e2e_{uuid.uuid4().hex[:6]}"

    # Шаг 1: Приветствие и согласие 152-ФЗ
    user = await get_or_create_user(user_id)
    assert user["state"] == "GUEST_CHOICE"

    consent = await set_consent(user_id, accepted=True)
    assert consent["is_guest"] is False
    assert consent["state"] == "SELECT_INTEREST"

    # Шаг 2: Выбор интереса (Футбол)
    inter = await set_interest(user_id, "Футбол")
    assert inter["interest"] == "Футбол"
    assert inter["state"] == "IDLE"

    # Шаг 3: Генерация метафоры
    topic = "Квадратные уравнения"
    result = await generate_explanation(topic=topic, interest="Футбол", grade=7)

    assert result["text"] is not None
    assert len(result["text"]) > 50
    # Проверка, что формулы преобразованы в Unicode
    assert "x²" in result["text"] or "парабол" in result["text"].lower()

    # Шаг 4: Проверка сгенерированного квиза
    quiz = result.get("quiz")
    assert quiz is not None
    assert "quiz_id" in quiz
    assert len(quiz["options"]) >= 2
    correct_idx = quiz["correct_option_index"]

    # Шаг 5: Регистрация квиза в FSM
    await register_quiz(
        max_user_id=user_id,
        quiz_id=quiz["quiz_id"],
        topic=topic,
        question=quiz["question"],
        options=quiz["options"],
        correct_option_index=correct_idx
    )

    # Шаг 6: Прохождение квиза (верный ответ)
    ans = await verify_quiz_answer(user_id, quiz["quiz_id"], selected_option=correct_idx)
    assert ans["status"] == "ok"
    assert ans["is_correct"] is True

    # Шаг 7: Защита Quiz Freshness Guard от повторного прохождения
    dup_ans = await verify_quiz_answer(user_id, quiz["quiz_id"], selected_option=correct_idx)
    assert dup_ans["status"] == "stale"
