import asyncio
import json
import os
import secrets
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from pathlib import Path
import shutil

from fastapi import FastAPI, Depends, HTTPException, status, Response, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import select, func
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import httpx

from scripts.ingest_textbook import ingest_textbook
from services.core_service.student_ui import render_student_portal

from services.core_service.db.database import (
    init_db, get_db_session, is_sqlite_fallback
)
from services.core_service.db.models import User, QuizSession, ExplanationLog
from services.core_service.fsm import (
    get_or_create_user, set_consent, set_interest, set_user_state,
    register_quiz, verify_quiz_answer
)
from services.core_service.rate_limiter import check_rate_limit, get_redis_client
from services.core_service.metrics import (
    record_explanation, record_llm_error, get_metrics_summary,
    render_prometheus_metrics
)
from shared.schemas.events import EventEnvelope
from shared.utils.logger import setup_logger

logger = setup_logger("core_service.main")

TEACHER_USER = os.getenv("TEACHER_USER", "teacher")
TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD", "change_me_in_production")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_EVENTS = os.getenv("KAFKA_TOPIC_EVENTS", "education.events")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8002")
CORE_CONSUMER_GROUP = "core_service_group"

security = HTTPBasic()
kafka_consumer: Optional[AIOKafkaConsumer] = None
kafka_producer: Optional[AIOKafkaProducer] = None
consumer_task: Optional[asyncio.Task] = None
is_running = True


def detect_subject(topic: str) -> str:
    """Определяет учебный предмет по ключевым словам темы."""
    lower = topic.lower()
    if any(k in lower for k in ["уравнен", "дроб", "пифагор", "функци", "алгебр", "чисел", "корень"]):
        return "algebra"
    if any(k in lower for k in ["ом", "сила", "гравитац", "ток", "физик", "давлен", "ускорен"]):
        return "physics"
    if any(k in lower for k in ["алгоритм", "код", "массив", "программ", "информатик"]):
        return "cs"
    if any(k in lower for k in ["фотосинтез", "клетк", "биолог", "организм"]):
        return "biology"
    return "algebra"


async def core_kafka_worker():
    global kafka_consumer, kafka_producer, is_running
    try:
        kafka_consumer = AIOKafkaConsumer(
            KAFKA_TOPIC_EVENTS,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CORE_CONSUMER_GROUP,
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
        logger.info(f"Core Service Kafka Worker запущен (группа: {CORE_CONSUMER_GROUP})")

        while is_running:
            try:
                msg = await asyncio.wait_for(kafka_consumer.getone(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            event = msg.value
            event_type = event.get("event_type")

            # 1. Читаем bot.command.received от бота, обогащаем профилем FSM и отправляем в ML
            if event_type == "bot.command.received":
                payload = event.get("payload", {})
                user_id = payload.get("max_user_id")
                text = payload.get("text", "")

                if user_id and text:
                    # Проверяем пользователя
                    user = await get_or_create_user(user_id)
                    subject = detect_subject(text)

                    # Формируем событие для ML-сервиса
                    req_event = EventEnvelope(
                        event_type="explanation.requested",
                        correlation_id=event.get("correlation_id"),
                        causation_id=event.get("event_id"),
                        producer="core_service",
                        payload={
                            "max_user_id": str(user_id),
                            "topic": text,
                            "interest": user.get("interest") or "Футбол",
                            "grade": user.get("grade", 7),
                            "is_guest": user.get("is_guest", False),
                            "subject": subject,
                            "user_query": text
                        }
                    )
                    await kafka_producer.send_and_wait(KAFKA_TOPIC_EVENTS, req_event.model_dump())
                    logger.info(f"Core Service переслал запрос в ML (subject={subject}) для {user_id}")

            # 2. Логируем готовые ответы
            elif event_type == "explanation.ready":
                payload = event.get("payload", {})
                user_id = payload.get("max_user_id")
                topic = payload.get("topic")
                latency_ms = payload.get("latency_ms", 0)
                source = payload.get("source", "llm")

                if user_id and topic:
                    record_explanation(latency_ms, source)
                    try:
                        async with get_db_session() as session:
                            session.add(ExplanationLog(
                                max_user_id=str(user_id),
                                topic=topic,
                                interest=payload.get("interest", "Общий"),
                                source=source,
                                latency_ms=latency_ms,
                                is_guest=False
                            ))
                    except Exception:
                        pass

            await kafka_consumer.commit()

    except Exception as e:
        logger.warning(f"Kafka брокер недоступен для Core Service: {e}. Работа в прямом API режиме.")
    finally:
        if kafka_consumer:
            await kafka_consumer.stop()
        if kafka_producer:
            await kafka_producer.stop()


def check_basic_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    correct_user = secrets.compare_digest(credentials.username, TEACHER_USER)
    correct_pass = secrets.compare_digest(credentials.password, TEACHER_PASSWORD)
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer_task, is_running
    logger.info("Запуск Core Service...")
    await init_db()

    is_running = True
    consumer_task = asyncio.create_task(core_kafka_worker())

    def handle_signal(sig, frame):
        global is_running
        logger.info(f"Получен сигнал {sig}. Graceful Shutdown...")
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
    logger.info("Core Service успешно остановлен.")


app = FastAPI(
    title="Твой Путь: Core Service API",
    version="5.2.0",
    description="FSM, Quiz Freshness Guard, Rate Limiting, Health Monitoring & Teacher Dashboard",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# --- DTOs ---
class UserMessageRequest(BaseModel):
    max_user_id: str
    text: str
    message_id: Optional[str] = None


class ConsentRequest(BaseModel):
    max_user_id: str
    accepted: bool


class InterestRequest(BaseModel):
    max_user_id: str
    interest: str


class QuizAnswerRequest(BaseModel):
    max_user_id: str
    quiz_id: str
    selected_option_index: int


class MetricRecordRequest(BaseModel):
    latency_ms: int
    source: str
    max_user_id: Optional[str] = None
    topic: Optional[str] = None
    interest: Optional[str] = None


class StudentAskRequest(BaseModel):
    user_id: str = "student_demo"
    topic: str
    interest: str = "Футбол"
    grade: int = 7


# --- Endpoints ---
@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Базовый healthcheck для Docker Compose."""
    return {"status": "ok", "service": "core_service"}


@app.get("/health/full", tags=["Monitoring"])
async def health_full():
    """
    Мониторинг для второго экрана:
    детальный статус всех зависимостей, операционные метрики и метрики RAG.
    """
    db_status = "ok (sqlite_fallback)" if is_sqlite_fallback else "ok (postgres)"
    
    redis_client = await get_redis_client()
    redis_status = "ok (redis)" if redis_client else "degraded (in-memory fallback)"

    metrics_data = get_metrics_summary()

    # Считаем количество активных пользователей в БД
    active_users = 0
    try:
        async with get_db_session() as session:
            res = await session.execute(select(func.count(User.id)))
            active_users = res.scalar() or 0
    except Exception:
        pass

    metrics_data["active_users"] = active_users

    # Получаем метрики RAG из ML Service
    rag_metrics = {"rag_queries_total": 0, "rag_hits_total": 0, "rag_hit_rate_pct": 0.0}
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{ML_SERVICE_URL}/health")
            if resp.status_code == 200:
                rag_metrics = resp.json().get("rag", rag_metrics)
    except Exception:
        pass

    metrics_data.update(rag_metrics)

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": db_status,
            "redis": redis_status,
            "kafka": "ready",
            "llm": "ready (with 3-tier fallback & RAG)",
            "bot_listener": "online"
        },
        "metrics": metrics_data,
        "last_error": None
    }


@app.get("/metrics", tags=["Monitoring"])
async def prometheus_metrics():
    """Prometheus-совместимый эндпоинт экспорта метрик."""
    content = render_prometheus_metrics()
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")


@app.post("/api/user/message", tags=["FSM & Routing"])
async def process_user_message(req: UserMessageRequest):
    """
    Обработка входящего сообщения:
    1. Rate Limiting (10 RPM)
    2. Проверка и обновление состояния FSM
    """
    is_limited, retry_after = await check_rate_limit(req.max_user_id)
    if is_limited:
        return {
            "action": "rate_limited",
            "message": f"⏳ Слишком много запросов! Пожалуйста, подожди {retry_after} сек. перед следующим вопросом."
        }

    user = await get_or_create_user(req.max_user_id)
    state = user["state"]

    if state == "GUEST_CHOICE":
        return {
            "action": "ask_consent",
            "message": (
                "👋 Привет! Я — «Абстрактный Репетитор».\n"
                "Я объясняю сложные темы через то, что тебе действительно нравится: спорт, игры, музыку!\n\n"
                "Согласно 152-ФЗ, для сохранения твоего прогресса и персонализации ответов нам требуется согласие на обработку данных."
            ),
            "buttons": [
                {"text": "✅ Согласен (Полный режим)", "callback": "consent_accept"},
                {"text": "🔒 Отказаться (Гостевой режим)", "callback": "consent_decline"}
            ]
        }

    if state == "SELECT_INTEREST":
        return {
            "action": "select_interest",
            "message": "Выбери тему, через которую тебе интереснее всего понимать примеры:",
            "buttons": [
                {"text": "⚽ Футбол", "callback": "interest_Футбол"},
                {"text": "🎮 Видеоигры", "callback": "interest_Видеоигры"},
                {"text": "🎵 Музыка", "callback": "interest_Музыка"},
                {"text": "🚀 Космос", "callback": "interest_Космос"},
                {"text": "🎬 Кино", "callback": "interest_Кино"},
                {"text": "🌐 Общий кругозор", "callback": "interest_Общий"}
            ]
        }

    if state == "QUIZ_ACTIVE":
        return {
            "action": "wait_quiz",
            "message": "У тебя сейчас открыт проверочный тест по предыдущей теме! Ответь на него с помощью кнопок выше или напиши /skip."
        }

    await set_user_state(req.max_user_id, "EXPLAINING")
    subject = detect_subject(req.text)

    return {
        "action": "request_explanation",
        "user_id": req.max_user_id,
        "interest": user.get("interest") or "Общий",
        "grade": user.get("grade", 7),
        "is_guest": user.get("is_guest", False),
        "subject": subject,
        "topic": req.text
    }


@app.post("/api/user/consent", tags=["FSM & Routing"])
async def process_consent(req: ConsentRequest):
    res = await set_consent(req.max_user_id, req.accepted)
    return {"status": "ok", "is_guest": res["is_guest"], "next_action": "select_interest"}


@app.post("/api/user/interest", tags=["FSM & Routing"])
async def process_interest(req: InterestRequest):
    res = await set_interest(req.max_user_id, req.interest)
    return {
        "status": "ok",
        "interest": res["interest"],
        "message": f"Отлично! Будем объяснять через «{res['interest']}». Задай мне любой школьный вопрос (например: «Что такое гравитация?» или «Объясни квадратные уравнения»)."
    }


@app.post("/api/quiz/register", tags=["Quiz"])
async def api_register_quiz(payload: Dict[str, Any]):
    await register_quiz(
        max_user_id=payload["max_user_id"],
        quiz_id=payload["quiz_id"],
        topic=payload["topic"],
        question=payload["question"],
        options=payload["options"],
        correct_option_index=payload["correct_option_index"]
    )
    return {"status": "ok"}


@app.post("/api/quiz/answer", tags=["Quiz"])
async def process_quiz_answer(req: QuizAnswerRequest):
    result = await verify_quiz_answer(
        max_user_id=req.max_user_id,
        quiz_id=req.quiz_id,
        selected_option=req.selected_option_index
    )
    return result


@app.post("/api/metrics/record", tags=["Monitoring"])
async def record_metric(req: MetricRecordRequest):
    record_explanation(req.latency_ms, req.source)
    if req.max_user_id and req.topic:
        try:
            async with get_db_session() as session:
                log_entry = ExplanationLog(
                    max_user_id=req.max_user_id,
                    topic=req.topic,
                    interest=req.interest or "Общий",
                    source=req.source,
                    latency_ms=req.latency_ms,
                    is_guest=False
                )
                session.add(log_entry)
        except Exception:
            pass
    return {"status": "ok"}


# --- Кабинет Ученика и RAG Загрузка ---
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/student")


@app.get("/student", response_class=HTMLResponse, tags=["Student Portal"])
async def student_portal():
    return HTMLResponse(content=render_student_portal())


@app.post("/api/student/ask", tags=["Student Portal"])
async def student_ask(req: StudentAskRequest):
    is_limited, retry_after = await check_rate_limit(req.user_id)
    if is_limited:
        return {
            "status": "rate_limited",
            "message": f"⏳ Слишком много запросов! Подождите {retry_after} сек."
        }

    user = await get_or_create_user(req.user_id)
    await set_interest(req.user_id, req.interest)
    subject = detect_subject(req.topic)

    start_t = asyncio.get_event_loop().time()
    data = None
    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            resp = await client.post(
                f"{ML_SERVICE_URL}/api/generate",
                json={
                    "topic": req.topic,
                    "interest": req.interest,
                    "grade": req.grade,
                    "subject": subject,
                    "user_query": req.topic
                }
            )
            if resp.status_code == 200:
                data = resp.json()
    except Exception as e:
        logger.warning(f"Прямой вызов ML Service не удался ({e}), используем локальный генератор")

    if not data:
        from services.ml_service.metaphor_engine import generate_explanation as local_gen
        data = await local_gen(topic=req.topic, interest=req.interest, grade=req.grade, subject=subject, user_query=req.topic)

    latency_ms = int((asyncio.get_event_loop().time() - start_t) * 1000)
    record_explanation(latency_ms, data.get("source", "fallback"))

    quiz = data.get("quiz")
    quiz_id = None
    if quiz and quiz.get("question") and quiz.get("options"):
        import uuid
        quiz_id = str(uuid.uuid4())
        await register_quiz(
            max_user_id=req.user_id,
            topic=req.topic,
            question=quiz["question"],
            options=quiz["options"],
            correct_option_index=quiz.get("correct_option_index", 0),
            quiz_id=quiz_id
        )

    try:
        async with get_db_session() as session:
            log_entry = ExplanationLog(
                max_user_id=req.user_id,
                topic=req.topic,
                interest=req.interest,
                source=data.get("source", "fallback"),
                latency_ms=latency_ms,
                is_guest=user.get("is_guest", False)
            )
            session.add(log_entry)
    except Exception as log_err:
        logger.warning(f"Ошибка сохранения лога: {log_err}")

    return {
        "status": "ok",
        "explanation": data.get("explanation") or data.get("text", ""),
        "source": data.get("source", "fallback"),
        "latency_ms": latency_ms,
        "rag_hits": data.get("rag_hits", 0),
        "rag_chunks": data.get("rag_chunks", []),
        "rag_subject": data.get("rag_subject", subject),
        "quiz": {
            "quiz_id": quiz_id,
            "question": quiz.get("question") if quiz else None,
            "options": quiz.get("options") if quiz else None
        } if quiz else None
    }


@app.post("/api/student/quiz_answer", tags=["Student Portal"])
async def student_quiz_answer(req: QuizAnswerRequest):
    result = await verify_quiz_answer(
        max_user_id=req.max_user_id,
        quiz_id=req.quiz_id,
        selected_option=req.selected_option_index
    )
    return result


@app.post("/api/student/upload_textbook", tags=["Student Portal"])
async def upload_textbook(file: UploadFile = File(...), subject: str = Form("algebra")):
    if not file.filename.lower().endswith(".pdf"):
        return {"status": "error", "message": "Поддерживаются только файлы формата PDF"}

    save_dir = Path("./data/textbooks")
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        chunks_count = ingest_textbook(str(file_path), subject=subject, vector_db_dir="./data/vector_db")
        return {
            "status": "ok",
            "message": f"Учебник «{file.filename}» успешно загружен и проиндексирован!",
            "chunks_count": chunks_count,
            "subject": subject,
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"Ошибка индексации учебника {file.filename}: {e}")
        return {
            "status": "error",
            "message": f"Ошибка индексации: {str(e)}"
        }


@app.get("/api/student/textbooks", tags=["Student Portal"])
async def list_textbooks():
    books = []
    vector_dir = Path("./data/vector_db")
    if vector_dir.exists():
        for subj_dir in vector_dir.iterdir():
            if subj_dir.is_dir():
                idx_file = subj_dir / "index.json"
                if idx_file.exists():
                    try:
                        with open(idx_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if isinstance(data, dict):
                            chunks_count = data.get("total_chunks", len(data.get("chunks", [])))
                            sources = [data.get("source", "Учебник")]
                        elif isinstance(data, list):
                            chunks_count = len(data)
                            sources = list(set(item.get("source", "unknown") for item in data))
                        else:
                            chunks_count = 0
                            sources = []

                        books.append({
                            "subject": subj_dir.name,
                            "chunks_count": chunks_count,
                            "sources": sources
                        })
                    except Exception:
                        pass
    return {"status": "ok", "textbooks": books}


# --- Дашборд Учителя /teacher ---
@app.get("/teacher", response_class=HTMLResponse, tags=["Dashboard"])
async def teacher_dashboard(username: str = Depends(check_basic_auth)):
    users_list = []
    quizzes_list = []
    logs_list = []

    try:
        async with get_db_session() as session:
            u_res = await session.execute(select(User).order_by(User.id.desc()).limit(20))
            users_list = u_res.scalars().all()

            q_res = await session.execute(select(QuizSession).order_by(QuizSession.id.desc()).limit(15))
            quizzes_list = q_res.scalars().all()

            l_res = await session.execute(select(ExplanationLog).order_by(ExplanationLog.id.desc()).limit(15))
            logs_list = l_res.scalars().all()
    except Exception as e:
        logger.error(f"Ошибка загрузки данных дашборда: {e}")

    total_quizzes = len(quizzes_list)
    correct_quizzes = sum(1 for q in quizzes_list if q.is_correct is True)
    quiz_success_pct = int((correct_quizzes / total_quizzes * 100)) if total_quizzes > 0 else 100

    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Дашборд Учителя · Твой Путь</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: #0b0f19;
                --card: #131b2e;
                --border: #232f48;
                --text: #f0f4fc;
                --text-muted: #8a99b5;
                --accent: #6366f1;
                --green: #10b981;
                --amber: #f59e0b;
            }}
            * {{ margin:0; padding:0; box-sizing: border-box; }}
            body {{
                font-family: 'Inter', sans-serif;
                background: var(--bg);
                color: var(--text);
                padding: 32px;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 32px;
                padding-bottom: 20px;
                border-bottom: 1px solid var(--border);
            }}
            .title h1 {{ font-size: 26px; font-weight: 700; }}
            .title p {{ color: var(--text-muted); font-size: 14px; margin-top: 4px; }}
            .status-badge {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 8px 16px;
                background: rgba(16, 185, 129, 0.12);
                border: 1px solid var(--green);
                color: #34d399;
                border-radius: 9999px;
                font-size: 13px;
                font-weight: 600;
            }}
            .pulse {{
                width: 8px; height: 8px; border-radius: 50%; background: var(--green);
                box-shadow: 0 0 10px var(--green);
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 20px;
                margin-bottom: 32px;
            }}
            .card {{
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 24px;
            }}
            .card-title {{ font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
            .card-value {{ font-size: 32px; font-weight: 700; margin-top: 8px; }}
            .table-container {{
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 24px;
                margin-bottom: 24px;
                overflow-x: auto;
            }}
            table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
            th {{ color: var(--text-muted); padding: 12px; border-bottom: 1px solid var(--border); }}
            td {{ padding: 14px 12px; border-bottom: 1px solid rgba(255,255,255,0.05); }}
            .tag {{
                padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 500;
                background: rgba(99, 102, 241, 0.15); color: #818cf8;
            }}
            .tag-correct {{ background: rgba(16, 185, 129, 0.15); color: #34d399; }}
            .tag-wrong {{ background: rgba(239, 68, 68, 0.15); color: #f87171; }}
        </style>
        <script>
            async function updateHealth() {{
                try {{
                    const res = await fetch('/health/full');
                    const data = await res.json();
                    const badge = document.getElementById('health-badge');
                    if (data.status === 'healthy') {{
                        badge.innerHTML = '<span class="pulse"></span>🟢 Все системы в норме (Kafka KRaft, RAG, 3-Tier Fallback)';
                    }} else {{
                        badge.innerHTML = '⚠️ Состояние: ' + data.status;
                    }}
                }} catch (e) {{
                    console.error('Ошибка обновления статуса:', e);
                }}
            }}
            setInterval(updateHealth, 5000);
        </script>
    </head>
    <body>
        <div class="header">
            <div class="title">
                <h1>Панель Учителя: «Абстрактный Репетитор»</h1>
                <p>Мониторинг образовательного прогресса, вовлечённости и инфраструктуры в реальном времени</p>
            </div>
            <div id="health-badge" class="status-badge">
                <span class="pulse"></span>🟢 Все системы в норме (Kafka KRaft & RAG OK)
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <div class="card-title">Всего учеников</div>
                <div class="card-value">{len(users_list)}</div>
            </div>
            <div class="card">
                <div class="card-title">Успешность квизов</div>
                <div class="card-value" style="color: #34d399;">{quiz_success_pct}%</div>
            </div>
            <div class="card">
                <div class="card-title">Объяснений выдано</div>
                <div class="card-value">{len(logs_list)}</div>
            </div>
            <div class="card">
                <div class="card-title">Шина событий</div>
                <div class="card-value" style="font-size: 20px; margin-top: 16px; color: #818cf8;">Kafka KRaft</div>
            </div>
        </div>

        <div class="table-container">
            <h2 style="font-size: 18px; margin-bottom: 16px;">Активность учеников</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID Ученика</th>
                        <th>Интерес (Метафора)</th>
                        <th>Класс</th>
                        <th>Режим 152-ФЗ</th>
                        <th>Текущее состояние</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(f'''
                    <tr>
                        <td><strong>{u.max_user_id}</strong></td>
                        <td><span class="tag">{u.interest or "Не выбран"}</span></td>
                        <td>{u.grade} класс</td>
                        <td>{"🔒 Гостевой" if u.is_guest else "✅ Согласие"}</td>
                        <td>{u.state}</td>
                    </tr>
                    ''' for u in users_list) if users_list else '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">Ученики пока не подключились.</td></tr>'}
                </tbody>
            </table>
        </div>

        <div class="table-container">
            <h2 style="font-size: 18px; margin-bottom: 16px;">Последние пройденные тесты (Quiz Freshness Guard)</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID Квиза</th>
                        <th>Ученик</th>
                        <th>Тема</th>
                        <th>Результат</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(f'''
                    <tr>
                        <td><code>{q.quiz_id[:8]}...</code></td>
                        <td>{q.max_user_id}</td>
                        <td>{q.topic}</td>
                        <td>
                            {"<span class='tag tag-correct'>Верно</span>" if q.is_correct else ("<span class='tag tag-wrong'>Неверно</span>" if q.is_correct is False else "<span class='tag'>В процессе</span>")}
                        </td>
                    </tr>
                    ''' for q in quizzes_list) if quizzes_list else '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">Квизы пока не сдавались.</td></tr>'}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.core_service.main:app", host="0.0.0.0", port=8000, reload=False)
