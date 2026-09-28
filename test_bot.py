import asyncio
import os
import json
from dotenv import load_dotenv
import traceback
import httpx

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
message_queue = asyncio.Queue() 
sender_task = None 

# === ХАКАТОНСКАЯ МАГИЯ 3.0: ГЛОБАЛЬНЫЙ ПЕРЕХВАТЧИК СЕТИ ===
original_request = httpx.AsyncClient.request

async def patched_request(self, method, url, **kwargs):
    response = await original_request(self, method, url, **kwargs)
    try:
        await response.aread()
        text_data = response.text
        
        if "message_callback" in text_data or "consent_" in text_data:
            data = json.loads(text_data)
            
            for u in data.get("updates", []):
                if u.get("update_type") == "message_callback" or "callback" in u:
                    cb_data = u.get("callback", {})
                    payload = cb_data.get("payload")
                    
                    # 💡 ДОСТАЕМ ПРАВИЛЬНЫЙ ID ЧАТА ИЗ ЛОГОВ MAX
                    chat_id = u.get("message", {}).get("recipient", {}).get("chat_id")
                    
                    # Фолбэк на user_id, если chat_id вдруг пустой
                    target_id = chat_id or cb_data.get("user", {}).get("user_id")
                    
                    if target_id and payload:
                        print(f"\n🔘 [СЕТЬ] Пойман клик! Chat ID: {target_id}, Выбор: {payload}")
                        
                        if payload == "consent_accept":
                            response_text = "🎉 Спасибо! Полный профиль активирован. Твой прогресс будет сохраняться."
                        elif payload == "consent_decline":
                            response_text = "👻 Режим гостя активирован. Прогресс сохраняться не будет."
                        else:
                            response_text = f"Получен выбор: {payload}"
                        
                        event = EventEnvelope(
                            event_type="bot.command.received",
                            payload={
                                "max_user_id": str(target_id),
                                "text": payload,
                                "command": payload
                            }
                        )
                        if producer:
                            await producer.send_and_wait(KAFKA_TOPIC, event.model_dump())
                            print(f"📤 Событие выбора отправлено в Kafka")
                        
                        # Теперь мы отправляем сообщение в правильный chat_id!
                        await message_queue.put({"chat_id": int(target_id), "text": response_text})
    except Exception:
        pass
    return response
# Внедряем патч в ядро библиотеки
httpx.AsyncClient.request = patched_request
# ==========================================================

async def message_sender_worker():
    print("✅ Воркер отправки сообщений запущен (лимит 30 req/sec)")
    while True:
        try:
            task = await message_queue.get()
            try:
                if isinstance(task, dict):
                    await bot.send_message(**task)
                else:
                    chat_id, text = task
                    await bot.send_message(chat_id=int(chat_id), text=text)
            except Exception as e:
                print(f"❌ Ошибка при отправке сообщения: {e}")
            
            await asyncio.sleep(1 / 30)
            message_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ Критическая ошибка в воркере: {e}")

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
    print("✅ Kafka Consumer запущен, ожидаем ответы от ML-сервиса...")
    
    try:
        async for msg in consumer:
            event = msg.value
            if event.get("event_type") == "explanation.ready":
                payload = event.get("payload", {})
                user_id = payload.get("max_user_id")
                answer_text = payload.get("text", "Ошибка: Пустой ответ от ML")
                
                if user_id:
                    print(f"📥 Пойман ответ для {user_id}. Кладу в очередь на отправку...")
                    await message_queue.put({"chat_id": int(user_id), "text": answer_text})
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
        await message_queue.put({"chat_id": int(user_id), "text": response_text})
        
    except Exception as e:
        print(f"❌ Ошибка в echo_handler: {e}")
        traceback.print_exc()

async def main():
    print("Запуск бота и инициализация балансировщика...")
    await setup_kafka_producer()
    
    global consumer_task, sender_task
    consumer_task = asyncio.create_task(kafka_consumer_worker())
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