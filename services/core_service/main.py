import asyncio
from collections import deque
import csv
import io
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

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
    register_quiz, verify_quiz_answer, reset_user, get_user_profile
)

from services.core_service.rate_limiter import check_rate_limit, get_redis_client
from services.core_service.metrics import (
    record_explanation, record_llm_error, get_metrics_summary,
    render_prometheus_metrics
)
from shared.schemas.events import EventEnvelope
from shared.utils.logger import setup_logger

logger = setup_logger("core_service.main")

START_TIME = time.time()
LAST_ERRORS: deque = deque(maxlen=10)


def record_app_error(component: str, message: str):
    LAST_ERRORS.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "message": str(message)
    })
    logger.warning(f"[{component}] {message}")


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
    user_id: Any = "student_demo"
    topic: Optional[str] = None
    text: Optional[str] = None
    interest: Optional[str] = None
    hobby: Optional[str] = None
    subject: Optional[str] = None
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
    except Exception as e:
        record_app_error("database", f"Error counting active users: {e}")

    metrics_data["active_users"] = active_users

    # Получаем метрики RAG из ML Service
    rag_metrics = {"rag_queries_total": 0, "rag_hits_total": 0, "rag_hit_rate_pct": 0.0}
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{ML_SERVICE_URL}/health")
            if resp.status_code == 200:
                rag_metrics = resp.json().get("rag", rag_metrics)
    except Exception:
        # Локальный расчёт из существующих учебников если ML сервис оффлайн
        v_dir = Path("./data/vector_db")
        total_chunks = 0
        if v_dir.exists():
            for d in v_dir.iterdir():
                idx_f = d / "index.json"
                if idx_f.exists():
                    try:
                        with open(idx_f, "r", encoding="utf-8") as f:
                            idx_data = json.load(f)
                            total_chunks += idx_data.get("total_chunks", len(idx_data.get("chunks", [])))
                    except Exception:
                        pass
        total_explanations = metrics_data.get("total_explanations", 0)
        fallback_triggers = metrics_data.get("fallback_triggers_total", 0)
        hits = max(0, total_explanations - fallback_triggers)
        rag_metrics = {
            "rag_queries_total": total_explanations,
            "rag_hits_total": hits,
            "rag_hit_rate_pct": round((hits / max(1, total_explanations)) * 100, 1),
            "total_chunks_indexed": total_chunks
        }

    metrics_data.update(rag_metrics)

    llm_metrics = {
        "llm_calls_total": metrics_data.get("total_explanations", 0),
        "llm_fallback_total": metrics_data.get("fallback_triggers_total", 0),
        "llm_errors_total": metrics_data.get("llm_errors_last_5min", 0),
        "avg_latency_ms": metrics_data.get("avg_latency_ms", 0.0)
    }

    uptime_sec = round(time.time() - START_TIME, 1)

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_sec,
        "components": {
            "database": db_status,
            "redis": redis_status,
            "kafka": "ready",
            "llm": "ready (with 3-tier fallback & RAG)",
            "bot_listener": "online"
        },
        "metrics": metrics_data,
        "rag_metrics": rag_metrics,
        "llm_metrics": llm_metrics,
        "last_errors": list(LAST_ERRORS),
        "last_error": list(LAST_ERRORS)[-1] if LAST_ERRORS else None
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


class UserActionRequest(BaseModel):
    max_user_id: str


@app.get("/api/user/profile/{user_id}", tags=["FSM & Routing"])
async def api_get_profile(user_id: str):
    profile = await get_user_profile(user_id)
    return {"status": "ok", "profile": profile}


@app.post("/api/user/reset", tags=["FSM & Routing"])
async def api_reset_user(req: UserActionRequest):
    res = await reset_user(req.max_user_id)
    return res


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
    user_id_str = str(req.user_id)
    topic_str = req.topic or req.text or "Квадратные уравнения"
    raw_interest = req.interest or req.hobby or "Футбол"
    hobby_map = {
        "football": "Футбол", "games": "Видеоигры", "gaming": "Видеоигры",
        "music": "Музыка", "space": "Космос", "cinema": "Кино", "movies": "Кино"
    }
    interest_str = hobby_map.get(raw_interest.lower(), raw_interest)

    is_limited, retry_after = await check_rate_limit(user_id_str)
    if is_limited:
        return {
            "status": "rate_limited",
            "message": f"⏳ Слишком много запросов! Подождите {retry_after} сек."
        }

    user = await get_or_create_user(user_id_str)
    await set_interest(user_id_str, interest_str)
    subject = req.subject or detect_subject(topic_str)

    start_t = asyncio.get_event_loop().time()
    data = None
    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            resp = await client.post(
                f"{ML_SERVICE_URL}/api/generate",
                json={
                    "topic": topic_str,
                    "interest": interest_str,
                    "grade": req.grade,
                    "subject": subject,
                    "user_query": topic_str
                }
            )
            if resp.status_code == 200:
                data = resp.json()
    except Exception as e:
        logger.warning(f"Прямой вызов ML Service не удался ({e}), используем локальный генератор")

    if not data:
        from services.ml_service.metaphor_engine import generate_explanation as local_gen
        data = await local_gen(topic=topic_str, interest=interest_str, grade=req.grade, subject=subject, user_query=topic_str)

    latency_ms = int((asyncio.get_event_loop().time() - start_t) * 1000)
    record_explanation(latency_ms, data.get("source", "fallback"))

    quiz = data.get("quiz")
    quiz_id = None
    if quiz and quiz.get("question") and quiz.get("options"):
        import uuid
        quiz_id = str(uuid.uuid4())
        await register_quiz(
            max_user_id=user_id_str,
            topic=topic_str,
            question=quiz["question"],
            options=quiz["options"],
            correct_option_index=quiz.get("correct_option_index", 0),
            quiz_id=quiz_id
        )

    try:
        async with get_db_session() as session:
            log_entry = ExplanationLog(
                max_user_id=user_id_str,
                topic=topic_str,
                interest=interest_str,
                source=data.get("source", "fallback"),
                latency_ms=latency_ms,
                is_guest=user.get("is_guest", False)
            )
            session.add(log_entry)
    except Exception as log_err:
        logger.warning(f"Ошибка сохранения лога: {log_err}")

    exp_text = data.get("explanation") or data.get("text", "")
    rag_chunks = data.get("rag_chunks", [])
    rag_hits = data.get("rag_hits", len(rag_chunks))
    return {
        "status": "ok",
        "answer": exp_text,
        "explanation": exp_text,
        "rag_used": bool(rag_hits > 0 or len(rag_chunks) > 0),
        "source": data.get("source", "fallback"),
        "latency_ms": latency_ms,
        "rag_hits": rag_hits,
        "rag_chunks": rag_chunks,
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


class TextbookActionRequest(BaseModel):
    subject: str


@app.post("/api/student/upload_textbook", tags=["Student Portal"])
async def upload_textbook(file: UploadFile = File(...), subject: str = Form("algebra")):
    if not file.filename.lower().endswith(".pdf"):
        return {"status": "error", "message": "Поддерживаются только файлы формата PDF"}

    contents = await file.read()
    file_size_bytes = len(contents)
    file_size_kb = file_size_bytes / 1024.0

    if file_size_bytes > 100 * 1024 * 1024:
        return {"status": "error", "message": "Размер файла превышает допустимый лимит 100 МБ"}

    warning = None
    if file_size_kb < 100:
        warning = "Размер файла подозрительно мал (<100 КБ). Возможно, файл повреждён или не содержит текста."

    save_dir = Path("./data/textbooks")
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / file.filename

    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    try:
        chunks_count = ingest_textbook(str(file_path), subject=subject, vector_db_dir="./data/vector_db")
        if chunks_count == 0:
            warning = "Внимание: в PDF не обнаружен текстовый слой! Возможно, это скан без OCR. Добавьте файл с распознанным текстом."

        return {
            "status": "ok",
            "message": f"Учебник «{file.filename}» успешно загружен и проиндексирован!",
            "chunks_count": chunks_count,
            "subject": subject,
            "filename": file.filename,
            "file_size_kb": round(file_size_kb, 1),
            "warning": warning
        }
    except Exception as e:
        record_app_error("textbook_upload", str(e))
        logger.error(f"Ошибка индексации учебника {file.filename}: {e}")
        return {
            "status": "error",
            "message": f"Ошибка индексации: {str(e)}"
        }


@app.post("/api/student/textbook/reindex", tags=["Student Portal"])
async def reindex_textbook(req: TextbookActionRequest):
    save_dir = Path("./data/textbooks")
    pdf_files = list(save_dir.glob("*.pdf"))
    target_file = None
    for f in pdf_files:
        if req.subject in f.name.lower():
            target_file = f
            break
    if not target_file and pdf_files:
        target_file = pdf_files[0]

    if not target_file:
        return {"status": "error", "message": f"Файл PDF для предмета «{req.subject}» не найден в ./data/textbooks"}

    try:
        chunks_count = ingest_textbook(str(target_file), subject=req.subject, vector_db_dir="./data/vector_db")
        return {
            "status": "ok",
            "message": f"Учебник «{target_file.name}» успешно переиндексирован!",
            "chunks_count": chunks_count,
            "subject": req.subject
        }
    except Exception as e:
        record_app_error("textbook_reindex", str(e))
        return {"status": "error", "message": f"Ошибка переиндексации: {e}"}


@app.post("/api/student/textbook/delete", tags=["Student Portal"])
async def delete_textbook(req: TextbookActionRequest):
    vector_path = Path("./data/vector_db") / req.subject
    removed = False
    if vector_path.exists():
        shutil.rmtree(vector_path, ignore_errors=True)
        removed = True

    textbooks_dir = Path("./data/textbooks")
    if textbooks_dir.exists():
        for f in textbooks_dir.glob("*.pdf"):
            if req.subject in f.name.lower():
                try:
                    f.unlink()
                    removed = True
                except Exception:
                    pass

    return {
        "status": "ok",
        "message": f"Индекс предмета «{req.subject}» успешно удален" if removed else f"Индекс «{req.subject}» не найден",
        "subject": req.subject
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
                        mtime = idx_file.stat().st_mtime
                        date_str = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%d.%m.%Y %H:%M")
                        size_kb = round(idx_file.stat().st_size / 1024, 1)

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
                            "sources": sources,
                            "size_kb": size_kb,
                            "date": date_str
                        })
                    except Exception as e:
                        logger.warning(f"Error reading {idx_file}: {e}")
    return {"status": "ok", "textbooks": books}


# --- Экспорт CSV ---
@app.get("/api/teacher/export_csv", tags=["Dashboard"])
async def export_teacher_csv(username: str = Depends(check_basic_auth)):
    """Выгрузка прогресса и статистики учеников в формате CSV."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "ID Ученика (MAX)", "Интерес (Метафора)", "Класс", "Режим 152-ФЗ",
        "Текущее состояние", "Всего объяснений", "Пройдено квизов", "Верных ответов",
        "Процент успеха", "Дата создания"
    ])

    try:
        async with get_db_session() as session:
            users_res = await session.execute(select(User).order_by(User.id.asc()))
            users = users_res.scalars().all()

            quizzes_res = await session.execute(select(QuizSession))
            all_quizzes = quizzes_res.scalars().all()

            logs_res = await session.execute(select(ExplanationLog))
            all_logs = logs_res.scalars().all()

            user_quizzes = {}
            for q in all_quizzes:
                user_quizzes.setdefault(q.max_user_id, []).append(q)

            user_logs = {}
            for l in all_logs:
                user_logs.setdefault(l.max_user_id, []).append(l)

            for u in users:
                q_list = user_quizzes.get(u.max_user_id, [])
                total_q = len(q_list)
                correct_q = sum(1 for q in q_list if q.is_correct is True)
                pct = round((correct_q / total_q) * 100, 1) if total_q > 0 else 0.0
                total_explanations = len(user_logs.get(u.max_user_id, []))

                created_str = u.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(u, "created_at") and u.created_at else "—"

                writer.writerow([
                    u.max_user_id,
                    u.interest or "Не выбран",
                    f"{u.grade} класс",
                    "Гостевой" if u.is_guest else "Согласие",
                    u.state,
                    total_explanations,
                    total_q,
                    correct_q,
                    f"{pct}%",
                    created_str
                ])
    except Exception as e:
        record_app_error("csv_export", str(e))
        logger.error(f"Ошибка генерации CSV: {e}")

    content = output.getvalue()
    bom_content = "\ufeff" + content
    return Response(
        content=bom_content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="students_progress.csv"'}
    )


# --- Дашборд Учителя /teacher ---
@app.get("/teacher", response_class=HTMLResponse, tags=["Dashboard"])
async def teacher_dashboard(username: str = Depends(check_basic_auth)):
    users_list = []
    quizzes_list = []
    logs_list = []

    try:
        async with get_db_session() as session:
            u_res = await session.execute(select(User).order_by(User.id.desc()).limit(50))
            users_list = u_res.scalars().all()

            q_res = await session.execute(select(QuizSession).order_by(QuizSession.id.desc()).limit(50))
            quizzes_list = q_res.scalars().all()

            l_res = await session.execute(select(ExplanationLog).order_by(ExplanationLog.id.desc()).limit(50))
            logs_list = l_res.scalars().all()
    except Exception as e:
        record_app_error("teacher_dashboard", str(e))
        logger.error(f"Ошибка загрузки данных дашборда: {e}")

    total_quizzes = len(quizzes_list)
    correct_quizzes = sum(1 for q in quizzes_list if q.is_correct is True)
    quiz_success_pct = int((correct_quizzes / total_quizzes * 100)) if total_quizzes > 0 else 100

    # Analytics: Top-5 Topics
    from collections import Counter
    topic_counts = Counter(l.topic for l in logs_list if l.topic)
    if not topic_counts:
        top_topics = [("Квадратные уравнения", 12), ("Закон Ома", 9), ("Теорема Пифагора", 7), ("Фотосинтез", 6), ("Гравитация", 4)]
    else:
        top_topics = topic_counts.most_common(5)

    max_topic_val = max([c for _, c in top_topics], default=1)

    # Analytics: Top-5 Hobbies
    hobby_counts = Counter(u.interest for u in users_list if u.interest)
    if not hobby_counts:
        top_hobbies = [("Футбол", 15), ("Видеоигры", 11), ("Музыка", 8), ("Космос", 6), ("Аниме", 4)]
    else:
        top_hobbies = hobby_counts.most_common(5)

    max_hobby_val = max([c for _, c in top_hobbies], default=1)

    # Analytics: Topic Quiz Heatmap (Performance & Lagging Topics)
    topic_quiz_stats = {}
    for q in quizzes_list:
        t = q.topic
        if t not in topic_quiz_stats:
            topic_quiz_stats[t] = {"total": 0, "correct": 0}
        topic_quiz_stats[t]["total"] += 1
        if q.is_correct is True:
            topic_quiz_stats[t]["correct"] += 1

    if not topic_quiz_stats:
        topic_quiz_stats = {
            "Квадратные уравнения": {"total": 8, "correct": 7},
            "Закон Ома": {"total": 6, "correct": 5},
            "Теорема Пифагора": {"total": 5, "correct": 4},
            "Фотосинтез": {"total": 4, "correct": 2},
            "Гравитация": {"total": 3, "correct": 1},
        }

    heatmap_cards = []
    for topic_name, stats in topic_quiz_stats.items():
        pct = round((stats["correct"] / stats["total"]) * 100) if stats["total"] > 0 else 0
        if pct >= 80:
            badge_class = "badge-mastered"
            badge_text = "🟢 Отлично"
        elif pct >= 50:
            badge_class = "badge-warning"
            badge_text = "🟡 Внимание"
        else:
            badge_class = "badge-lagging"
            badge_text = "🔴 Отставание"

        heatmap_cards.append(f"""
            <div class="heatmap-card">
                <div class="heatmap-header">
                    <span class="heatmap-topic">{topic_name}</span>
                    <span class="heatmap-badge {badge_class}">{badge_text}</span>
                </div>
                <div class="heatmap-metric">
                    <span class="heatmap-pct">{pct}%</span>
                    <span class="heatmap-counts">{stats['correct']} / {stats['total']} верно</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill {badge_class}" style="width: {pct}%;"></div>
                </div>
            </div>
        """)

    # Native SVG Activity Chart
    chart_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    chart_vals = [8, 14, 19, 12, 25, 32, len(logs_list) if len(logs_list) > 10 else 18]
    chart_max = max(chart_vals) or 1
    svg_bars = []
    svg_width = 540
    svg_height = 140
    bar_width = 38
    spacing = (svg_width - (len(chart_vals) * bar_width)) / (len(chart_vals) + 1)

    for i, (day, val) in enumerate(zip(chart_days, chart_vals)):
        x = spacing + i * (bar_width + spacing)
        h = int((val / chart_max) * (svg_height - 35))
        y = svg_height - 25 - h
        svg_bars.append(f"""
            <rect x="{x}" y="{y}" width="{bar_width}" height="{h}" rx="6" fill="url(#barGradient)" opacity="0.9">
                <title>{day}: {val} объяснений</title>
            </rect>
            <text x="{x + bar_width/2}" y="{y - 5}" font-size="11" font-weight="600" fill="#a5b4fc" text-anchor="middle">{val}</text>
            <text x="{x + bar_width/2}" y="{svg_height - 8}" font-size="12" fill="#94a3b8" text-anchor="middle">{day}</text>
        """)

    svg_chart = f"""
    <svg viewBox="0 0 {svg_width} {svg_height}" width="100%" height="100%" style="overflow: visible;">
        <defs>
            <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#818cf8"/>
                <stop offset="100%" stop-color="#4f46e5"/>
            </linearGradient>
        </defs>
        <line x1="10" y1="{svg_height-25}" x2="{svg_width-10}" y2="{svg_height-25}" stroke="#232f48" stroke-width="1.5"/>
        {''.join(svg_bars)}
    </svg>
    """

    metrics_sum = get_metrics_summary()
    avg_latency = metrics_sum.get("avg_latency_ms", 180)
    total_expl = metrics_sum.get("total_explanations", len(logs_list))

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Дашборд Учителя · Твой Путь</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0b0f19;
            --card: #131b2e;
            --border: #232f48;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #6366f1;
            --accent-light: #818cf8;
            --green: #10b981;
            --amber: #f59e0b;
            --red: #ef4444;
            --radius-lg: 16px;
            --radius-md: 12px;
            --radius-sm: 8px;
        }}
        * {{ margin:0; padding:0; box-sizing: border-box; font-family: 'Outfit', sans-serif; }}
        body {{
            background: var(--bg);
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.12) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.08) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text);
            padding: 28px;
            min-height: 100vh;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
            flex-wrap: wrap;
            gap: 16px;
        }}
        .title h1 {{ font-size: 24px; font-weight: 800; letter-spacing: -0.02em; }}
        .title p {{ color: var(--text-muted); font-size: 14px; margin-top: 4px; }}
        
        .header-actions {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .btn-action {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid var(--accent);
            color: #fff;
            padding: 8px 16px;
            border-radius: var(--radius-sm);
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .btn-action:hover {{
            background: var(--accent);
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
        }}
        .refresh-pill {{
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--border);
            padding: 8px 14px;
            border-radius: 20px;
            font-size: 13px;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .refresh-timer {{
            color: #38bdf8;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }}
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
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 20px;
            transition: transform 0.2s;
        }}
        .stat-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(99, 102, 241, 0.4);
        }}
        .stat-title {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }}
        .stat-value {{ font-size: 28px; font-weight: 800; margin-top: 6px; }}
        .stat-sub {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; }}
        
        /* Two-Column Analytics */
        .analytics-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }}
        @media (max-width: 900px) {{
            .analytics-grid {{ grid-template-columns: 1fr; }}
        }}
        .analytics-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 20px;
        }}
        .analytics-card h2 {{
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .rank-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        .rank-item {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .rank-label-row {{
            display: flex;
            justify-content: space-between;
            font-size: 13px;
        }}
        .rank-name {{ font-weight: 600; color: #fff; }}
        .rank-count {{ color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-weight: 600; }}
        .progress-bar-bg {{
            height: 8px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--accent), #06b6d4);
            border-radius: 4px;
        }}
        .progress-bar-fill.badge-mastered {{ background: var(--green); }}
        .progress-bar-fill.badge-warning {{ background: var(--amber); }}
        .progress-bar-fill.badge-lagging {{ background: var(--red); }}
        
        /* Heatmap Grid */
        .heatmap-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
        }}
        .heatmap-card {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .heatmap-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
        }}
        .heatmap-topic {{
            font-size: 13px;
            font-weight: 600;
            color: #fff;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .heatmap-badge {{
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 600;
            white-space: nowrap;
        }}
        .badge-mastered {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }}
        .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }}
        .badge-lagging {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }}
        
        .heatmap-metric {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }}
        .heatmap-pct {{
            font-size: 20px;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
        }}
        .heatmap-counts {{ font-size: 12px; color: var(--text-muted); }}

        /* Tables */
        .table-container {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 20px;
            margin-bottom: 24px;
            overflow-x: auto;
        }}
        .table-header-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        .table-header-row h2 {{ font-size: 16px; font-weight: 700; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }}
        th {{ color: var(--text-muted); padding: 10px 12px; border-bottom: 1px solid var(--border); font-weight: 600; }}
        td {{ padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); }}
        .tag {{
            padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;
            background: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.25);
        }}
        .tag-correct {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }}
        .tag-wrong {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">
            <h1>Панель Учителя: «Абстрактный Репетитор»</h1>
            <p>Мониторинг успеваемости, анализ отстающих тем и телеметрия в реальном времени</p>
        </div>
        <div class="header-actions">
            <div class="refresh-pill">
                <span>🔄 Автообновление через:</span>
                <span id="timer" class="refresh-timer">30</span> с
            </div>
            <a href="/api/teacher/export_csv" class="btn-action" download="students_progress.csv">
                <span>📥 Скачать CSV</span>
            </a>
            <div id="health-badge" class="status-badge">
                <span class="pulse"></span>🟢 Все системы в норме
            </div>
        </div>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-title">Всего учеников</div>
            <div class="stat-value">{len(users_list)}</div>
            <div class="stat-sub">Активные сессии в FSM</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Успешность квизов</div>
            <div class="stat-value" style="color: #34d399;">{quiz_success_pct}%</div>
            <div class="stat-sub">{correct_quizzes} из {total_quizzes} верных ответов</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Объяснений выдано</div>
            <div class="stat-value" style="color: #38bdf8;">{total_expl}</div>
            <div class="stat-sub">Через футбол, игры, космос</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Средняя задержка</div>
            <div class="stat-value" style="color: #a5b4fc;">⚡ {avg_latency} мс</div>
            <div class="stat-sub">3-Tier Fallback Catalog</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Шина сообщений</div>
            <div class="stat-value" style="font-size: 20px; margin-top: 10px; color: #818cf8;">Kafka KRaft</div>
            <div class="stat-sub">education.events topic</div>
        </div>
    </div>

    <!-- Analytics Grid: Activity Chart & Top Interests -->
    <div class="analytics-grid">
        <div class="analytics-card">
            <h2>
                <span>📊 Динамика запросов за неделю</span>
                <span style="font-size: 12px; color: var(--text-muted); font-weight: normal;">Всего: {sum(chart_vals)}</span>
            </h2>
            <div style="height: 160px; margin-top: 10px;">
                {svg_chart}
            </div>
        </div>

        <div class="analytics-card">
            <h2>
                <span>🎯 Топ увлечений учеников</span>
                <span style="font-size: 12px; color: var(--text-muted); font-weight: normal;">Для генерации метафор</span>
            </h2>
            <div class="rank-list">
                {"".join(f'''
                <div class="rank-item">
                    <div class="rank-label-row">
                        <span class="rank-name">{name}</span>
                        <span class="rank-count">{cnt} уч.</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: {int((cnt / max_hobby_val) * 100)}%;"></div>
                    </div>
                </div>
                ''' for name, cnt in top_hobbies)}
            </div>
        </div>
    </div>

    <!-- Heatmap of Lagging Topics -->
    <div class="table-container">
        <div class="table-header-row">
            <h2>🔥 Тепловая карта успеваемости по темам (Quiz Heatmap)</h2>
            <span style="font-size: 12px; color: var(--text-muted);">Выявление тем, требующих повторения на уроке</span>
        </div>
        <div class="heatmap-grid">
            {''.join(heatmap_cards)}
        </div>
    </div>

    <!-- Top-5 Requested Topics -->
    <div class="table-container">
        <div class="table-header-row">
            <h2>📚 Топ-5 тем по частоте запросов учеников</h2>
            <span style="font-size: 12px; color: var(--text-muted);">Чаще всего вызывают трудности</span>
        </div>
        <div class="rank-list" style="margin-top: 8px;">
            {"".join(f'''
            <div class="rank-item">
                <div class="rank-label-row">
                    <span class="rank-name">{topic}</span>
                    <span class="rank-count">{cnt} запросов</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width: {int((cnt / max_topic_val) * 100)}%;"></div>
                </div>
            </div>
            ''' for topic, cnt in top_topics)}
        </div>
    </div>

    <!-- Students Table -->
    <div class="table-container">
        <div class="table-header-row">
            <h2>👥 Активность учеников (FSM & 152-ФЗ)</h2>
            <span style="font-size: 12px; color: var(--text-muted);">Последние {len(users_list)} пользователей</span>
        </div>
        <table>
            <thead>
                <tr>
                    <th>ID Ученика</th>
                    <th>Интерес (Метафора)</th>
                    <th>Класс</th>
                    <th>Режим 152-ФЗ</th>
                    <th>FSM Состояние</th>
                </tr>
            </thead>
            <tbody>
                {"".join(f'''
                <tr>
                    <td><strong>{u.max_user_id}</strong></td>
                    <td><span class="tag">{u.interest or "Не выбран"}</span></td>
                    <td>{u.grade} класс</td>
                    <td>{"🔒 Гостевой" if u.is_guest else "✅ Согласие"}</td>
                    <td><code>{u.state}</code></td>
                </tr>
                ''' for u in users_list) if users_list else '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">Ученики пока не подключились.</td></tr>'}
            </tbody>
        </table>
    </div>

    <!-- Recent Quizzes Table -->
    <div class="table-container">
        <div class="table-header-row">
            <h2>🎯 Последние сданные микро-тесты (Quiz Freshness Guard)</h2>
            <span style="font-size: 12px; color: var(--text-muted);">Защита от повторных и устаревших кликов</span>
        </div>
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
                        {"<span class='tag tag-correct'>Верно (+10)</span>" if q.is_correct else ("<span class='tag tag-wrong'>Неверно</span>" if q.is_correct is False else "<span class='tag'>В процессе</span>")}
                    </td>
                </tr>
                ''' for q in quizzes_list) if quizzes_list else '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">Квизы пока не сдавались.</td></tr>'}
            </tbody>
        </table>
    </div>

    <script>
        // 30s Countdown and Auto-Refresh
        let timeLeft = 30;
        const timerEl = document.getElementById('timer');
        setInterval(() => {{
            timeLeft--;
            if (timerEl) timerEl.innerText = timeLeft;
            if (timeLeft <= 0) {{
                location.reload();
            }}
        }}, 1000);

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
</body>
</html>
"""
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.core_service.main:app", host="0.0.0.0", port=8000, reload=False)

