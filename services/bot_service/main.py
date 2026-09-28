import asyncio
import json
import os
import signal
import traceback
from typing import Optional

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
    get_after_explanation_keyboard
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

# Локальное хранилище последнего сгенерированного квиза для быстрого ответа
_pending_quizzes = {}


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

                if user_id:
                    # Отменяем Watchdog таймер
                    if corr_id:
                        await cancel_watchdog(corr_id)

                    # Форматируем и аккуратно разбиваем сообщение под лимит MAX (4000 симв.)
                    clean_text = latex_to_unicode(text)
                    chunks = split_for_max(clean_text, limit=4000)

                    for chunk in chunks:
                        await bot.send_message(chat_id=int(user_id), text=chunk)

                    # Если сгенерирован квиз — регистрируем и отправляем кнопки
                    if quiz:
                        quiz_id = quiz.get("quiz_id")
                        question = latex_to_unicode(quiz.get("question", ""))
                        options = [latex_to_unicode(opt) for opt in quiz.get("options", [])]

                        # Регистрируем в Core Service
                        try:
                            async with httpx.AsyncClient(timeout=3.0) as client:
                                await client.post(
                                    f"{CORE_SERVICE_URL}/api/quiz/register",
                                    json={
                                        "max_user_id": str(user_id),
                                        "quiz_id": quiz_id,
                                        "topic": quiz.get("topic", "Тема"),
                                        "question": question,
                                        "options": options,
                                        "correct_option_index": quiz.get("correct_option_index", 0)
                                    }
                                )
                        except Exception as reg_err:
                            logger.warning(f"Ошибка регистрации квиза в Core Service: {reg_err}")

                        quiz_msg = f"🎯 **Проверь себя:**\n{question}"
                        kb = get_quiz_keyboard(quiz_id, options)
                        await bot.send_message(chat_id=int(user_id), text=quiz_msg, reply_markup=kb)

                    # Записываем метрику
                    try:
                        async with httpx.AsyncClient(timeout=2.0) as client:
                            await client.post(
                                f"{CORE_SERVICE_URL}/api/metrics/record",
                                json={
                                    "latency_ms": latency_ms,
                                    "source": source,
                                    "max_user_id": str(user_id),
                                    "topic": payload.get("topic")
                                }
                            )
                    except Exception:
                        pass

    except Exception as e:
        logger.warning(f"Ошибка Kafka Consumer: {e}")
    finally:
        if 'consumer' in locals() and consumer:
            await consumer.stop()


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

        # 2. Обработка базовых команд
        if text.startswith("/start"):
            welcome = (
                "👋 Привет! Я — **«Абстрактный Репетитор»**.\n\n"
                "Я помогаю понимать сложные школьные темы (математику, физику, химию, программирование) "
                "через то, что тебе по-настоящему близко: **спорт, видеоигры, музыку, космос и кино**!\n\n"
                "🔒 *Согласно 152-ФЗ, для сохранения прогресса и квизов мы запрашиваем согласие на обработку данных. "
                "Ты также можешь выбрать Гостевой режим (без сохранения персональных данных).*"
            )
            await bot.send_message(chat_id=int(user_id), text=welcome, reply_markup=get_consent_keyboard())
            return

        if text.startswith("/help"):
            help_text = (
                "📖 **Как пользоваться репетитором:**\n\n"
                "1. Выбери сферу интересов через команду /interest.\n"
                "2. Напиши тему, которую не понял в школе (например: *«Что такое гравитация?»*, *«Объясни теорему Пифагора»*).\n"
                "3. Получи яркую метафору и ответь на короткий проверочный квиз!\n"
                "4. Проверить свой статус можно командой /profile."
            )
            await bot.send_message(chat_id=int(user_id), text=help_text)
            return

        if text.startswith("/interest"):
            await bot.send_message(
                chat_id=int(user_id),
                text="Выбери сферу интересов для построения аналогий:",
                reply_markup=get_interests_keyboard()
            )
            return

        # 3. Маршрутизация через Core Service FSM
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                f"{CORE_SERVICE_URL}/api/user/message",
                json={"max_user_id": str(user_id), "text": text}
            )

        if resp.status_code == 200:
            data = resp.json()
            action = data.get("action")

            if action == "rate_limited":
                await bot.send_message(chat_id=int(user_id), text=data.get("message"))
                return

            if action == "ask_consent":
                await bot.send_message(
                    chat_id=int(user_id),
                    text=data.get("message"),
                    reply_markup=get_consent_keyboard()
                )
                return

            if action == "select_interest":
                await bot.send_message(
                    chat_id=int(user_id),
                    text=data.get("message"),
                    reply_markup=get_interests_keyboard()
                )
                return

            if action == "wait_quiz":
                await bot.send_message(chat_id=int(user_id), text=data.get("message"))
                return

            if action == "request_explanation":
                # Запускаем Watchdog таймер (45 сек)
                envelope = EventEnvelope(
                    event_type="explanation.requested",
                    producer="bot_service",
                    payload={
                        "max_user_id": str(user_id),
                        "topic": text,
                        "interest": data.get("interest", "Футбол"),
                        "grade": data.get("grade", 7),
                        "is_guest": data.get("is_guest", False)
                    }
                )

                await register_watchdog(envelope.correlation_id, int(user_id), bot, timeout_sec=45)

                # Отправляем подтверждение пользователю
                await bot.send_message(
                    chat_id=int(user_id),
                    text=f"🧠 Отличная тема! Строю метафору через сферу «{data.get('interest')}»..."
                )

                # Передаем в Kafka (или вызываем напрямую ML Service при отсутствии брокера)
                if producer:
                    await producer.send_and_wait(KAFKA_TOPIC_EVENTS, envelope.model_dump())
                else:
                    # Прямой локальный вызов ML Service (Fallback для автономного запуска)
                    asyncio.create_task(direct_ml_fallback(envelope, int(user_id), text, data.get("interest", "Футбол")))

    except Exception as e:
        logger.error(f"Ошибка в message_handler: {e}")
        traceback.print_exc()


async def direct_ml_fallback(envelope: EventEnvelope, user_id: int, topic: str, interest: str):
    """Прямой вызов ML Service при отсутствии Kafka (Demo-Resilience)."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"{ML_SERVICE_URL}/api/generate",
                json={"topic": topic, "interest": interest, "grade": 7}
            )
        if resp.status_code == 200:
            res_data = resp.json()
            await cancel_watchdog(envelope.correlation_id)

            clean_text = latex_to_unicode(res_data.get("text", ""))
            chunks = split_for_max(clean_text, limit=4000)
            for c in chunks:
                await bot.send_message(chat_id=user_id, text=c)

            quiz = res_data.get("quiz")
            if quiz:
                quiz_id = quiz.get("quiz_id")
                question = latex_to_unicode(quiz.get("question", ""))
                options = [latex_to_unicode(o) for o in quiz.get("options", [])]

                # Регистрация квиза
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

                await bot.send_message(
                    chat_id=user_id,
                    text=f"🎯 **Проверь себя:**\n{question}",
                    reply_markup=get_quiz_keyboard(quiz_id, options)
                )
    except Exception as e:
        logger.error(f"Ошибка direct_ml_fallback: {e}")


# --- Обработчик нажатий на Inline-кнопки ---
@dp.callback()
async def callback_handler(callback: Callback):
    try:
        user_id = callback.user.id
        data = callback.payload
        logger.info(f"Callback от {user_id}: {data}")

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
            await bot.send_message(chat_id=int(user_id), text=msg)
            await bot.send_message(
                chat_id=int(user_id),
                text="Теперь выбери сферу интересов для объяснения аналогий:",
                reply_markup=get_interests_keyboard()
            )
            return

        # 2. Выбор сферы интересов
        if data.startswith("interest_"):
            interest = data.replace("interest_", "")
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(
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
            await bot.send_message(chat_id=int(user_id), text=confirm_msg)
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
                        await bot.send_message(
                            chat_id=int(user_id),
                            text=res_json.get("message", "⚠️ Этот тест уже не активен.")
                        )
                        return

                    is_corr = res_json.get("is_correct")
                    if is_corr:
                        reply = "🎉 **Абсолютно верно!** Ты отлично усвоил эту тему!\n\nГотов к новому вопросу — просто напиши его мне."
                    else:
                        reply = "❌ **Не совсем так.** Но ничего страшного, на ошибках учатся!\n\nЗадай следующий вопрос или повтори тему."

                    await bot.send_message(chat_id=int(user_id), text=reply)

    except Exception as e:
        logger.error(f"Ошибка в callback_handler: {e}")
        traceback.print_exc()


# --- Главная функция запуска сервиса ---
async def main():
    global consumer_task, health_server_task, is_running
    logger.info("Запуск Bot Service...")

    # 1. Запуск сервера /health на порту 8001
    health_server_task = asyncio.create_task(run_health_server())

    # 2. Подключение к Kafka
    await setup_kafka()
    consumer_task = asyncio.create_task(kafka_consumer_worker())

    # Graceful shutdown handler
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
