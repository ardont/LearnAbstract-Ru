# ⚡ Глава 6: Шина сообщений Apache Kafka (KRaft)
[⬅️ Глава 5: Bot Service](./05_bot_service_and_max.md) · [Оглавление](./README.md) · [Вперед: Хранилища данных ➡️](./07_data_storage_pg_redis.md)

---

## 1. Архитектура шины событий в режиме KRaft

В платформе «Твой Путь» в качестве шины сообщений используется **Apache Kafka версии 3.7.0**, запущенная в современном режиме **KRaft (Kafka Raft Metadata Mode)** без устаревшего внешнего координатора Apache ZooKeeper.

```
                   ┌──────────────────────────────────────┐
                   │    Apache Kafka 3.7.0 (KRaft Node)   │
                   │    Node ID: 1, Quorum: Broker+Controller│
                   └──────────────────┬───────────────────┘
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
  ┌────────────────────────┐                    ┌────────────────────────┐
  │ Топик: education.events│                    │ Топик: ...events.dlq   │
  │ (Основной шинный обмен)│                    │ (Dead Letter Queue)    │
  └────────────┬───────────┘                    └────────────────────────┘
               │
    ┌──────────┼──────────────────────┐
    │          │                      │
    ▼          ▼                      ▼
┌────────┐ ┌────────┐           ┌────────┐
│Group:  │ │Group:  │           │Group:  │
│bot_serv│ │core_ser│           │ml_serv │
└────────┘ └────────┘           └────────┘
```

### Преимущества архитектуры KRaft:
1. **Отсутствие ZooKeeper**: Управление кворумом метаданных выполняется внутри самой Kafka через специализированный Raft-консенсус (порт контроллера `9093`).
2. **Мгновенный холодный старт**: Брокер готов к приему сообщений за 5–8 секунд (вместо 35–50 секунд в связке с ZooKeeper), что критично при хакатонных перезапусках и CI/CD тестах.
3. **Строгая консистентность метаданных**: Изменения топиков и партиций фиксируются в виде журнального лога внутри брокера, исключая рассинхронизацию состояния между ZooKeeper и брокерами.

---

## 2. Конфигурация брокера и топиков (`docker-compose.yml`)

В `docker-compose.yml` описан брокер и легковесный контейнер инициализации `kafka-init`:

```yaml
services:
  kafka:
    image: apache/kafka:3.7.0
    container_name: abstractway-kafka
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
    healthcheck:
      test: ["CMD", "/opt/kafka/bin/kafka-broker-api-versions.sh", "--bootstrap-server", "localhost:9092"]
      interval: 10s
      timeout: 5s
      retries: 10
```

### Контейнер `kafka-init`:
Контейнер стартует только после прохождения healthcheck основного брокера (`condition: service_healthy`) и гарантирует создание двух системных топиков с флагом `--if-not-exists`:
* **`education.events`** — основной поток учебных событий.
* **`education.events.dlq`** — очередь недоставленных и аварийных сообщений (Dead Letter Queue).

---

## 3. Сквозной контракт событий: `EventEnvelope` (`events.py`)

Все сервисы взаимодействуют по строго типизированному контракту `EventEnvelope` (`shared/schemas/events.py`):

```python
class EventEnvelope(BaseModel):
    """Единый формат события архитектуры v5.0/v6.0."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    version: str = "1.0"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: Optional[str] = None
    producer: str = "unknown"
    payload: Dict[str, Any]
```

### Семантика ключевых полей:
* **`correlation_id`**: Единый ID запроса от момента нажатия кнопки школьником до отправки ответа. Проходит через все сервисы без изменений. Позволяет выполнить мгновенный grep или запрос в ELK:
  ```bash
  grep "c71a39f0-2f91-4d32-9c12-3498b5a034f1" /logs/*.log
  ```
* **`causation_id`**: Указывает на `event_id` родительского события, породившего текущее действие (например, `explanation.requested` ссылается на `event_id` от `bot.command.received`).

### Каталог типов событий (`event_type`):
| Тип события | Продюсер | Консьюмер | Назначение |
| :--- | :--- | :--- | :--- |
| `bot.command.received` | `bot_service` | `core_service` | Входящее текстовое сообщение или команда ученика |
| `explanation.requested`| `core_service`| `ml_service` | Обогащенный запрос на метафору (с интересом и классом из БД) |
| `explanation.ready`    | `ml_service`  | `bot_service`, `core_service` | Готовое объяснение с микро-квизом и замеренной задержкой |
| `quiz.answered`        | `core_service`| Аналитика | Факт прохождения теста и начисления XP |
| `dead_letter`          | Любой сервис | `DLQ Inspector` | Аварийный пакет с трейсбеком ошибки |

---

## 4. Гарантии доставки: At-Least-Once и ручной коммит офсетов

Во всех воркерах (`services/core_service/main.py`, `services/ml_service/main.py`) **отключен автоматический коммит офсетов**:
```python
consumer = AIOKafkaConsumer(
    KAFKA_TOPIC_EVENTS,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id="ml_service_group",
    enable_auto_commit=False,  # РУЧНОЙ КОММИТ
    auto_offset_reset="latest",
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)
```

### Почему ручной коммит критически важен:
1. **При автокоммите (`enable_auto_commit=True`)**: Kafka фиксирует смещение сразу при получении сообщения из сети. Если в процессе инференса LLM воркер аварийно упал (OOM, сбой питания), сообщение считается прочитанным и **безвозвратно теряется**. Ученик зависает в ожидании навсегда.
2. **При ручном коммите (`enable_auto_commit=False`)**:
   ```python
   # 1. Читаем событие
   msg = await consumer.getone()
   # 2. Выполняем бизнес-логику (RAG + LLM + Fallback)
   result = await generate_explanation(...)
   # 3. Публикуем результат в Kafka
   await producer.send_and_wait(KAFKA_TOPIC_EVENTS, reply.model_dump())
   # 4. ТОЛЬКО ТЕПЕРЬ подтверждаем обработку!
   await consumer.commit()
   ```
   Если сервис падает на шаге 2, после перезапуска контейнера сообщение вычитывается заново и обрабатывается.

---

## 5. Изоляция сбоев: Dead Letter Queue (`dlq.py`)

Если сообщение повреждено (битый JSON, некорректная схема, внутренняя ошибка), бесконечные повторные попытки заблокировали бы очередь («Poison Pill Attack»).

Для безопасного перехвата таких сообщений реализован модуль `services/ml_service/dlq.py`:

```python
async def send_to_dlq(
    producer: AIOKafkaProducer,
    original_event: Dict[str, Any],
    error: str,
    stack_trace: str,
    service: str
):
    dlq_payload = DLQPayload(
        original_event=original_event,
        error=str(error),
        stack_trace=stack_trace,
        service=service
    )
    envelope = EventEnvelope(
        event_type="dead_letter",
        producer=service,
        payload=dlq_payload.model_dump()
    )
    await producer.send_and_wait("education.events.dlq", envelope.model_dump())
    logger.error(f"Событие отправлено в DLQ ({service}): {error}")
```

### Регламент работы с DLQ:
1. Воркер перехватывает исключение в блоке `try ... except`.
2. Событие вместе с полным Python Traceback упаковывается в `DLQPayload` и отправляется в `education.events.dlq`.
3. Офсет в основном топике коммитится, и консьюмер безопасно переходит к следующему запросу.
4. Очередь не зависает, а инженеры могут изучить инцидент через мониторинг.

---

## 6. Consumer Groups и независимое чтение

Каждый сервис подключается со своим уникальным `group_id`:
* `core_service_group`
* `ml_service_group`
* `bot_service_group`

Благодаря модели Publish/Subscribe событие `explanation.ready` читается **одновременно двумя сервисами параллельно**:
* `bot_service`: отправляет текст и кнопки теста в чат MAX.
* `core_service`: сохраняет статистику задержки (`latency_ms`) и предмет в PostgreSQL для отображения в Кабинете Учителя.

---

[⬅️ Глава 5: Bot Service](./05_bot_service_and_max.md) · [Оглавление](./README.md) · [Вперед: Хранилища данных ➡️](./07_data_storage_pg_redis.md)
