import asyncio
import json
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from schemas.events import EventEnvelope

async def main():
    print("🚀 Запуск Mock ML Service...")
    
    # Настраиваем консьюмер для чтения запросов
    consumer = AIOKafkaConsumer(
        "education.events",
        bootstrap_servers="localhost:9092",
        group_id="mock-ml-group",
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    # Настраиваем продюсер для отправки ответов
    producer = AIOKafkaProducer(
        bootstrap_servers="localhost:9092",
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    await consumer.start()
    await producer.start()
    print("✅ Имитатор ML-сервиса готов. Жду события bot.command.received...")

    try:
        async for msg in consumer:
            event = msg.value
            
            # Ловим только новые запросы от пользователей
            if event.get("event_type") == "bot.command.received":
                payload = event.get("payload", {})
                user_id = payload.get("max_user_id")
                text = payload.get("text", "")
                
                print(f"\n📥 ML-сервис получил вопрос от {user_id}: {text}")
                print("⏳ Генерирую ответ (имитация задержки 2 сек)...")
                await asyncio.sleep(2) 
                
                # Формируем ответ строго по контракту хакатона
                reply_event = EventEnvelope(
                    event_type="explanation.ready",
                    payload={
                        "max_user_id": user_id,
                        "text": f"🤖 [ML Mock Ответ]: Вы спросили «{text}». Вот моё сгенерированное объяснение!"
                    }
                )
                
                await producer.send_and_wait("education.events", reply_event.model_dump())
                print(f"📤 Ответ explanation.ready отправлен обратно в Kafka!")
                
    finally:
        await consumer.stop()
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(main())