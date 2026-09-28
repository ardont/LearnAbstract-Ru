import asyncio
import json
import os
import signal
import traceback
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from maxbot.bot import Bot
from maxbot.dispatcher import Dispatcher
from maxbot.types import Message, Callback
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import httpx
from uvicorn import Config, Server

from services.bot_service.idempotency import is_duplicate_message
from services.bot_service.watchdog import register_watchdog, cancel_watchdog
from services.bot_service.keyboards import (
    get_consent_keyboard,
    get_interests_keyboard,
    get_quiz_keyboard,
    get_after_explanation_keyboard,
    get_profile_keyboard
)
from shared.schemas.events import EventEnvelope
from shared.utils.text_formatter import latex_to_unicode, split_for_max
from shared.utils.logger import setup_logger

load_dotenv()
logger = setup_logger("bot_service.main")

TOKEN = os.getenv("MAX_BOT_TOKEN")
CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "http://localhost:8000")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8002")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_EVENTS = os.getenv("KAFKA_TOPIC_EVENTS", "education.events")

if not TOKEN:
    logger.warning("Переменная MAX_BOT_TOKEN не задана! Проверьте файл .env перед запуском бота.")

bot = Bot(token=TOKEN or "placeholder_token")
dp = Dispatcher(bot)

producer: Optional[AIOKafkaProducer] = None
consumer_task: Optional[asyncio.Task] = None
health_server_task: Optional[asyncio.Task] = None
is_running = True

# Локальное хранилище данных последних сессий пользователей
_user_last_data: Dict[str, Dict[str, Any]] = {}


# --- Вспомогательные функции ---
async def send_message_with_retry(chat_id: int, text: str, reply_markup=None, max_retries: int = 3):
    """Отправка сообщения в MAX бота с повторными попытками при сетевых сбоях."""
    for attempt in range(max_retries):
        try:
            return await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (2 ** attempt))
            else:
                logger.error(f"Ошибка отправки сообщения пользователю {chat_id} (попытка {attempt + 1}/{max_retries}): {e}")


def classify_intent(text: str) -> str:
    """Определяет намерение пользователя: команда, учебный вопрос, отвлечённая беседа или слишком короткий запрос."""
    if not text:
        return "empty"
    t = text.strip()
    if t.startswith("/"):
        return "command"

    lower = t.lower()
    words = t.split()

    # Слишком короткие или неясные одиночные слова (уточнение контекста)
    single_vague_words = ["уравнение", "закон", "формула", "физика", "теорема", "правило", "урок", "задача", "тема"]
    if lower in single_vague_words or (len(words) == 1 and len(t) < 4):
        return "vague"

    # Разговорный оффтоп / смолл-ток
    chitchat = [
        "привет", "здравствуй", "хай", "как дела", "кто ты", "погода", "анекдот",
        "шутка", "курс валют", "сколько время", "ты человек", "спасибо", "пока", "до свидания"
    ]
    if any(k in lower for k in chitchat) and len(words) <= 4:
        return "chitchat"

    # Академические ключевые слова (математика, физика, биология, химия, CS)
    school_keywords = [
        "уравнен", "пифагор", "ом", "закон", "физик", "алгебр", "биолог", "клетк", "фотосинтез",
        "гравитац", "производн", "интеграл", "дроб", "треугольник", "скорост", "ускорен", "сил",
        "вектор", "ток", "напряжен", "сопротивлен", "площад", "периметр", "функци", "график",
        "матриц", "алгоритм", "сортировк", "энерги", "молекул", "атом", "химия", "реакци",
        "электрон", "протон", "нейтрон", "давлен", "плотност", "теплот", "косинус", "синус",
        "тангенс", "гипотенуз", "катет", "дискриминант", "ньютон", "архимед", "паскал",
        "эволюци", "днк", "рнк", "ген", "хромосом", "валентност", "оксид", "кислот", "щелоч"
    ]
    if any(k in lower for k in school_keywords):
        return "educational"

    triggers = ["объясни", "как работ", "что такое", "в чём суть", "в чем суть", "почему", "формул", "теорем", "правил"]
    if any(k in lower for k in triggers):
        return "educational"

    # Если фраза длиннее 2 слов — считаем вопросом к репетитору
    if len(words) >= 2:
        return "educational"

    return "vague"


# --- Health Server (Port 8001) для Docker Compose ---
async def run_health_server():
    from fastapi import FastAPI
    health_app = FastAPI(title="Bot Service Health")

    @health_app.get("/health")
    async def health():
        return {"status": "ok", "service": "bot_service", "bot_configured": bool(TOKEN)}

    config = Config(app=health_app, host="0.0.0.0", port=8001, log_level="warning")
    server = Server(config)
    await server.serve()


# --- Kafka Setup ---
async def setup_kafka():
    global producer
    try:
        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await producer.start()
        logger.info("Kafka Producer для Bot Service запущен.")
    except Exception as e:
        logger.warning(f"Kafka Producer недоступен: {e}. Работа в прямом локальном режиме.")
        producer = None


async def kafka_consumer_worker():
    """Консьюмер для доставки готовых ответов explanation.ready пользователям."""
    global is_running
    try:
        consumer = AIOKafkaConsumer(
            KAFKA_TOPIC_EVENTS,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id="bot_service_group",
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
            auto_offset_reset="latest"
        )
        await consumer.start()
        logger.info("Kafka Consumer запущен. Ожидание ответов explanation.ready...")

        while is_running:
            try:
                msg = await asyncio.wait_for(consumer.getone(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            event = msg.value
            if event.get("event_type") == "explanation.ready":
                corr_id = event.get("correlation_id")
                payload = event.get("payload", {})
                user_id = payload.get("max_user_id")
                text = payload.get("text", "")
                quiz = payload.get("quiz")
                source = payload.get("source", "llm")
                latency_ms = payload.get("latency_ms", 0)
                topic = payload.get("topic", "Тема")

                if user_id:
                    if corr_id:
                        await cancel_watchdog(corr_id)

                    clean_text = latex_to_unicode(text)
                    chunks = split_for_max(clean_text, limit=4000)

                    for chunk in chunks:
                        await send_message_with_retry(chat_id=int(user_id), text=chunk)

                    quiz_id = None
                    if quiz:
                        quiz_id = quiz.get("quiz_id")
                        question = latex_to_unicode(quiz.get("question", ""))
                        options = [latex_to_unicode(opt) for opt in quiz.get("options", [])]

                        # Регистрация в Core Service
                        try:
                            async with httpx.AsyncClient(timeout=3.0) as client:
                                await client.post(
                                    f"{CORE_SERVICE_URL}/api/quiz/register",
                                    json={
                                        "max_user_id": str(user_id),
                                        "quiz_id": quiz_id,
                                        "topic": topic,
                                        "question": question,
                                        "options": options,
                                        "correct_option_index": quiz.get("correct_option_index", 0)
                                    }
                                )
                        except Exception as reg_err:
                            logger.warning(f"Ошибка регистрации квиза в Core Service: {reg_err}")

                        quiz_msg = f"🎯 **Проверь себя (Микро-тест):**\n{question}"
                        kb = get_quiz_keyboard(quiz_id, options)
                        await send_message_with_retry(chat_id=int(user_id), text=quiz_msg, reply_markup=kb)

                    # Сохраняем состояние сессии
                    _user_last_data[str(user_id)] = {
                        "topic": topic,
                        "quiz_id": quiz_id,
                        "quiz": quiz
                    }

                    # Отправляем кнопки действий после объяснения
                    post_kb = get_after_explanation_keyboard(topic=topic, quiz_id=quiz_id or "")
                    await send_message_with_retry(
                        chat_id=int(user_id),
                        text="💡 Что делаем дальше?",
                        reply_markup=post_kb
                    )

                    # Записываем метрику
                    try:
                        async with httpx.AsyncClient(timeout=2.0) as client:
                            await client.post(
                                f"{CORE_SERVICE_URL}/api/metrics/record",
                                json={
                                    "latency_ms": latency_ms,
                                    "source": source,
                                    "max_user_id": str(user_id),
                                    "topic": topic
                                }
                            )
                    except Exception:
                        pass

    except Exception as e:
        logger.warning(f"Ошибка Kafka Consumer: {e}")
    finally:
        if 'consumer' in locals() and consumer:
            await consumer.stop()


# --- Прямой ML Fallback при отсутствии Kafka ---
async def direct_ml_fallback(envelope: EventEnvelope, user_id: int, topic: str, interest: str):
    """Прямой вызов ML Service при отсутствии Kafka (Demo-Resilience)."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{ML_SERVICE_URL}/api/generate",
                json={"topic": topic, "interest": interest, "grade": 7, "user_query": topic}
            )
        if resp.status_code == 200:
            res_data = resp.json()
            await cancel_watchdog(envelope.correlation_id)

            clean_text = latex_to_unicode(res_data.get("text", "") or res_data.get("explanation", ""))
            chunks = split_for_max(clean_text, limit=4000)
            for c in chunks:
                await send_message_with_retry(chat_id=user_id, text=c)

            quiz = res_data.get("quiz")
            quiz_id = None
            if quiz:
                quiz_id = quiz.get("quiz_id") or f"quiz_{int(asyncio.get_event_loop().time())}"
                question = latex_to_unicode(quiz.get("question", ""))
                options = [latex_to_unicode(o) for o in quiz.get("options", [])]

                try:
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        await client.post(
                            f"{CORE_SERVICE_URL}/api/quiz/register",
                            json={
                                "max_user_id": str(user_id),
                                "quiz_id": quiz_id,
                                "topic": topic,
                                "question": question,
                                "options": options,
                                "correct_option_index": quiz.get("correct_option_index", 0)
                            }
                        )
                except Exception:
                    pass

                await send_message_with_retry(
                    chat_id=user_id,
                    text=f"🎯 **Проверь себя (Микро-тест):**\n{question}",
                    reply_markup=get_quiz_keyboard(quiz_id, options)
                )

            _user_last_data[str(user_id)] = {
                "topic": topic,
                "quiz_id": quiz_id,
                "quiz": quiz
            }

            post_kb = get_after_explanation_keyboard(topic=topic, quiz_id=quiz_id or "")
            await send_message_with_retry(
                chat_id=user_id,
                text="💡 Что делаем дальше?",
                reply_markup=post_kb
            )

    except Exception as e:
        logger.error(f"Ошибка direct_ml_fallback: {e}")
        await send_message_with_retry(
            chat_id=user_id,
            text="⚠️ Не удалось получить ответ вовремя. Пожалуйста, попробуй задать вопрос ещё раз."
        )


# --- Обработчики команд и сообщений бота ---
@dp.message()
async def message_handler(message: Message):
    try:
        user_id = message.from_user.id if hasattr(message, "from_user") and message.from_user else message.chat.id
        msg_id = getattr(message, "message_id", None)
        text = (message.text or "").strip()

        # 1. Защита от дублей (Идемпотентность)
        if await is_duplicate_message(str(msg_id) if msg_id else None, str(user_id), text):
            logger.info(f"Игнорирование дубликата сообщения от {user_id}")
            return

        logger.info(f"Получено сообщение от {user_id}: {text}")

        # 2. Меню-команды
        if text.startswith("/start"):
            welcome = (
                "👋 Привет! Я — **«Абстрактный Репетитор» (v6.0)**.\n\n"
                "Я помогаю понимать сложные школьные темы (математику, физику, биологию, информатику) "
                "через то, что тебе по-настоящему близко: **спорт, видеоигры, музыку, космос и кино**!\n\n"
                "🔒 *Согласно 152-ФЗ, для сохранения прогресса и квизов мы запрашиваем согласие на обработку данных. "
                "Ты также можешь выбрать Гостевой режим (без сохранения персональных данных).*"
            )
            await send_message_with_retry(chat_id=int(user_id), text=welcome, reply_markup=get_consent_keyboard())
            return

        if text.startswith("/help"):
            help_text = (
                "📖 **Справка по командам бота:**\n\n"
                "• **/start** — перезапуск бота и выбор режима 152-ФЗ\n"
                "• **/help** — эта справка\n"
                "• **/hobby** (или **/interest**) — выбор сферы увлечений (Футбол, Видеоигры, Музыка, Космос, Кино, Кругозор)\n"
                "• **/quiz** — пройти проверочный тест по текущей теме\n"
                "• **/profile** — твой класс, баллы, точность ответов и статистика\n"
                "• **/reset** — сбросить профиль и начать заново\n\n"
                "💡 **Как задать вопрос:**\n"
                "Просто напиши школьную тему своими словами:\n"
                "• *«Объясни закон Ома»*\n"
                "• *«В чём суть теоремы Пифагора?»*\n"
                "• *«Как работает фотосинтез?»*\n"
                "• *«Что такое квадратные уравнения?»*"
            )
            await send_message_with_retry(chat_id=int(user_id), text=help_text)
            return

        if text.startswith("/hobby") or text.startswith("/interest"):
            await send_message_with_retry(
                chat_id=int(user_id),
                text="🎯 Выбери сферу увлечений для построения ярких аналогий:",
                reply_markup=get_interests_keyboard()
            )
            return

        if text.startswith("/profile"):
            await show_user_profile(int(user_id))
            return

        if text.startswith("/reset"):
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.post(
                    f"{CORE_SERVICE_URL}/api/user/reset",
                    json={"max_user_id": str(user_id)}
                )
            await send_message_with_retry(
                chat_id=int(user_id),
                text="🔄 Твой профиль сброшен. Давай настроим бота заново!",
                reply_markup=get_consent_keyboard()
            )
            return

        if text.startswith("/quiz"):
            last_data = _user_last_data.get(str(user_id))
            if last_data and last_data.get("quiz"):
                q = last_data["quiz"]
                quiz_id = last_data["quiz_id"]
                options = [latex_to_unicode(o) for o in q.get("options", [])]
                await send_message_with_retry(
                    chat_id=int(user_id),
                    text=f"🎯 **Тест по теме «{last_data.get('topic', 'Тема')}»:**\n{latex_to_unicode(q.get('question', ''))}",
                    reply_markup=get_quiz_keyboard(quiz_id, options)
                )
            else:
                await send_message_with_retry(
                    chat_id=int(user_id),
                    text="ℹ️ У тебя пока нет активного теста. Задай мне любой вопрос по школьной программе, и я составлю проверочный тест после объяснения!"
                )
            return

        # 3. Анализ намерения (Intent Detection)
        intent = classify_intent(text)

        if intent == "chitchat":
            chitchat_reply = (
                "👋 Привет! Я — ИИ-репетитор по школьным предметам.\n\n"
                "Я умею объяснять сложные темы по математике, физике, информатике и биологии "
                "через спорт, игры, космос и музыку!\n\n"
                "💡 **Попробуй спросить меня:**\n"
                "• *«Объясни теорему Пифагора»*\n"
                "• *«Закон Ома через игры»*\n"
                "• *«Как устроен фотосинтез?»*\n"
                "• *«Что такое гравитация?»*"
            )
            await send_message_with_retry(chat_id=int(user_id), text=chitchat_reply)
            return

        if intent == "vague":
            vague_reply = (
                f"💡 Ты написал короткий запрос: «**{text}**».\n\n"
                "Пожалуйста, уточни вопрос подробнее, чтобы я подобрал точную метафору:\n"
                "• *«Объясни квадратные уравнения»*\n"
                "• *«Закон Ома для участка цепи»*\n"
                "• *«Теорема Пифагора с доказательством»*"
            )
            await send_message_with_retry(chat_id=int(user_id), text=vague_reply)
            return

        # 4. Маршрутизация через Core Service FSM
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                f"{CORE_SERVICE_URL}/api/user/message",
                json={"max_user_id": str(user_id), "text": text}
            )

        if resp.status_code == 200:
            data = resp.json()
            action = data.get("action")

            if action == "rate_limited":
                await send_message_with_retry(chat_id=int(user_id), text=data.get("message"))
                return

            if action == "ask_consent":
                await send_message_with_retry(
                    chat_id=int(user_id),
                    text=data.get("message"),
                    reply_markup=get_consent_keyboard()
                )
                return

            if action == "select_interest":
                await send_message_with_retry(
                    chat_id=int(user_id),
                    text=data.get("message"),
                    reply_markup=get_interests_keyboard()
                )
                return

            if action == "wait_quiz":
                await send_message_with_retry(chat_id=int(user_id), text=data.get("message"))
                return

            if action == "request_explanation":
                envelope = EventEnvelope(
                    event_type="explanation.requested",
                    producer="bot_service",
                    payload={
                        "max_user_id": str(user_id),
                        "topic": text,
                        "interest": data.get("interest", "Футбол"),
                        "grade": data.get("grade", 7),
                        "is_guest": data.get("is_guest", False),
                        "subject": data.get("subject", "algebra"),
                        "user_query": text
                    }
                )

                await register_watchdog(envelope.correlation_id, int(user_id), bot, timeout_sec=45)

                await send_message_with_retry(
                    chat_id=int(user_id),
                    text=f"🧠 Отличная тема! Строю метафору через сферу «{data.get('interest')}»..."
                )

                if producer:
                    await producer.send_and_wait(KAFKA_TOPIC_EVENTS, envelope.model_dump())
                else:
                    asyncio.create_task(direct_ml_fallback(envelope, int(user_id), text, data.get("interest", "Футбол")))

    except Exception as e:
        logger.error(f"Ошибка в message_handler: {e}")
        traceback.print_exc()


async def show_user_profile(user_id: int):
    """Отображение профиля ученика и статистики."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{CORE_SERVICE_URL}/api/user/profile/{user_id}")
        if resp.status_code == 200:
            prof = resp.json().get("profile", {})
            profile_text = (
                "👤 **Твой профиль в «Абстрактном Репетиторе»:**\n\n"
                f"• **Любимое увлечение:** {prof.get('interest', 'Не выбрано')}\n"
                f"• **Класс обучения:** {prof.get('grade', 7)} класс\n"
                f"• **Режим 152-ФЗ:** {'🔒 Гостевой' if prof.get('is_guest') else '✅ Сохранение прогресса'}\n"
                f"• **Пройдено микро-тестов:** {prof.get('total_quizzes', 0)}\n"
                f"• **Правильных ответов:** {prof.get('correct_quizzes', 0)} ({prof.get('success_rate_pct', 0)}%)\n"
                f"• **Баллы опыта:** 🌟 **{prof.get('points', 0)} XP**\n"
            )
            await send_message_with_retry(chat_id=user_id, text=profile_text, reply_markup=get_profile_keyboard())
            return
    except Exception as e:
        logger.warning(f"Ошибка получения профиля: {e}")

    await send_message_with_retry(
        chat_id=user_id,
        text="👤 Профиль: 7 класс. Для выбора хобби нажми /hobby.",
        reply_markup=get_profile_keyboard()
    )


# --- Обработчик нажатий на Inline-кнопки ---
@dp.callback()
async def callback_handler(callback: Callback):
    try:
        user_id = callback.user.id
        data = callback.payload
        logger.info(f"Callback от {user_id}: {data}")

        # О проекте
        if data == "about_project":
            about_text = (
                "ℹ️ **О проекте «Твой Путь: Абстрактный Репетитор» (v6.0):**\n\n"
                "🎓 **Цель:** помочь школьникам легко и с интересом осваивать сложные понятия школьной программы.\n\n"
                "✨ **Ключевые возможности:**\n"
                "• **Метафоры по интересам:** формулы через футбол, игры, космос, музыку и кино.\n"
                "• **RAG по учебникам:** извлечение точных формул и определений с номерами страниц.\n"
                "• **100 проверенных метафор:** 20 ключевых тем × 5 увлечений в локальном каталоге.\n"
                "• **Quiz Freshness Guard:** моментальные интерактивные тесты с защитой от повторных кликов.\n"
                "• **152-ФЗ:** полное соответствие законодательству РФ с поддержкой гостевого режима."
            )
            await send_message_with_retry(chat_id=int(user_id), text=about_text, reply_markup=get_consent_keyboard())
            return

        # Действия после объяснения
        if data == "action_profile":
            await show_user_profile(int(user_id))
            return

        if data == "cmd_hobby":
            await send_message_with_retry(
                chat_id=int(user_id),
                text="🎯 Выбери сферу увлечений для построения ярких аналогий:",
                reply_markup=get_interests_keyboard()
            )
            return

        if data == "cmd_reset":
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.post(
                    f"{CORE_SERVICE_URL}/api/user/reset",
                    json={"max_user_id": str(user_id)}
                )
            await send_message_with_retry(
                chat_id=int(user_id),
                text="🔄 Профиль сброшен. Давай настроим бота заново!",
                reply_markup=get_consent_keyboard()
            )
            return

        if data.startswith("remetaphor_"):
            topic = data.replace("remetaphor_", "")
            if topic == "last":
                last_data = _user_last_data.get(str(user_id), {})
                topic = last_data.get("topic", "Квадратные уравнения")
            await send_message_with_retry(
                chat_id=int(user_id),
                text=f"🔄 Подбираю другую метафору для темы «**{topic}**»..."
            )
            # Запускаем генерацию новой метафоры
            envelope = EventEnvelope(
                event_type="explanation.requested",
                producer="bot_service",
                payload={
                    "max_user_id": str(user_id),
                    "topic": topic,
                    "interest": "Видеоигры",
                    "grade": 7,
                    "is_guest": False,
                    "subject": "algebra",
                    "user_query": topic
                }
            )
            await register_watchdog(envelope.correlation_id, int(user_id), bot, timeout_sec=45)
            if producer:
                await producer.send_and_wait(KAFKA_TOPIC_EVENTS, envelope.model_dump())
            else:
                asyncio.create_task(direct_ml_fallback(envelope, int(user_id), topic, "Видеоигры"))
            return

        # 1. Согласие 152-ФЗ
        if data in ("consent_accept", "consent_decline"):
            accepted = (data == "consent_accept")
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.post(
                    f"{CORE_SERVICE_URL}/api/user/consent",
                    json={"max_user_id": str(user_id), "accepted": accepted}
                )

            msg = (
                "✅ Согласие принято! Профиль сохранён."
                if accepted else
                "🔒 Активирован гостевой режим. Твои данные не будут сохраняться в базу данных."
            )
            await send_message_with_retry(chat_id=int(user_id), text=msg)
            await send_message_with_retry(
                chat_id=int(user_id),
                text="Теперь выбери сферу интересов для объяснения аналогий:",
                reply_markup=get_interests_keyboard()
            )
            return

        # 2. Выбор сферы интересов
        if data.startswith("interest_"):
            interest = data.replace("interest_", "")
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.post(
                    f"{CORE_SERVICE_URL}/api/user/interest",
                    json={"max_user_id": str(user_id), "interest": interest}
                )
            confirm_msg = (
                f"🎉 Отлично! Выбрана сфера: **{interest}**.\n\n"
                "Задай мне любой вопрос по школьной программе! Например:\n"
                "• *«Объясни закон Ома»*\n"
                "• *«Что такое квадратные уравнения?»*\n"
                "• *«Как работает гравитация?»*"
            )
            await send_message_with_retry(chat_id=int(user_id), text=confirm_msg)
            return

        # 3. Ответ на квиз (Quiz Freshness Guard)
        if data.startswith("quiz_"):
            parts = data.split("_")
            if len(parts) >= 3:
                quiz_id = parts[1]
                selected_opt = int(parts[2])

                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.post(
                        f"{CORE_SERVICE_URL}/api/quiz/answer",
                        json={
                            "max_user_id": str(user_id),
                            "quiz_id": quiz_id,
                            "selected_option_index": selected_opt
                        }
                    )

                if resp.status_code == 200:
                    res_json = resp.json()
                    status_flag = res_json.get("status")

                    if status_flag == "stale":
                        await send_message_with_retry(
                            chat_id=int(user_id),
                            text=res_json.get("message", "⚠️ Этот тест уже не активен или был пройден ранее. Вопрос не засчитан.")
                        )
                        return

                    is_corr = res_json.get("is_correct")
                    if is_corr:
                        reply = "🎉 **Абсолютно верно! (+10 очков)** Ты отлично усвоил эту тему!\n\nГотов к новому вопросу — просто напиши его мне."
                    else:
                        reply = "❌ **Не совсем так.** Попробуй перечитать метафору ещё раз!\n\nЗадай следующий вопрос или повтори тему."

                    last_data = _user_last_data.get(str(user_id), {})
                    topic = last_data.get("topic", "")
                    post_kb = get_after_explanation_keyboard(topic=topic, quiz_id="")
                    await send_message_with_retry(chat_id=int(user_id), text=reply, reply_markup=post_kb)

    except Exception as e:
        logger.error(f"Ошибка в callback_handler: {e}")
        traceback.print_exc()


# --- Главная функция запуска сервиса ---
async def main():
    global consumer_task, health_server_task, is_running
    logger.info("Запуск Bot Service...")

    health_server_task = asyncio.create_task(run_health_server())
    await setup_kafka()
    consumer_task = asyncio.create_task(kafka_consumer_worker())

    def handle_signal(sig, frame):
        global is_running
        logger.info(f"Bot Service получил сигнал {sig}. Запуск Graceful Shutdown...")
        is_running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        logger.info("Запуск Telegram/MAX polling...")
        await dp.run_polling()
    finally:
        is_running = False
        if producer:
            await producer.stop()
        if consumer_task:
            consumer_task.cancel()
        if health_server_task:
            health_server_task.cancel()
        logger.info("Bot Service корректно остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
