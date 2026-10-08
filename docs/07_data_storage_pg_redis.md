# 💾 Глава 7: Хранилища данных: PostgreSQL и Redis
[⬅️ Глава 6: Шина Kafka](./06_event_bus_kafka.md) · [Оглавление](./README.md) · [Вперед: Спецификация API ➡️](./08_api_and_swagger.md)

---

## 1. Концепция хранения: Polyglot Persistence

Архитектура платформы «Твой Путь» разделяет потоки данных по их жизненному циклу и требованиям к скорости:
1. **Долговременный реляционный слой (PostgreSQL 15)**: персистентность профилей учеников, история прохождения квизов, логи задержек для учителя.
2. **Оперативный слой в оперативной памяти (Redis 7)**: скользящие окна лимитов запросов (Rate Limiter), атомарные блокировки идемпотентности, мониторинг живых сессий.
3. **Локальный аварийный слой (SQLite / aiosqlite)**: моментальный fallback при сбое внешней СУБД для обеспечения 100% готовности демонстрации («План Б»).

```
                ┌──────────────────────────────────────┐
                │          Core & Bot Services         │
                └───────┬──────────────────────┬───────┘
                        │                      │
           (Оперативные структуры)   (Транзакции и аналитика)
                        │                      │
                        ▼                      ▼
             ┌─────────────────────┐┌────────────────────────┐
             │       REDIS 7       ││     POSTGRESQL 15      │
             │ • ZSET: Rate Limit  ││ (SQLAlchemy 2.0 async) │
             │ • SET NX: Дедуплик. ││ • users                │
             │ • TTL: Watchdog     ││ • quiz_sessions        │
             └──────────┬──────────┘│ • explanation_logs     │
                        │           └──────────┬─────────────┘
                (Если сбой Redis)              │ (Если сбой PG)
                        │                      ▼
                        ▼           ┌────────────────────────┐
             ┌─────────────────────┐│     SQLITE (core.db)   │
             │  In-Memory Fallback ││  Резервная локальная БД│
             │(deque + Lock + Dict)│└────────────────────────┘
             └─────────────────────┘
```

---

## 2. Реляционная схема данных (`services/core_service/db/models.py`)

Модели спроектированы в декларативном стиле SQLAlchemy 2.0 с поддержкой асинхронного драйвера `asyncpg`:

### 1. Таблица `users` (Профиль и состояние FSM)
```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    max_user_id = Column(String(100), unique=True, index=True, nullable=False)
    state = Column(String(50), default="GUEST_CHOICE", nullable=False)
    interest = Column(String(100), nullable=True)
    grade = Column(Integer, default=7, nullable=False)
    is_guest = Column(Boolean, default=False, nullable=False)
    current_quiz_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
```
* **Индексы**: `max_user_id` снабжен уникальным индексом для мгновенного поиска за $O(1)$ при каждом сообщении бота.
* **Поле `current_quiz_id`**: критический элемент **Quiz Freshness Guard**. Хранит ID актуального активного теста. Если ученик кликает по старой кнопке в чате, расхождение ID немедленно отклоняет ответ.

### 2. Таблица `quiz_sessions` (История тестирования)
```python
class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(String(100), unique=True, index=True, nullable=False)
    max_user_id = Column(String(100), index=True, nullable=False)
    topic = Column(String(200), nullable=False)
    question = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    correct_option_index = Column(Integer, nullable=False)
    user_answer = Column(Integer, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    answered_at = Column(DateTime, nullable=True)
```
* Варианты ответов квиза хранятся в JSON-формате через проперти-геттер/сеттер `options`.
* Записи используются учителем для построения **Тепловой карты трудностей (Quiz Heatmap)**.

### 3. Таблица `explanation_logs` (Логирование качества и задержек)
```python
class ExplanationLog(Base):
    __tablename__ = "explanation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    max_user_id = Column(String(100), index=True, nullable=False)
    topic = Column(String(200), nullable=False)
    interest = Column(String(100), nullable=False)
    source = Column(String(50), default="llm", nullable=False)  # llm, fallback_exact...
    latency_ms = Column(Integer, default=0, nullable=False)
    is_guest = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
```

---

## 3. Отказоустойчивый пул подключений (`database.py`)

На хакатонах и в полевых условиях внешняя СУБД может не подняться вовремя (задержка Docker-сети, нехватка RAM). В `services/core_service/db/database.py` реализован механизм **Demo-Resilience**:

```python
async def init_db() -> bool:
    global active_engine, active_session_maker, is_sqlite_fallback

    # 1. Попытка подключения к основному PostgreSQL
    try:
        engine = create_async_engine(
            POSTGRES_URL,
            echo=False,
            pool_pre_ping=True,
            connect_args={"timeout": 3}  # Жесткий таймаут на пробу
        )
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        active_engine = engine
        active_session_maker = async_sessionmaker(active_engine, expire_on_commit=False, class_=AsyncSession)
        is_sqlite_fallback = False
        logger.info("Подключение к PostgreSQL успешно установлено")
        ...
        return True
    except Exception as e:
        logger.warning(f"PostgreSQL недоступен. Переключение на резервный SQLite...")

    # 2. Мгновенное резервное переключение на SQLite
    try:
        engine = create_async_engine(SQLITE_URL, echo=False)
        active_engine = engine
        active_session_maker = async_sessionmaker(active_engine, expire_on_commit=False, class_=AsyncSession)
        is_sqlite_fallback = True
        ...
        logger.info("Резервная БД SQLite успешно инициализирована")
        return True
    except Exception as e:
        logger.critical(f"Критическая ошибка инициализации БД: {e}")
        return False
```

* Пользователи и жюри не увидят `500 Internal Server Error`: сервис прозрачно переключится на локальный `core.db`.
* Статус СУБД честно отображается в системном дашборде `/health/full`:  
  `"database": "ok (postgres)"` либо `"database": "ok (sqlite_fallback)"`.

---

## 4. Архитектура данных в Redis

Redis работает в памяти и используется для трёх высоконагруженных задач:

### 1. Скользящий Rate Limiter (Redis Sorted Sets — `ZSET`)
* **Ключ**: `rate_limit:{user_id}`
* **Score & Member**: Unix Timestamp запроса (миллисекунды).
* **Атомарный конвейер (Pipeline)**:
  1. `ZREMRANGEBYSCORE key 0 (now - 60)` — выкидываем события старше 1 минуты.
  2. `ZCARD key` — подсчитываем оставшиеся события за последние 60 секунд.
  3. `ZADD key {now: now}` — вносим новый запрос.
  4. `EXPIRE key 65` — ставим TTL для автоматической очистки памяти.
* Если `count >= 10 RPM` — запрос отклоняется с указанием точного времени `retry_after`.

### 2. Идемпотентность вебхуков (`SET NX`)
* **Ключ**: `ingress_msg:{message_id}` (TTL: 3600 с)
* Команда `SET key "1" EX 3600 NX` выполняется за микросекунды и гарантирует, что повторные сетевые пакеты мессенджера не вызовут дублирования ответов.

### 3. Watchdog-таймеры
* **Ключ**: `active_watchdog:{correlation_id}` (TTL: 45 с)
* Содержит `user_id` и автоматически исчезает при штатном ответе.

---

## 5. Аналитические выборки и экспорт отчетов

В Кабинете Учителя (`/teacher`) бэкенд выполняет оптимизированные аналитические выборки:

```python
# Расчет тепловой карты ошибок по предметам:
query = select(
    QuizSession.topic,
    func.count(QuizSession.id).label("total"),
    func.sum(case((QuizSession.is_correct == False, 1), else_=0)).label("errors")
).group_by(QuizSession.topic)
```

При клике на «Экспорт в CSV» формируется поток данных с префиксом **UTF-8 BOM (`\ufeff`)**:
```python
output = io.StringIO()
output.write("\ufeff") # Byte Order Mark для Microsoft Excel
writer = csv.writer(output, dialect="excel")
writer.writerow(["Ученик", "Предмет", "Тема", "Результат", "Дата"])
```
Это гарантирует, что школьный учитель откроет файл на любом компьютере с Windows и увидит идеальный русский текст без кракозябр.

---

[⬅️ Глава 6: Шина Kafka](./06_event_bus_kafka.md) · [Оглавление](./README.md) · [Вперед: Спецификация API ➡️](./08_api_and_swagger.md)
