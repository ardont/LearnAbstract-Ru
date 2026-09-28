import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

# Принудительная установка UTF-8 для вывода в консоль Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Подключаем корень репозитория
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.core_service.db.database import init_db, get_db_session
from services.core_service.db.models import User, QuizSession, ExplanationLog


async def seed_data():
    print("Наполнение базы демонстрационными данными (ученики, темы, квизы)...")
    await init_db()

    demo_users = [
        {"max_user_id": "1001", "interest": "Футбол", "grade": 7, "is_guest": False, "state": "IDLE"},
        {"max_user_id": "1002", "interest": "Видеоигры", "grade": 8, "is_guest": False, "state": "IDLE"},
        {"max_user_id": "1003", "interest": "Музыка", "grade": 9, "is_guest": False, "state": "IDLE"},
        {"max_user_id": "1004", "interest": "Космос", "grade": 10, "is_guest": False, "state": "QUIZ_ACTIVE"},
        {"max_user_id": "1005", "interest": "Кино", "grade": 7, "is_guest": True, "state": "IDLE"},
        {"max_user_id": "1006", "interest": "Футбол", "grade": 8, "is_guest": False, "state": "IDLE"},
    ]

    demo_quizzes = [
        {
            "quiz_id": str(uuid.uuid4()),
            "max_user_id": "1001",
            "topic": "Квадратные уравнения",
            "question": "Что в футбольной аналогии означают корни квадратного уравнения?",
            "options": ["Силу удара", "Точки взлёта и приземления мяча", "Номер игрока", "Свисток судьи"],
            "correct_option_index": 1,
            "user_answer": 1,
            "is_correct": True
        },
        {
            "quiz_id": str(uuid.uuid4()),
            "max_user_id": "1002",
            "topic": "Закон Ома",
            "question": "Что в аналогии RPG соответствует электрическому сопротивлению R?",
            "options": ["Броня босса", "Мана игрока", "Урон от файербола", "Скорость бега"],
            "correct_option_index": 0,
            "user_answer": 0,
            "is_correct": True
        },
        {
            "quiz_id": str(uuid.uuid4()),
            "max_user_id": "1003",
            "topic": "Теорема Пифагора",
            "question": "Чему равна гипотенуза при катетах 30 и 40 метров?",
            "options": ["70 м", "50 м", "60 м", "100 м"],
            "correct_option_index": 1,
            "user_answer": 1,
            "is_correct": True
        },
        {
            "quiz_id": str(uuid.uuid4()),
            "max_user_id": "1006",
            "topic": "Гравитация",
            "question": "Как изменится сила притяжения при увеличении расстояния в 2 раза?",
            "options": ["Уменьшится в 2 раза", "Уменьшится в 4 раза", "Увеличится в 2 раза", "Не изменится"],
            "correct_option_index": 1,
            "user_answer": 0,
            "is_correct": False
        },
    ]

    demo_logs = [
        {"max_user_id": "1001", "topic": "Квадратные уравнения", "interest": "Футбол", "source": "fallback_exact", "latency_ms": 180},
        {"max_user_id": "1002", "topic": "Закон Ома", "interest": "Видеоигры", "source": "llm", "latency_ms": 1420},
        {"max_user_id": "1003", "topic": "Теорема Пифагора", "interest": "Музыка", "source": "fallback_exact", "latency_ms": 195},
        {"max_user_id": "1004", "topic": "Черные дыры и гравитация", "interest": "Космос", "source": "fallback_subject", "latency_ms": 210},
        {"max_user_id": "1005", "topic": "Теория вероятностей", "interest": "Кино", "source": "fallback_general", "latency_ms": 175},
        {"max_user_id": "1006", "topic": "Гравитация", "interest": "Футбол", "source": "llm", "latency_ms": 1380},
    ]

    async with get_db_session() as session:
        for u in demo_users:
            user = User(
                max_user_id=u["max_user_id"],
                interest=u["interest"],
                grade=u["grade"],
                is_guest=u["is_guest"],
                state=u["state"]
            )
            session.add(user)

        for q in demo_quizzes:
            quiz = QuizSession(
                quiz_id=q["quiz_id"],
                max_user_id=q["max_user_id"],
                topic=q["topic"],
                question=q["question"],
                correct_option_index=q["correct_option_index"],
                user_answer=q["user_answer"],
                is_correct=q["is_correct"]
            )
            quiz.options = q["options"]
            session.add(quiz)

        for l in demo_logs:
            log_item = ExplanationLog(
                max_user_id=l["max_user_id"],
                topic=l["topic"],
                interest=l["interest"],
                source=l["source"],
                latency_ms=l["latency_ms"],
                is_guest=False
            )
            session.add(log_item)

        await session.commit()

    print("[OK] Демонстрационные данные успешно загружены! Дашборд /teacher готов к показу.")


if __name__ == "__main__":
    asyncio.run(seed_data())
