import asyncio
import os
import json
from dotenv import load_dotenv
import traceback

from maxbot.bot import Bot
from maxbot.dispatcher import Dispatcher
from maxbot.types import Message
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

from schemas.events import EventEnvelope

load_dotenv()

TOKEN = os.getenv("MAX_BOT_TOKEN")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_EVENTS", "education.events")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Глобальные переменные для Kafka и очереди
producer = None
consumer_task = None
message_queue = asyncio.Queue() # Очередь для исходящих сообщений
sender_task = None # Фоновая задача для отправки

async def message_sender_worker():
    """
    Фоновый воркер (Throttling).
    Соблюдает лимит MAX API: 30 запросов/сек.
    """
    print("✅ Воркер отправки сообщений запущен (лимит 30 req/sec)")
    while True:
        try:
            # Ждем появления задачи в очереди
            chat_id, text = await message_queue.get()
            
            try:
                # Фактическая отправка
                await bot.send_message(chat_id=int(chat_id), text=text)
            except Exception as e:
                print(f"❌ Ошибка при отправке сообщения пользователю {chat_id}: {e}")
            
            # Строгий throttling: пауза 1/30 секунды (~0.033 сек) перед следующим сообщением
            await asyncio.sleep(1 / 30)
            
            # Отмечаем задачу как выполненную
            message_queue.task_done()
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ Критическая ошибка в воркере отправки: {e}")

async def setup_kafka_producer():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await producer.start()
    print("✅ Kafka Producer успешно запущен")

async def kafka_consumer_worker():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="max-bot-consumer-group",
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset="latest"
    )
    await consumer.start()
    print("✅ Kafka Consumer запущен, ожидаем ответы от ML-сервиса (explanation.ready)...")
    
    try:
        async for msg in consumer:
            event = msg.value
            if event.get("event_type") == "explanation.ready":
                payload = event.get("payload", {})
                user_id = payload.get("max_user_id")
                answer_text = payload.get("text", "Ошибка: Пустой ответ от ML")
                
                if user_id:
                    print(f"📥 Пойман ответ для пользователя {user_id}. Кладу в очередь на отправку...")
                    # Вместо прямой отправки кладем в очередь (Throttling)
                    await message_queue.put((user_id, answer_text))
                    print("✅ Ответ от ML добавлен в очередь!")
    except Exception as e:
        print(f"❌ Критическая ошибка Consumer: {e}")
    finally:
        await consumer.stop()
        
@dp.message()
async def echo_handler(message: Message):
    try:
        user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
        text = getattr(message, 'text', '')
        
        print(f"📩 Получено сообщение от {user_id}: {text}")
        
        event = EventEnvelope(
            event_type="bot.command.received",
            payload={
                "max_user_id": str(user_id),
                "text": text,
                "command": text
            }
        )
        
        if producer:
            await producer.send_and_wait(KAFKA_TOPIC, event.model_dump())
            print(f"📤 Событие отправлено в Kafka: {event.event_id}")
        
        response_text = "Принял запрос! Передаю агентам ML для генерации ответа... 🧠"
        
        # Вместо прямой отправки кладем в очередь (Throttling)
        await message_queue.put((user_id, response_text))
        
    except Exception as e:
        print(f"❌ Ошибка в echo_handler: {e}")
        traceback.print_exc()

async def main():
    print("Запуск бота и инициализация балансировщика...")
    await setup_kafka_producer()
    
    global consumer_task, sender_task
    
    # Запускаем Consumer
    consumer_task = asyncio.create_task(kafka_consumer_worker())
    
    # Запускаем воркер отправки сообщений (Throttling)
    sender_task = asyncio.create_task(message_sender_worker())
    
    try:
        await dp.run_polling()
    finally:
        if producer:
            await producer.stop()
            print("🛑 Kafka Producer остановлен")
        if consumer_task:
            consumer_task.cancel()
        if sender_task:
            sender_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())