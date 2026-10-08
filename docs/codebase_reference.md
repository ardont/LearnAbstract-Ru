# 🗺️ Полный справочник кодовой базы: Архитектура каждого файла, модуля и функции

[⬅️ Вернуться к оглавлению книги](./README.md) · [Глава 02: Архитектура системы](./02_architecture_overview.md) · [Глава 08: Спецификация API](./08_api_and_swagger.md)

---

## 🧭 Навигация по разделам справочника

* [1. Общая архитектурная концепция и граф зависимостей](#sec-1)
* [2. Микросервис Core Service (`services/core_service/`)](#sec-2)
  * [main.py](#sec-2-1) · [fsm.py](#sec-2-2) · [rate_limiter.py](#sec-2-3) · [student_ui.py](#sec-2-4) · [metrics.py](#sec-2-5) · [db/database.py](#sec-2-6) · [db/models.py](#sec-2-7)
* [3. Микросервис ML Service (`services/ml_service/`)](#sec-3)
  * [main.py](#sec-3-1) · [rag_engine.py](#sec-3-2) · [metaphor_engine.py](#sec-3-3) · [fallback_catalog.py](#sec-3-4) · [llm_client.py](#sec-3-5) · [guardrails.py](#sec-3-6) · [dlq.py](#sec-3-7) · [metrics.py](#sec-3-8)
* [4. Микросервис Bot Service (`services/bot_service/`)](#sec-4)
  * [main.py](#sec-4-1) · [idempotency.py](#sec-4-2) · [watchdog.py](#sec-4-3) · [keyboards.py](#sec-4-4)
* [5. Общие библиотеки и контракты (`shared/`)](#sec-5)
  * [schemas/events.py](#sec-5-1) · [utils/logger.py](#sec-5-2) · [utils/text_formatter.py](#sec-5-3)
* [6. Скрипты автоматизации и эксплуатации (`scripts/`)](#sec-6)
  * [ingest_textbook.py](#sec-6-1) · [seed_demo_data.py](#sec-6-2) · [pre_demo_check.py](#sec-6-3) · [diagnose_rag.py](#sec-6-4) · [build_fallback_catalog.py](#sec-6-5) · [check_topics.py](#sec-6-6) · [create_sample_pdf.py](#sec-6-7) · [generate_comprehensive_textbook.py](#sec-6-8) · [generate_final_report.py](#sec-6-9) · [run_all_local.py](#sec-6-10) · [test_llm_real.py](#sec-6-11) · [start.sh / start.bat](#sec-6-12) · [stop.sh / stop.bat](#sec-6-13) · [deploy.sh](#sec-6-14) · [backup.sh](#sec-6-15)
* [7. Набор автоматических тестов (`tests/`)](#sec-7)
  * [test_fsm.py](#sec-7-1) · [test_chunking.py](#sec-7-2) · [test_guardrails.py](#sec-7-3) · [test_idempotency.py](#sec-7-4) · [test_text_formatter.py](#sec-7-5) · [test_web_api.py](#sec-7-6) · [test_rag_quality.py](#sec-7-7) · [test_rag_e2e.py](#sec-7-8) · [test_fallback_catalog.py](#sec-7-9) · [test_bot_handlers.py](#sec-7-10) · [test_dlq.py](#sec-7-11) · [test_e2e_kafka.py](#sec-7-12) · [test_e2e_pipeline.py](#sec-7-13)
* [8. Корневые конфигурации и спецификации](#sec-8)
  * [docker-compose.yml](#sec-8-1) · [DATA-API.yaml](#sec-8-2) · [openapi.json](#sec-8-3) · [requirements.txt](#sec-8-4) · [.env.example](#sec-8-5) · [mock_ml_service.py](#sec-8-6) · [test_bot.py](#sec-8-7) · [README.md](#sec-8-8) · [LICENSE](#sec-8-9)
* [9. Сквозная матрица взаимодействий (Who Calls What)](#sec-9)

---

<a id="sec-1"></a>
## 1. Общая архитектурная концепция и граф зависимостей

Проект **«Твой Путь: Абстрактный Репетитор»** реализует гибридную событийно-ориентированную архитектуру (**EDA**) с шиной **Apache Kafka в режиме KRaft** и прямым REST-фоллбэком.

```
       [ Ученик в мессенджере MAX ]                     [ Веб-кабинет Ученика /student ]
                    │                                                  │
                    ▼                                                  ▼
      ┌───────────────────────────┐                      ┌───────────────────────────┐
      │   services/bot_service/   │                      │   services/core_service/  │
      │   (Шлюз MAX, порт 8001)   │                      │     (BFF, порт 8000)      │
      └─────────────┬─────────────┘                      └─────────────┬─────────────┘
                    │                                                  │
                    │      Шина событий Kafka (education.events)       │
                    └─────────────────────► ◄──────────────────────────┘
                                            │
                                            ▼
                             ┌───────────────────────────┐
                             │    services/ml_service/   │
                             │   (RAG + LLM, порт 8002)  │
                             └───────────────────────────┘
```

---

<a id="sec-2"></a>
## 2. Микросервис Core Service (`services/core_service/`)

Core Service выполняет роль центрального координатора (BFF), хранит профили учеников, управляет FSM и предоставляет аналитический кабинет учителя. Подробная концепция описана в [Главе 03: Core Service](./03_core_service.md).

---

<a id="sec-2-1"></a>
### 2.1. [services/core_service/main.py](../services/core_service/main.py) — Точка входа FastAPI, BFF и воркер Kafka
* **Что это**: Главный исполнительный файл Core Service (FastAPI на порту 8000).
* **Зачем создавался**: Предоставляет публичный REST API для веб-клиента, вебхуков и дашборда учителя, оркестрирует транзакции в БД, следит за здоровьем платформы и потребляет события шины.
* **Как устроен и как работает**:
  * `lifespan(app)`: Инициализирует БД через `init_db()`, поднимает фоновый Kafka Worker `core_kafka_worker()` и регистрирует сигналы OS для Graceful Shutdown.
  * `core_kafka_worker()`: Слушает топик `education.events`. При получении `bot.command.received` обогащает запрос профилем ученика из БД (`get_or_create_user`), определяет предмет через `detect_subject` и публикует `explanation.requested`. Подтверждает офсет вручную `await kafka_consumer.commit()`.
  * `detect_subject(topic: str) -> str`: Классифицирует предмет по ключевым словам (`algebra`, `physics`, `cs`, `biology`).
  * `check_basic_auth(credentials)`: HTTP Basic Auth для Кабинета Учителя с защитой от тайминг-атак через `secrets.compare_digest`.
  * Эндпоинты: `/health`, `/health/full` (системный статус для жюри), `/metrics` (Prometheus), `/api/user/*`, `/api/quiz/*`, `/api/student/*`, `/teacher` и `/api/teacher/export_csv` (выгрузка отчета с UTF-8 BOM `\ufeff`).
* **С чем связан**: Импортирует [db/database.py](../services/core_service/db/database.py), [db/models.py](../services/core_service/db/models.py), [fsm.py](../services/core_service/fsm.py), [rate_limiter.py](../services/core_service/rate_limiter.py), [student_ui.py](../services/core_service/student_ui.py), [schemas/events.py](../shared/schemas/events.py). См. также [Главу 03: Core Service](./03_core_service.md).

---

<a id="sec-2-2"></a>
### 2.2. [services/core_service/fsm.py](../services/core_service/fsm.py) — Конечный автомат, 152-ФЗ и Quiz Freshness Guard
* **Что это**: Менеджер состояний диалога школьника.
* **Зачем создавался**: Обеспечивает строгое соблюдение закона 152-ФЗ «О персональных данных» и защищает систему от повторных кликов по старым кнопкам в чате.
* **Как устроен и как работает**:
  * `get_or_create_user(max_user_id)`: Авторегистрация пользователя с начальным состоянием `GUEST_CHOICE`.
  * `set_consent(max_user_id, accepted)`: Обрабатывает экран согласия. При отказе (`accepted=False`) выставляет флаг `is_guest=True` (обезличенный режим).
  * `set_interest(max_user_id, interest)`: Фиксирует увлечение (`Футбол`, `Видеоигры`, `Музыка` и др.) и переводит FSM в `IDLE`.
  * `register_quiz(max_user_id, quiz_id, ...)`: Сохраняет `QuizSession` и привязывает `User.current_quiz_id = quiz_id` в статусе `QUIZ_ACTIVE`.
  * `verify_quiz_answer(max_user_id, quiz_id, selected_option)`: **Quiz Freshness Guard**. Сверяет `user.current_quiz_id == quiz_id`. Если прислан старый ID — возвращает статус `"stale"`. Если актуален — начисляет XP, сохраняет `is_correct` и сбрасывает `current_quiz_id = None`.
  * `reset_user(max_user_id)`: Полный сброс профиля до `GUEST_CHOICE`.
  * `get_user_profile(max_user_id)`: Подсчет процента верных ответов и очков XP.
* **С чем связан**: Вызывается из [main.py](../services/core_service/main.py), работает через [db/database.py](../services/core_service/db/database.py) и модели [db/models.py](../services/core_service/db/models.py). См. также [Главу 03: Core Service](./03_core_service.md).

---

<a id="sec-2-3"></a>
### 2.3. [services/core_service/rate_limiter.py](../services/core_service/rate_limiter.py) — Скользящий Rate Limiter
* **Что это**: Ограничитель частоты запросов (10 RPM).
* **Зачем создавался**: Защита от спама, флуда и исчерпания лимитов внешних API нейросетей.
* **Как устроен и как работает**:
  * Реализует алгоритм **Sliding Window Log** за 60 секунд.
  * `check_rate_limit(user_id, limit_rpm=10)`:
    * При доступном Redis выполняет конвейер: `ZREMRANGEBYSCORE` (удаление старше 60 с) $\to$ `ZCARD` (подсчет) $\to$ `ZADD` (добавление текущего) $\to$ `EXPIRE 65`.
    * При превышении вычисляет точный `retry_after = 60 - (now - oldest_score)`.
    * При сбое Redis автоматически переключается на потокобезопасный локальный `collections.deque` с `asyncio.Lock()`.
* **С чем связан**: Вызывается в эндпоинте `/api/user/message` в [main.py](../services/core_service/main.py). Подробности в [Главе 03: Core Service](./03_core_service.md).

---

<a id="sec-2-4"></a>
### 2.4. [services/core_service/student_ui.py](../services/core_service/student_ui.py) — SSR Веб-портал Ученика
* **Что это**: Серверный генератор веб-интерфейса ученика (`GET /student`).
* **Зачем создавался**: Предоставляет полноценную браузерную альтернативу мессенджеру MAX для учеников без смартфона и для демонстрации жюри.
* **Как устроен и как работает**:
  * `render_student_portal() -> str`: Отдает монолитную HTML/CSS/JS разметку с темной/светлой темой.
  * Включает чат с аватарами, быстрые чипсы школьных тем, интерактивный блок квиза с мгновенным подсвечиванием правильного ответа, блок управления загруженными в RAG учебниками. Не требует внешних npm/CDN пакетов.
* **С чем связан**: Вызывается роутером `GET /student` в [main.py](../services/core_service/main.py).

---

<a id="sec-2-5"></a>
### 2.5. [services/core_service/metrics.py](../services/core_service/metrics.py) — Метрики Prometheus
* **Что это**: Сборщик телеметрии и мониторинга производительности.
* **Зачем создавался**: Обеспечивает Observability системы для интеграции с Prometheus и Grafana, а также питает данными дашборд `/health/full`.
* **Как устроен и как работает**:
  * Объявляет метрики `http_requests_total`, `llm_latency_seconds` (гистограмма бакетов от 0.1 до 10 с), `fallback_triggers_total`, `explanations_total`.
  * Ведет локальные кольцевые очереди `_llm_latencies` (maxlen=100) и `_llm_errors_5min`.
  * `record_explanation(latency_ms, source)` и `get_metrics_summary()` рассчитывают скользящее среднее время ответа.
  * `render_prometheus_metrics()` генерирует текст для эндпоинта `/metrics`.
* **С чем связан**: Вызывается в [main.py](../services/core_service/main.py).

---

<a id="sec-2-6"></a>
### 2.6. [services/core_service/db/database.py](../services/core_service/db/database.py) — Пул БД и Demo-Resilience Fallback
* **Что это**: Асинхронный драйвер базы данных.
* **Зачем создавался**: Гарантирует бесперебойную работу сервиса при сбое внешней PostgreSQL СУБД (**Demo-Resilience**).
* **Как устроен и как работает**:
  * `init_db()`: Пытается подключиться к PostgreSQL (`postgresql+asyncpg://...`) с жестким таймаутом в 3 секунды. Если СУБД недоступна — прозрачно переключается на локальный файл `sqlite+aiosqlite:///./core.db`.
  * Создает таблицы через `Base.metadata.create_all`.
  * `get_db_session()`: Предоставляет `AsyncSession` в виде контекстного менеджера с откатом транзакции при ошибках.
* **С чем связан**: Используется всеми сервисами Core Service. Подробно разобран в [Главе 07: Хранилища данных](./07_data_storage_pg_redis.md).

---

<a id="sec-2-7"></a>
### 2.7. [services/core_service/db/models.py](../services/core_service/db/models.py) — ORM-модели SQLAlchemy
* **Что это**: Описание схемы реляционных таблиц.
* **Зачем создавался**: Строгая типизация сущностей пользователей, сессий квизов и логов генераций.
* **Как устроен и как работает**:
  * Модели `User` (поля `max_user_id`, `state`, `interest`, `grade`, `is_guest`, `current_quiz_id`), `QuizSession` (тесты, варианты ответов, признак `is_correct`), `ExplanationLog` (время выполнения, источник метафоры).
* **С чем связан**: Используется в [db/database.py](../services/core_service/db/database.py), [fsm.py](../services/core_service/fsm.py) и [main.py](../services/core_service/main.py).

---

<a id="sec-3"></a>
## 3. Микросервис ML Service (`services/ml_service/`)

ML Service отвечает за формулобезопасный RAG-поиск, генерацию персонализированных метафор, Guardrails и каскадный Fallback. Подробности в [Главе 04: ML Service и RAG](./04_ml_service_and_rag.md).

---

<a id="sec-3-1"></a>
### 3.1. [services/ml_service/main.py](../services/ml_service/main.py) — Точка входа и Kafka-консьюмер
* **Что это**: Главный исполнительный файл ML Service (порт 8002).
* **Зачем создавался**: Вычитывает из Kafka запросы на генерацию метафор, запускает пайплайн инференса и отправляет готовый результат.
* **Как устроен и как работает**:
  * `kafka_worker()`: Консьюмер группы `ml_service_group` с отключенным автокоммитом (`enable_auto_commit=False`). Читает `explanation.requested`, передает в `generate_explanation()` из [llm_client.py](../services/ml_service/llm_client.py), упаковывает результат в `EventEnvelope` (`explanation.ready`) и отправляет обратно в шину.
  * При возникновении неустранимого сбоя вызывает `send_to_dlq()` из [dlq.py](../services/ml_service/dlq.py) и все равно коммитит смещение во избежание блокировки очереди.
* **С чем связан**: Слушает топик Kafka `education.events`, вызывает [llm_client.py](../services/ml_service/llm_client.py), [dlq.py](../services/ml_service/dlq.py), [schemas/events.py](../shared/schemas/events.py).

---

<a id="sec-3-2"></a>
### 3.2. [services/ml_service/rag_engine.py](../services/ml_service/rag_engine.py) — Движок BM25 Okapi и стемминг
* **Что это**: Поисковый индекс по чанкам учебников.
* **Зачем создавался**: Извлечение точных цитат из утвержденных школьных учебников без использования тяжелых сторонних векторных библиотек.
* **Как устроен и как работает**:
  * `_tokenize(text)`: Чистит текст, убирает стоп-слова русского языка (`RUSSIAN_STOP_WORDS`), лемматизирует через `pymorphy3` или встроенный эвристический стеммер `_stem_simple`.
  * Класс `BM25Okapi`: Реализует математику Lucene BM25 ($k_1=1.5, b=0.75$) с защитой от отрицательного $IDF$.
  * Класс `RAGEngine`: Проверяет наличие учебника по предмету (`has_subject`), загружает `data/vector_db/{subject}/index.json` с кэшированием по `mtime` и возвращает топ-$k$ чанков через метод `retrieve(query, subject, k=3)`.
* **С чем связан**: Вызывается из [llm_client.py](../services/ml_service/llm_client.py) и скрипта [diagnose_rag.py](../scripts/diagnose_rag.py).

---

<a id="sec-3-3"></a>
### 3.3. [services/ml_service/metaphor_engine.py](../services/ml_service/metaphor_engine.py) — 4-уровневый генератор метафор
* **Что это**: Каскадный оффлайн-движок метафор («План Б»).
* **Зачем создавался**: Гарантирует ответ за 180 мс даже при полном отсутствии интернета или падении нейросети.
* **Как устроен и как работает**:
  * `get_metaphor(topic, interest, grade)`:
    * **Уровень 1**: Поиск по каталогу из 100 метафор через `get_catalog_metaphor()` из [fallback_catalog.py](../services/ml_service/fallback_catalog.py).
    * **Уровень 1 (Exact)**: Локальный словарь `EXACT_TOPICS`.
    * **Уровень 2 (Предмет)**: Предметные шаблоны `SUBJECT_CATEGORIES` (алгебра, физика, информатика, биология).
    * **Уровень 3 (General)**: Универсальный общенаучный шаблон.
  * Все формулы автоматически конвертируются через `latex_to_unicode()`.
* **С чем связан**: Вызывается как Fallback из [llm_client.py](../services/ml_service/llm_client.py).

---

<a id="sec-3-4"></a>
### 3.4. [services/ml_service/fallback_catalog.py](../services/ml_service/fallback_catalog.py) — Каталог 100 выверенных метафор
* **Что это**: Статическая база знаний готовых метафор (170 КБ).
* **Зачем создавался**: 100% защита живой презентации от любых сбоев LLM.
* **Как устроен и как работает**:
  * Словарь `FALLBACK_CATALOG`: 20 ключевых школьных тем × 5 увлечений (Футбол, Баскетбол, Видеоигры, Музыка, Кино).
  * Каждая запись содержит 3-шаговую дидактическую структуру (Метафора $\to$ Формула в Unicode $\to$ Практический вывод) и квиз с 4 вариантами ответа и разбором.
  * `get_catalog_metaphor(topic, interest)`: Нечеткий поиск по синонимам тем.
* **С чем связан**: Импортируется в [metaphor_engine.py](../services/ml_service/metaphor_engine.py).

---

<a id="sec-3-5"></a>
### 3.5. [services/ml_service/llm_client.py](../services/ml_service/llm_client.py) — Оркестрация LLM-промптов
* **Что это**: Клиент к нейросетевым моделям (DeepSeek / Ollama).
* **Зачем создавался**: Соединяет запрос ребенка, контекст RAG и дидактические инструкции в единый промпт.
* **Как устроен и как работает**:
  * `generate_explanation(topic, interest, grade, subject, user_query)`:
    1. Проверка входных Guardrails через `check_guardrails()`.
    2. Если включен `DEMO_MODE=true` или нет `LLM_API_KEY` — мгновенный переход к `get_metaphor()` (180 мс).
    3. Поиск чанков учебника через `rag_engine.retrieve(..., k=3)`.
    4. Отправка в LLM через `httpx.AsyncClient` с таймаутом.
    5. Проверка ответа через `OutputGuardrails.validate()`. При ошибках или опасном контенте — возврат безопасного Fallback.
* **С чем связан**: Вызывается из [main.py](../services/ml_service/main.py), использует [rag_engine.py](../services/ml_service/rag_engine.py), [guardrails.py](../services/ml_service/guardrails.py), [metaphor_engine.py](../services/ml_service/metaphor_engine.py).

---

<a id="sec-3-6"></a>
### 3.6. [services/ml_service/guardrails.py](../services/ml_service/guardrails.py) — Фильтры Input & Output безопасности
* **Что это**: Двухуровневый шлюз защиты контента.
* **Зачем создавался**: Защита детей от нежелательной информации и защита системы от Prompt Injection.
* **Как устроен и как работает**:
  * `check_guardrails(text)`: Блокирует `INJECTION_PATTERNS` (`ignore instructions`, `jailbreak`, `забудь инструкции`) и опасные слова (оружие, взрывчатка, наркотики).
  * `OutputGuardrails.validate(text)`: Проверяет ответ LLM на запрещенные темы (удары током, насилие), утечки PII (телефоны, email) и ограничение длины в 4000 символов.
* **С чем связан**: Вызывается в [llm_client.py](../services/ml_service/llm_client.py).

---

<a id="sec-3-7"></a>
### 3.7. [services/ml_service/dlq.py](../services/ml_service/dlq.py) — Dead Letter Queue
* **Что это**: Изолятор фатальных ошибок шины.
* **Зачем создавался**: Исключение «отравленных сообщений» (Poison Pills), способных парализовать очередь Kafka.
* **Как устроен и как работает**:
  * `send_to_dlq(original_event, exc, service_name)`: Собирает исходное событие, сообщение об ошибке и `traceback.format_exc()`, упаковывает в `EventEnvelope` (`event_type="education.events.dlq"`) и отправляет в аварийный топик.
* **С чем связан**: Вызывается в блоках перехвата исключений в [main.py](../services/ml_service/main.py). Подробно разобран в [Главе 06: Шина Kafka](./06_event_bus_kafka.md).

---

<a id="sec-3-8"></a>
### 3.8. [services/ml_service/metrics.py](../services/ml_service/metrics.py) — Метрики RAG
* **Что это**: Счетчик точности поискового RAG-движка.
* **Зачем создавался**: Учет RAG Hit Rate (процента запросов, нашедших точный фрагмент учебника).
* **Как устроен и как работает**:
  * Счетчики `rag_queries_total`, `rag_hits_total`.
  * `record_rag_query(hit: bool)` и `get_rag_metrics_summary()` рассчитывают процент успешных попаданий.
* **С чем связан**: Вызывается в [rag_engine.py](../services/ml_service/rag_engine.py).

---

<a id="sec-4"></a>
## 4. Микросервис Bot Service (`services/bot_service/`)

Bot Service связывает экосистему мессенджера MAX (`@t569_hakaton_max_bot`) с платформой. Подробный разбор UX диалога см. в [Главе 05: Bot Service](./05_bot_service_and_max.md).

---

<a id="sec-4-1"></a>
### 4.1. [services/bot_service/main.py](../services/bot_service/main.py) — Шлюз MAX и диспетчер сообщений
* **Что это**: Главный исполнительный файл чат-бота (порт 8001).
* **Зачем создавался**: Прием вебхуков, ведение диалога со школьником, отправка инлайн-кнопок и трансляция событий в шину.
* **Как устроен и как работает**:
  * `classify_intent(text)`: Эвристический анализатор намерений (`command`, `vague`, `chitchat`, `educational`).
  * `send_message_with_retry()`: Надежная отправка с 3 попытками и экспоненциальным бэкоффом.
  * `kafka_consumer_worker()`: Вычитывает готовые ответы `explanation.ready` из Kafka, отменяет Watchdog, конвертирует LaTeX в Unicode через `latex_to_unicode()`, нарезает через `split_for_max(limit=4000)` и отправляет в чат.
  * Команды: `/start` (инициализация FSM), `/profile` (успеваемость), `/reset` (сброс), `/hobby` (смена хобби).
  * Коллбэки: `consent_*` (152-ФЗ), `interest_*` (хобби), `quiz_*` (ответы на тесты).
* **С чем связан**: Использует [idempotency.py](../services/bot_service/idempotency.py), [watchdog.py](../services/bot_service/watchdog.py), [keyboards.py](../services/bot_service/keyboards.py), [utils/text_formatter.py](../shared/utils/text_formatter.py).

---

<a id="sec-4-2"></a>
### 4.2. [services/bot_service/idempotency.py](../services/bot_service/idempotency.py) — Дедупликация вебхуков SET NX
* **Что это**: Фильтр повторных входящих сообщений.
* **Зачем создавался**: Мессенджеры работают по семантике At-Least-Once Delivery. Без дедупликации один вопрос привел бы к дублированию ответов и лишним расходам токенов.
* **Как устроен и как работает**:
  * `is_duplicate_message(message_id, user_id, text)`:
    * Формирует ключ `ingress_msg:{id}` (TTL 3600 с) или `ingress_msg:{sha256}` (TTL 60 с).
    * В Redis выполняет атомарный `SET key 1 EX ttl NX`. Если ключ уже был, возвращает `True` (дубликат отсекается).
    * При недоступности Redis использует локальный кэш `_local_cache` с автоочисткой по таймстемпу.
* **С чем связан**: Вызывается при каждом входящем сообщении в [main.py](../services/bot_service/main.py).

---

<a id="sec-4-3"></a>
### 4.3. [services/bot_service/watchdog.py](../services/bot_service/watchdog.py) — Watchdog-таймеры на 45 секунд
* **Что это**: Таймер удержания внимания ребенка.
* **Зачем создавался**: Если генерация LLM длится более 10–15 секунд, ребенок считает, что бот завис. Watchdog информирует о процессе и удерживает контакт.
* **Как устроен и как работает**:
  * `register_watchdog(correlation_id, user_id, bot, timeout_sec=45)`: Запускает `asyncio.Task` и дублирует ключ в Redis `SET active_watchdog:{corr_id} EX 45`.
  * При срабатывании отправляет ободряющее сообщение: *«Генерация подробного объяснения требует чуть больше времени...»*.
  * `cancel_watchdog(correlation_id)`: Штатно отменяет задачу при получении ответа из Kafka.
* **С чем связан**: Вызывается при отправке вопроса и при получении ответа в [main.py](../services/bot_service/main.py).

---

<a id="sec-4-4"></a>
### 4.4. [services/bot_service/keyboards.py](../services/bot_service/keyboards.py) — Инлайн-клавиатуры
* **Что это**: Фабрика кнопочных интерфейсов для MAX.
* **Зачем создавался**: Исключение ручного ввода и опечаток ребенка, ускорение прохождения квизов.
* **Как устроен и как работает**:
  * Функции `get_consent_keyboard()` (152-ФЗ), `get_interests_keyboard()` (хобби), `get_quiz_keyboard(quiz_id, options)` (варианты теста), `get_after_explanation_keyboard()` (навигация после ответа), `get_profile_keyboard()`.
* **С чем связан**: Используется всеми хэндлерами в [main.py](../services/bot_service/main.py).

---

<a id="sec-5"></a>
## 5. Общие библиотеки и контракты (`shared/`)

Связующие модули между всеми сервисами платформы.

---

<a id="sec-5-1"></a>
### 5.1. [shared/schemas/events.py](../shared/schemas/events.py) — Контракты EventEnvelope
* **Что это**: Схемы Pydantic v2 для шины Apache Kafka.
* **Зачем создавался**: Обеспечение строгой типизации данных и контракта версионирования между сервисами (см. [Главу 06: Шина Kafka](./06_event_bus_kafka.md)).
* **Как устроен и как работает**:
  * Класс `EventEnvelope`: базовый контейнер (`event_id`, `event_type`, `version="1.0"`, `timestamp`, `correlation_id`, `causation_id`, `producer`, `payload`).
  * Модели полезной нагрузки: `UserMessagePayload`, `ExplanationRequestPayload`, `ExplanationResponsePayload`, `QuizResponsePayload`, `QuizAnswerPayload`, `DLQPayload`.
* **С чем связан**: Импортируется во всех трех микросервисах.

---

<a id="sec-5-2"></a>
### 5.2. [shared/utils/logger.py](../shared/utils/logger.py) — Структурированный JSON-логгер и 152-ФЗ
* **Что это**: Централизованный логгер с маскированием персональных данных.
* **Зачем создавался**: Обеспечение комплаенса 152-ФЗ (недопущение утечки PII в логи) и сквозной трассировки через `correlation_id`.
* **Как устроен и как работает**:
  * `correlation_id_ctx`: Переменная контекста `contextvars.ContextVar`.
  * `mask_pii(text)`: Заменяет телефонные номера (`+7 (***) ***-**-12`) и email-адреса на маскированные шаблоны.
  * `StructuredFormatter`: Форматирует каждую запись лога в JSON со сквозным `correlation_id`.
  * `setup_logger(name)`: Настройка логгера.
* **С чем связан**: Используется во всех Python-модулях репозитория.

---

<a id="sec-5-3"></a>
### 5.3. [shared/utils/text_formatter.py](../shared/utils/text_formatter.py) — Конвертер LaTeX -> Unicode и сплиттер
* **Что это**: Парсер математических выражений и сплиттер сообщений.
* **Зачем создавался**: Мессенджер MAX не имеет встроенного KaTeX-рендерера, сырой LaTeX выглядит нечитаемо.
* **Как устроен и как работает**:
  * `latex_to_unicode(text)`: Заменяет степени (`x^2 -> x²`), индексы (`x_1 -> x₁`), дроби (`\frac{a}{b} -> (a / b)`), корни (`\sqrt{D} -> √(D)`), греческие буквы ($\Delta, \alpha, \omega$) и операторы ($\times, \pm, \leq$).
  * `split_for_max(text, limit=4000)`: Делит длинный текст на чанки по границам параграфов и предложений без разрыва слов.
* **С чем связан**: Используется в [ml_service/llm_client.py](../services/ml_service/llm_client.py), [ml_service/metaphor_engine.py](../services/ml_service/metaphor_engine.py) и [bot_service/main.py](../services/bot_service/main.py).

---

<a id="sec-6"></a>
## 6. Скрипты автоматизации и эксплуатации (`scripts/`)

---

<a id="sec-6-1"></a>
### 6.1. [scripts/ingest_textbook.py](../scripts/ingest_textbook.py) — Формулобезопасный чанкинг и индексатор
* **Что это**: Утилита нарезки и индексации школьных учебников в формате PDF.
* **Зачем создавался**: Решает фундаментальную проблему RAG в точных науках — разрыв математических формул при нарезке текста.
* **Как устроен и как работает**:
  * `get_formula_spans(text)`: Находит диапазоны `$..$`, `$$..$$`, `\begin{..}..\end{..}`.
  * `split_text_into_chunks(text, 1000, 200)`: Нарезает текст чанками по 1000 символов с перекрытием 200. Если граница попадает внутрь формулы — сдвигает ее за пределы формульного спана.
  * `ingest_textbook(pdf_path, subject, output_dir)`: Извлекает текст через `pypdf`, нарезает и сохраняет `index.json`.
* **С чем связан**: Вызывается также из API веб-кабинета `/api/student/upload_textbook`.

---

<a id="sec-6-2"></a>
### 6.2. [scripts/seed_demo_data.py](../scripts/seed_demo_data.py) — Генератор демо-данных для жюри
* **Что это**: Скрипт наполнения базы данных.
* **Зачем создавался**: Создает реалистичную картину активности класса (20+ учеников, ответы на квизы, динамика за неделю) перед выходом на защиту.
* **Как устроен и как работает**: Заполняет таблицы `users`, `quiz_sessions`, `explanation_logs` в PostgreSQL/SQLite.

---

<a id="sec-6-3"></a>
### 6.3. [scripts/pre_demo_check.py](../scripts/pre_demo_check.py) — Предзащитная автопроверка портов
* **Что это**: Healthcheck-сканер перед защитой.
* **Зачем создавался**: Мгновенная верификация доступности портов 8000, 8001, 8002, 9092, 5432, 6379 и генерация отчета готовности.

---

<a id="sec-6-4"></a>
### 6.4. [scripts/diagnose_rag.py](../scripts/diagnose_rag.py) — Диагностика точности RAG
* **Что это**: Инспектор поискового индекса BM25.
* **Зачем создавался**: Проверяет покрытие учебников чанками и тестирует релевантность выдачи на контрольных вопросах.

---

<a id="sec-6-5"></a>
### 6.5. [scripts/build_fallback_catalog.py](../scripts/build_fallback_catalog.py) — Сборщик базы метафор
* **Что это**: Генератор статического каталога [fallback_catalog.py](../services/ml_service/fallback_catalog.py).
* **Зачем создавался**: Компиляция и валидация 100 метафор по матрице «20 тем × 5 увлечений».

---

<a id="sec-6-6"></a>
### 6.6. [scripts/check_topics.py](../scripts/check_topics.py) — Валидатор покрытия тем
* **Что это**: Тест на полноту охвата программы 5–7 классов.

---

<a id="sec-6-7"></a>
### 6.7. [scripts/create_sample_pdf.py](../scripts/create_sample_pdf.py) — Генератор тестового PDF
* **Что это**: Создает легковесный PDF с формулами для быстрых автотестов чанкинга без тяжелых учебников.

---

<a id="sec-6-8"></a>
### 6.8. [scripts/generate_comprehensive_textbook.py](../scripts/generate_comprehensive_textbook.py) — Генератор полного учебника
* **Что это**: Создает 30-страничный учебник алгебры с доказательствами теорем и формулами для нагрузочного тестирования BM25.

---

<a id="sec-6-9"></a>
### 6.9. [scripts/generate_final_report.py](../scripts/generate_final_report.py) — Финальный отчет метрик
* **Что это**: Агрегатор показателей точности RAG, скорости ответа и надежности Fallback для презентации команды.

---

<a id="sec-6-10"></a>
### 6.10. [scripts/run_all_local.py](../scripts/run_all_local.py) — Локальный мультипроцессный раннер
* **Что это**: Запуск всех 3 микросервисов параллельно в отдельных подпроцессах без Docker.

---

<a id="sec-6-11"></a>
### 6.11. [scripts/test_llm_real.py](../scripts/test_llm_real.py) — Тест реального инференса LLM
* **Что это**: Проверка соединения с удаленным API DeepSeek и локальным Ollama.

---

<a id="sec-6-12"></a>
### 6.12. [scripts/start.sh](../scripts/start.sh) / [scripts/start.bat](../scripts/start.bat) — Скрипты единого запуска
* **Что это**: Запуск инфраструктуры Docker Compose и микросервисов в одну команду.

---

<a id="sec-6-13"></a>
### 6.13. [scripts/stop.sh](../scripts/stop.sh) / [scripts/stop.bat](../scripts/stop.bat) — Скрипты остановки
* **Что это**: Корректный останов сервисов с сохранением баз данных и топиков.

---

<a id="sec-6-14"></a>
### 6.14. [scripts/deploy.sh](../scripts/deploy.sh) — Скрипт развертывания
* **Что это**: Автоматизация деплоя на выделенный сервер хакатона.

---

<a id="sec-6-15"></a>
### 6.15. [scripts/backup.sh](../scripts/backup.sh) — Автоматический бэкап базы данных
* **Что это**: Создание дампов PostgreSQL через `pg_dump`.

---

<a id="sec-7"></a>
## 7. Набор автоматических тестов (`tests/`)

* <a id="sec-7-1"></a>**7.1. [tests/test_fsm.py](../tests/test_fsm.py)** — Проверяет граф переходов FSM, логику согласия 152-ФЗ и работу Quiz Freshness Guard при клике на старые тесты.
* <a id="sec-7-2"></a>**7.2. [tests/test_chunking.py](../tests/test_chunking.py)** — Проверяет, что формулы `$..$`, `$$..$$`, `\begin{..}` никогда не разрываются посередине при нарезке на чанки 1000/200.
* <a id="sec-7-3"></a>**7.3. [tests/test_guardrails.py](../tests/test_guardrails.py)** — Проверяет блокировку Prompt Injection (`ignore instructions`, `jailbreak`) и фильтрацию опасных тем.
* <a id="sec-7-4"></a>**7.4. [tests/test_idempotency.py](../tests/test_idempotency.py)** — Проверяет отсечение дублирующихся сообщений в окнах 3600 с и 60 с.
* <a id="sec-7-5"></a>**7.5. [tests/test_text_formatter.py](../tests/test_text_formatter.py)** — Проверяет корректность конвертации LaTeX в Unicode ($x^2 \to x²$, $\sqrt{D} \to √(D)$).
* <a id="sec-7-6"></a>**7.6. [tests/test_web_api.py](../tests/test_web_api.py)** — Интеграционные тесты эндпоинтов Core Service (`/health`, `/api/user/*`, `/api/quiz/*`) через `fastapi.testclient.TestClient`.
* <a id="sec-7-7"></a>**7.7. [tests/test_rag_quality.py](../tests/test_rag_quality.py)** — Проверка релевантности ранжирования BM25 Okapi.
* <a id="sec-7-8"></a>**7.8. [tests/test_rag_e2e.py](../tests/test_rag_e2e.py)** — Сквозной тест от загрузки PDF до поиска чанков.
* <a id="sec-7-9"></a>**7.9. [tests/test_fallback_catalog.py](../tests/test_fallback_catalog.py)** — Проверяет целостность всех 100 метафор в каталоге.
* <a id="sec-7-10"></a>**7.10. [tests/test_bot_handlers.py](../tests/test_bot_handlers.py)** — Мок-тесты хэндлеров команд и коллбэков бота в MAX.
* <a id="sec-7-11"></a>**7.11. [tests/test_dlq.py](../tests/test_dlq.py)** — Проверка перенаправления сбойных пакетов в Dead Letter Queue.
* <a id="sec-7-12"></a>**7.12. [tests/test_e2e_kafka.py](../tests/test_e2e_kafka.py)** — Тест сквозной передачи событий через Kafka.
* <a id="sec-7-13"></a>**7.13. [tests/test_e2e_pipeline.py](../tests/test_e2e_pipeline.py)** — Полный цикл «Вопрос $\to$ RAG $\to$ Метафора $\to$ Квиз $\to$ Оценка».

---

<a id="sec-8"></a>
## 8. Корневые конфигурации и спецификации

* <a id="sec-8-1"></a>**8.1. [docker-compose.yml](../docker-compose.yml)** — Описание контейнеров: Kafka 3.7.0 в режиме KRaft (без ZooKeeper), `kafka-init` (автосоздание топиков `education.events` и `education.events.dlq`), PostgreSQL 15 Alpine, Redis 7 Alpine.
* <a id="sec-8-2"></a>**8.2. [DATA-API.yaml](../DATA-API.yaml)** — Официальная спецификация API для автоматизированной проверки жюри хакатона.
* <a id="sec-8-3"></a>**8.3. [openapi.json](../openapi.json)** — Спецификация OpenAPI 3.1 для Swagger/ReDoc.
* <a id="sec-8-4"></a>**8.4. [requirements.txt](../requirements.txt)** — Python-зависимости (FastAPI, uvicorn, aiokafka, redis, sqlalchemy, asyncpg, aiosqlite, pypdf, httpx, prometheus-client, pydantic, pymorphy3).
* <a id="sec-8-5"></a>**8.5. [.env.example](../.env.example)** — Шаблон переменных окружения (`MAX_BOT_TOKEN`, `LLM_API_KEY`, `DATABASE_URL` и др.).
* <a id="sec-8-6"></a>**8.6. [mock_ml_service.py](../mock_ml_service.py)** — Автономный мок ML-сервиса для изоляции фронтенд-тестов.
* <a id="sec-8-7"></a>**8.7. [test_bot.py](../test_bot.py)** — Интерактивный терминальный симулятор для ручного тестирования бота.
* <a id="sec-8-8"></a>**8.8. [README.md](../README.md)** — Главный паспорт проекта с описанием команды, архитектуры и ссылками.
* <a id="sec-8-9"></a>**8.9. [LICENSE](../LICENSE)** — Лицензия MIT.

---

<a id="sec-9"></a>
## 9. Сквозная матрица взаимодействий (Who Calls What)

| Исходный шаг | Вызывающий компонент | Целевой метод / Функция | Назначение действия |
| :--- | :--- | :--- | :--- |
| Сообщение в чате | Мессенджер MAX | [bot_service.idempotency.is_duplicate_message](../services/bot_service/idempotency.py) | Проверка дедупликации через Redis SET NX |
| Классификация | [bot_service.main](../services/bot_service/main.py) | `classify_intent` в [bot_service.main](../services/bot_service/main.py) | Определение намерения (команда/учеба/оффтоп) |
| Запуск таймера | [bot_service.main](../services/bot_service/main.py) | [bot_service.watchdog.register_watchdog](../services/bot_service/watchdog.py) | Регистрация таймера ожидания на 45 сек |
| Передача в шину | [bot_service.main](../services/bot_service/main.py) | Kafka `education.events` (`bot.command.received`) | Публикация запроса в очередь сообщений |
| Чтение шины | [core_service.main](../services/core_service/main.py) | [core_service.fsm.get_or_create_user](../services/core_service/fsm.py) | Проверка статуса FSM и интереса в БД |
| Защита от DoS | [core_service.main](../services/core_service/main.py) | [core_service.rate_limiter.check_rate_limit](../services/core_service/rate_limiter.py) | Скользящее окно 10 RPM в Redis ZSET |
| Запрос в ML | [core_service.main](../services/core_service/main.py) | Kafka `education.events` (`explanation.requested`)| Передача обогащенного запроса в ML Service |
| RAG Поиск | [ml_service.main](../services/ml_service/main.py) | [ml_service.rag_engine.RAGEngine.retrieve](../services/ml_service/rag_engine.py) | Поиск 3 чанков в учебнике через BM25 Okapi |
| Синтез ответа | [ml_service.main](../services/ml_service/main.py) | [ml_service.llm_client.generate_explanation](../services/ml_service/llm_client.py) | Промпт в DeepSeek/Ollama или Fallback |
| Безопасность | [ml_service.llm_client](../services/ml_service/llm_client.py)| [ml_service.guardrails.OutputGuardrails.validate](../services/ml_service/guardrails.py)| Проверка токсичности и утечек PII |
| Формулы | [ml_service.llm_client](../services/ml_service/llm_client.py)| [shared.utils.text_formatter.latex_to_unicode](../shared/utils/text_formatter.py) | Конвертация формул LaTeX в Unicode |
| Ответ готов | [ml_service.main](../services/ml_service/main.py) | Kafka `education.events` (`explanation.ready`) | Публикация результата в Kafka |
| Доставка в чат | [bot_service.main](../services/bot_service/main.py) | [bot_service.watchdog.cancel_watchdog](../services/bot_service/watchdog.py) | Снятие Watchdog-таймера и отправка текста |
| Клик по квизу | Мессенджер MAX | [core_service.fsm.verify_quiz_answer](../services/core_service/fsm.py) | Проверка Quiz Freshness Guard и начисление XP |
| Аналитика | Браузер Учителя | `export_teacher_csv` в [core_service.main](../services/core_service/main.py) | Выгрузка отчета в Excel (CSV с UTF-8 BOM) |

---

[⬅️ Вернуться к оглавлению книги](./README.md) · [Глава 02: Архитектура системы](./02_architecture_overview.md) · [Глава 08: Спецификация API](./08_api_and_swagger.md)
