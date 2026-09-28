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


@pytest.mark.asyncio
async def test_fsm_consent_and_guest_mode():
    await init_db()
    test_user_id = f"test_{uuid.uuid4().hex[:6]}"

    # 1. Новый пользователь начинается с GUEST_CHOICE
    user = await get_or_create_user(test_user_id)
    assert user["state"] == "GUEST_CHOICE"
    assert user["is_guest"] is False

    # 2. Отказ от согласия -> перевод в гостевой режим is_guest=True
    consent_res = await set_consent(test_user_id, accepted=False)
    assert consent_res["is_guest"] is True
    assert consent_res["state"] == "SELECT_INTEREST"

    # 3. Выбор интереса
    int_res = await set_interest(test_user_id, "Футбол")
    assert int_res["interest"] == "Футбол"
    assert int_res["state"] == "IDLE"


@pytest.mark.asyncio
async def test_quiz_freshness_guard():
    await init_db()
    test_user_id = f"test_{uuid.uuid4().hex[:6]}"
    await get_or_create_user(test_user_id)

    quiz_id_1 = str(uuid.uuid4())
    await register_quiz(
        max_user_id=test_user_id,
        quiz_id=quiz_id_1,
        topic="Закон Ома",
        question="Тестовый вопрос?",
        options=["А", "Б", "В"],
        correct_option_index=1
    )

    # 1. Правильный ответ на актуальный квиз
    ans_res = await verify_quiz_answer(test_user_id, quiz_id_1, selected_option=1)
    assert ans_res["status"] == "ok"
    assert ans_res["is_correct"] is True

    # 2. Quiz Freshness Guard: повторный клик по тому же квизу
    stale_res = await verify_quiz_answer(test_user_id, quiz_id_1, selected_option=1)
    assert stale_res["status"] == "stale"
    assert "не активен" in stale_res["message"]

    # 3. Клик по несуществующему квизу
    bogus_res = await verify_quiz_answer(test_user_id, "fake_quiz_999", selected_option=0)
    assert bogus_res["status"] == "stale"
