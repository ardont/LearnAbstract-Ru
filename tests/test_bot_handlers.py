import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.bot_service.main import classify_intent
from services.bot_service.keyboards import (
    get_consent_keyboard,
    get_interests_keyboard,
    get_quiz_keyboard,
    get_after_explanation_keyboard,
    get_profile_keyboard
)
from services.core_service.db.database import init_db
from services.core_service.fsm import get_or_create_user, reset_user, get_user_profile, set_consent, set_interest


def test_classify_intent():
    # 1. Commands
    assert classify_intent("/start") == "command"
    assert classify_intent("/help") == "command"
    assert classify_intent("/hobby") == "command"
    assert classify_intent("/quiz") == "command"
    assert classify_intent("/profile") == "command"
    assert classify_intent("/reset") == "command"

    # 2. Educational queries
    assert classify_intent("Объясни мне квадратные уравнения") == "educational"
    assert classify_intent("В чём суть закона Ома?") == "educational"
    assert classify_intent("Теорема Пифагора") == "educational"
    assert classify_intent("Как работает фотосинтез?") == "educational"
    assert classify_intent("Что такое сила гравитации?") == "educational"
    assert classify_intent("Алгоритм сортировки пузырьком") == "educational"

    # 3. Off-topic chitchat
    assert classify_intent("привет, как дела?") == "chitchat"
    assert classify_intent("какая сегодня погода?") == "chitchat"
    assert classify_intent("расскажи анекдот") == "chitchat"
    assert classify_intent("кто ты") == "chitchat"

    # 4. Vague / too short queries
    assert classify_intent("уравнение") == "vague"
    assert classify_intent("закон") == "vague"
    assert classify_intent("формула") == "vague"


def test_keyboards_structure():
    # Consent keyboard (3 buttons)
    ck = get_consent_keyboard()
    assert len(ck.inline_keyboard) == 3
    texts = [btn.text for row in ck.inline_keyboard for btn in row]
    assert any("Согласен" in t for t in texts)
    assert any("Гостевой" in t for t in texts)
    assert any("О проекте" in t for t in texts)

    # Interests keyboard (6 buttons)
    ik = get_interests_keyboard()
    int_texts = [btn.text for row in ik.inline_keyboard for btn in row]
    assert len(int_texts) == 6
    assert any("Футбол" in t for t in int_texts)
    assert any("Видеоигры" in t for t in int_texts)
    assert any("Музыка" in t for t in int_texts)
    assert any("Космос" in t for t in int_texts)

    # Quiz keyboard
    qk = get_quiz_keyboard("q123", ["Вариант A", "Вариант B", "Вариант C"])
    assert len(qk.inline_keyboard) == 3

    # Post-explanation keyboard
    pk = get_after_explanation_keyboard(topic="Закон Ома", quiz_id="q123")
    pk_texts = [btn.text for row in pk.inline_keyboard for btn in row]
    assert any("Пройти тест" in t for t in pk_texts)
    assert any("Другая метафора" in t for t in pk_texts)
    assert any("Мой прогресс" in t for t in pk_texts)

    # Profile keyboard
    pro_k = get_profile_keyboard()
    pro_texts = [btn.text for row in pro_k.inline_keyboard for btn in row]
    assert any("Сменить хобби" in t for t in pro_texts)
    assert any("Сбросить профиль" in t for t in pro_texts)


@pytest.mark.asyncio
async def test_fsm_reset_and_profile():
    await init_db()
    uid = "test_bot_user_999"

    # Setup user
    await get_or_create_user(uid)
    await set_consent(uid, accepted=True)
    await set_interest(uid, "Космос")

    # Check profile
    prof = await get_user_profile(uid)
    assert prof["interest"] == "Космос"
    assert prof["is_guest"] is False
    assert "total_quizzes" in prof
    assert "points" in prof

    # Reset user
    reset_res = await reset_user(uid)
    assert reset_res["status"] == "ok"
    assert reset_res["state"] == "GUEST_CHOICE"

    # Profile after reset
    prof2 = await get_user_profile(uid)
    assert prof2["state"] == "GUEST_CHOICE"
