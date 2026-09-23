import asyncio
import os
import json
from dotenv import load_dotenv

from maxbot.bot import Bot
from maxbot.dispatcher import Dispatcher
from maxbot.types import Message
from aiokafka import AIOKafkaProducer

from schemas.events import EventEnvelope

load_dotenv()

TOKEN = os.getenv("MAX_BOT_TOKEN")
# Берем адрес Kafka из .env или используем дефолтный localhost
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
# В архитектуре хакатона для MVP предложено использовать education.events
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_EVENTS", "education.events")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Глобальная переменная для продюсера
producer = None

async def setup_kafka():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await producer.start()
    print("✅ Kafka Producer успешно запущен")

@dp.message()
async def echo_handler(message: Message):
    user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
    text = message.text
    
    print(f"📩 Получено сообщение от {user_id}: {text}")
    
    # 1. Формируем событие по контракту
    event = EventEnvelope(
        event_type="bot.command.received",
        payload={
            "max_user_id": str(user_id),
            "text": text,
            "command": text # Для MVP пока считаем весь текст командой
        }
    )
    
    # 2. Отправляем в Kafka
    if producer:
        await producer.send_and_wait(KAFKA_TOPIC, event.model_dump())
        print(f"📤 Событие отправлено в Kafka: {event.event_id}")
    
    # 3. Отвечаем пользователю, что запрос принят
    response_text = "Принял запрос! Передаю агентам ML для генерации ответа... 🧠"
    if hasattr(message, 'answer'):
        await message.answer(response_text)
    else:
        await bot.send_message(chat_id=user_id, text=response_text)

async def main():
    print("Запуск бота и подключение к Kafka...")
    await setup_kafka()
    
    try:
        await dp.run_polling()
    finally:
        if producer:
            await producer.stop()
            print("Kafka Producer остановлен")

if __name__ == "__main__":
    asyncio.run(main())