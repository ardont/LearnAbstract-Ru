from typing import Dict, Any, Optional
from sqlalchemy import select
from services.core_service.db.database import get_db_session
from services.core_service.db.models import User, QuizSession, utcnow
from shared.utils.logger import setup_logger

logger = setup_logger("core_service.fsm")

VALID_STATES = {"GUEST_CHOICE", "SELECT_INTEREST", "IDLE", "EXPLAINING", "QUIZ_ACTIVE"}
AVAILABLE_INTERESTS = ["Футбол", "Видеоигры", "Музыка", "Космос", "Кино", "Общий"]


async def get_or_create_user(max_user_id: str) -> Dict[str, Any]:
    """Получает или создает пользователя в БД."""
    async with get_db_session() as session:
        result = await session.execute(select(User).where(User.max_user_id == str(max_user_id)))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                max_user_id=str(max_user_id),
                state="GUEST_CHOICE",
                grade=7,
                is_guest=False
            )
            session.add(user)
            await session.flush()

        return {
            "id": user.id,
            "max_user_id": user.max_user_id,
            "state": user.state,
            "interest": user.interest,
            "grade": user.grade,
            "is_guest": user.is_guest,
            "current_quiz_id": user.current_quiz_id
        }


async def set_consent(max_user_id: str, accepted: bool) -> Dict[str, Any]:
    """
    152-ФЗ: Обработка согласия или перехода в гостевой режим.
    При отказе устанавливается is_guest=True.
    """
    async with get_db_session() as session:
        result = await session.execute(select(User).where(User.max_user_id == str(max_user_id)))
        user = result.scalar_one_or_none()
        if not user:
            user = User(max_user_id=str(max_user_id))
            session.add(user)

        user.is_guest = not accepted
        user.state = "SELECT_INTEREST"
        user.updated_at = utcnow()
        await session.commit()

        logger.info(f"User {max_user_id} согласие: {accepted} (is_guest={user.is_guest})")
        return {"state": user.state, "is_guest": user.is_guest}


async def set_interest(max_user_id: str, interest: str) -> Dict[str, Any]:
    """Установка сферы интересов ученика."""
    async with get_db_session() as session:
        result = await session.execute(select(User).where(User.max_user_id == str(max_user_id)))
        user = result.scalar_one_or_none()
        if user:
            user.interest = interest if interest in AVAILABLE_INTERESTS else "Общий"
            user.state = "IDLE"
            user.updated_at = utcnow()
            await session.commit()
            return {"state": user.state, "interest": user.interest}
        return {"state": "IDLE", "interest": interest}


async def set_user_state(max_user_id: str, new_state: str, current_quiz_id: Optional[str] = None) -> None:
    """Установка состояния FSM."""
    if new_state not in VALID_STATES:
        raise ValueError(f"Неизвестное состояние FSM: {new_state}")

    async with get_db_session() as session:
        result = await session.execute(select(User).where(User.max_user_id == str(max_user_id)))
        user = result.scalar_one_or_none()
        if user:
            user.state = new_state
            if current_quiz_id is not None:
                user.current_quiz_id = current_quiz_id
            user.updated_at = utcnow()
            await session.commit()


async def register_quiz(
    max_user_id: str,
    quiz_id: str,
    topic: str,
    question: str,
    options: list,
    correct_option_index: int
) -> None:
    """Регистрирует активный квиз для пользователя и переводит в QUIZ_ACTIVE."""
    async with get_db_session() as session:
        quiz = QuizSession(
            quiz_id=quiz_id,
            max_user_id=str(max_user_id),
            topic=topic,
            question=question,
            correct_option_index=correct_option_index
        )
        quiz.options = options
        session.add(quiz)

        result = await session.execute(select(User).where(User.max_user_id == str(max_user_id)))
        user = result.scalar_one_or_none()
        if user:
            user.state = "QUIZ_ACTIVE"
            user.current_quiz_id = quiz_id
            user.updated_at = utcnow()

        await session.commit()
        logger.info(f"Зарегистрирован квиз {quiz_id} для пользователя {max_user_id}")


async def verify_quiz_answer(
    max_user_id: str,
    quiz_id: str,
    selected_option: int
) -> Dict[str, Any]:
    """
    Quiz Freshness Guard:
    Проверяет актуальность квиза: current_quiz_id == quiz_id.
    Если ученик нажал старую кнопку из истории — возвращает статус 'stale' и не ломает FSM.
    """
    async with get_db_session() as session:
        # Проверяем пользователя
        user_res = await session.execute(select(User).where(User.max_user_id == str(max_user_id)))
        user = user_res.scalar_one_or_none()

        if not user or user.current_quiz_id != quiz_id:
            logger.warning(
                f"Quiz Freshness Guard сработал для {max_user_id}: "
                f"активный квиз={getattr(user, 'current_quiz_id', None)}, прислан={quiz_id}"
            )
            return {
                "status": "stale",
                "is_correct": False,
                "message": "⚠️ Этот тест уже не активен или был пройден ранее. Вопрос не засчитан."
            }

        # Получаем данные самого квиза
        quiz_res = await session.execute(select(QuizSession).where(QuizSession.quiz_id == quiz_id))
        quiz = quiz_res.scalar_one_or_none()

        if not quiz:
            return {
                "status": "not_found",
                "is_correct": False,
                "message": "Квиз не найден в базе данных."
            }

        is_correct = (selected_option == quiz.correct_option_index)
        quiz.user_answer = selected_option
        quiz.is_correct = is_correct
        quiz.answered_at = utcnow()

        # Сбрасываем активный квиз и возвращаем в IDLE
        user.current_quiz_id = None
        user.state = "IDLE"
        user.updated_at = utcnow()

        await session.commit()
        logger.info(f"Ответ на квиз {quiz_id} проверен: correct={is_correct}")

        return {
            "status": "ok",
            "is_correct": is_correct,
            "correct_option_index": quiz.correct_option_index,
            "selected_option": selected_option
        }
