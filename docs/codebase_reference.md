# 🗺️ Полный справочник кодовой базы: Архитектура каждого файла, модуля и функции

[⬅️ Вернуться к оглавлению книги](./README.md) · [Глава 02: Архитектура системы](./02_architecture_overview.md) · [Глава 08: Спецификация API](./08_api_and_swagger.md)

---

## 🧭 Навигация по разделам справочника

1. [Общая архитектурная концепция и граф зависимостей](#1-общая-архитектурная-концепция-и-граф-зависимостей)
2. [Микросервис Core Service (`services/core_service/`)](#2-микросервис-core-service-servicescore_service)
   * [`main.py`](#21-servicescore_servicemainpy--точка-входа-fastapi-bff-и-воркер-kafka) · [`fsm.py`](#22-servicescore_servicefsmpy--конечный-автомат-152-фз-и-quiz-freshness-guard) · [`rate_limiter.py`](#23-servicescore_servicerate_limiterpy--скользящий-rate-limiter) · [`student_ui.py`](#24-servicescore_servicestudent_uipy--ssr-веб-портал-ученика) · [`metrics.py`](#25-servicescore_servicemetricspy--метрики-prometheus) · [`db/database.py`](#26-servicescore_servicedbdatabasepy--пул-бд-и-demo-resilience-fallback) · [`db/models.py`](#27-servicescore_servicedbmodelspy--orm-модели-sqlalchemy)
3. [Микросервис ML Service (`services/ml_service/`)](#3-микросервис-ml-service-servicesml_service)
   * [`main.py`](#31-servicesml_servicemainpy--точка-входа-и-kafka-консьюмер) · [`rag_engine.py`](#32-servicesml_servicerag_enginepy--движок-bm25-okapi-и-стемминг) · [`metaphor_engine.py`](#33-servicesml_servicemetaphor_enginepy--4-уровневый-генератор-метафор) · [`fallback_catalog.py`](#34-servicesml_servicefallback_catalogpy--каталог-100-выверенных-метафор) · [`llm_client.py`](#35-servicesml_servicellm_clientpy--оркестрация-llm-промптов) · [`guardrails.py`](#36-servicesml_serviceguardrailspy--фильтры-input--output-безопасности) · [`dlq.py`](#37-servicesml_servicedlqpy--dead-letter-queue) · [`metrics.py`](#38-servicesml_servicemetricspy--метрики-rag)
4. [Микросервис Bot Service (`services/bot_service/`)](#4-микросервис-bot-service-servicesbot_service)
   * [`main.py`](#41-servicesbot_servicemainpy--шлюз-max-и-диспетчер-сообщений) · [`idempotency.py`](#42-servicesbot_serviceidempotencypy--дедупликация-вебхуков-set-nx) · [`watchdog.py`](#43-servicesbot_servicewatchdogpy--watchdog-таймеры-на-45-секунд) · [`keyboards.py`](#44-servicesbot_servicekeyboardspy--инлайн-клавиатуры)
5. [Общие библиотеки и контракты (`shared/`)](#5-общие-библиотеки-и-контракты-shared)
   * [`schemas/events.py`](#51-sharedschemaseventspy--контракты-eventenvelope) · [`utils/logger.py`](#52-sharedutilsloggerpy--структурированный-json-логгер-и-152-фз) · [`utils/text_formatter.py`](#53-sharedutilstext_formatterpy--конвертер-latex--unicode-и-сплиттер)
6. [Скрипты автоматизации и эксплуатации (`scripts/`)](#6-скрипты-автоматизации-и-эксплуатации-scripts)
   * [`ingest_textbook.py`](#61-scriptsingest_textbookpy--формулобезопасный-чанкинг-и-индексатор) · [`seed_demo_data.py`](#62-scriptsseed_demo_datapy--генератор-демо-данных-для-жюри) · [`pre_demo_check.py`](#63-scriptspre_demo_checkpy--предзащитная-автопроверка-портов) · [`diagnose_rag.py`](#64-scriptsdiagnose_ragpy--диагностика-точности-rag) · [`build_fallback_catalog.py`](#65-scriptsbuild_fallback_catalogpy--сборщик-базы-метафор) · [`check_topics.py`](#66-scriptscheck_topicspy--валидатор-покрытия-тем) · [`create_sample_pdf.py`](#67-scriptscreate_sample_pdfpy--генератор-тестового-pdf) · [`generate_comprehensive_textbook.py`](#68-scriptsgenerate_comprehensive_textbookpy--генератор-полного-учебника) · [`generate_final_report.py`](#69-scriptsgenerate_final_reportpy--финальный-отчет-метрик) · [`run_all_local.py`](#610-scriptsrun_all_localpy--локальный-мультипроцессный-раннер) · [`test_llm_real.py`](#611-scriptstest_llm_realpy--тест-реального-инференса-llm) · [`start.sh` / `start.bat`](#612-scriptsstartsh--startbat--скрипты-единого-запуска) · [`stop.sh` / `stop.bat`](#613-scriptsstopsh--stopbat--скрипты-остановки) · [`deploy.sh`](#614-scriptsdeploysh--скрипт-развертывания) · [`backup.sh`](#615-scriptsbackupsh--автоматический-бэкап-базы-данных)
7. [Набор автоматических тестов (`tests/`)](#7-набор-автоматических-тестов-tests)
   * [`test_fsm.py`](#71-teststest_fsmpy) · [`test_chunking.py`](#72-teststest_chunkingpy) · [`test_guardrails.py`](#73-teststest_guardrailspy) · [`test_idempotency.py`](#74-teststest_idempotencypy) · [`test_text_formatter.py`](#75-teststest_text_formatterpy) · [`test_web_api.py`](#76-teststest_web_apipy) · [`test_rag_quality.py`](#77-teststest_rag_qualitypy) · [`test_rag_e2e.py`](#78-teststest_rag_e2epy) · [`test_fallback_catalog.py`](#79-teststest_fallback_catalogpy) · [`test_bot_handlers.py`](#710-teststest_bot_handlerspy) · [`test_dlq.py`](#711-teststest_dlqpy) · [`test_e2e_kafka.py`](#712-teststest_e2e_kafkapy) · [`test_e2e_pipeline.py`](#713-teststest_e2e_pipelinepy)
8. [Корневые конфигурации и спецификации](#8-корневые-конфигурации-и-спецификации)
   * [`docker-compose.yml`](#81-docker-composeyml) · [`DATA-API.yaml`](#82-data-apiyaml) · [`openapi.json`](#83-openapi-json) · [`requirements.txt`](#84-requirementstxt) · [`.env.example`](#85-envexample) · [`mock_ml_service.py`](#86-mock_ml_servicepy) · [`test_bot.py`](#87-test_botpy) · [`README.md`](#88-readmemd) · [`LICENSE`](#89-license)
9. [Сквозная матрица взаимодействий (Who Calls What)](#9-сквозная-матрица-взаимодействий-who-calls-what)

---

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

## 2. Микросервис Core Service (`services/core_service/`)

Core Service выполняет роль центрального координатора (BFF), хранит профили учеников, управляет FSM и предоставляет аналитический кабинет учителя. Подробная концепция описана в [Главе 03: Core Service](./03_core_service.md).

---

### 2.1. [`services/core_service/main.py`](file:///c:/Users/Maxim/Desktop/фокусы/хакатоны/макс/твой%20путь/repo/services/core_service/main.py) — Точка входа FastAPI, BFF и воркер Kafka
* **Что это**: Главный исполнительный файл Core Service (FastAPI на порту 8000).
* **Зачем создавался**: Предоставляет публичный REST API для веб-клиента, вебхуков и дашборда учителя, оркестрирует транзакции в БД, следит за здоровьем платформы и потребляет события шины.
* **Как устроен и как работает**:
  * `lifespan(app)`: Инициализирует БД через `init_db()`, поднимает фоновый Kafka Worker `core_kafka_worker()` и регистрирует сигналы OS для Graceful Shutdown.
  * `core_kafka_worker()`: Слушает топик `education.events`. При получении `bot.command.received` обогащает запрос профилем ученика из БД (`get_or_create_user`), определяет предмет через `detect_subject` и публикует `explanation.requested`. Подтверждает офсет вручную `await kafka_consumer.commit()`.
  * `detect_subject(topic: str) -> str`: Классифицирует предмет по ключевым словам (`algebra`, `physics`, `cs`, `biology`).
  * `check_basic_auth(credentials)`: HTTP Basic Auth для Кабинета Учителя с защитой от тайминг-атак через `secrets.compare_digest`.
  * Эндпоинты: `/health`, `/health/full` (системный статус для жюри), `/metrics` (Prometheus), `/api/user/*`, `/api/quiz/*`, `/api/student/*`, `/teacher` и `/api/teacher/export_csv` (выгрузка отчета с UTF-8 BOM `\ufeff`).
* **С чем связан**: Импортирует [database.py](./codebase_reference.md#26-servicescore_servicedbdatabasepy--пул-бд-и-demo-resilience-fallback), [models.py](./codebase_reference.md#27-servicescore_servicedbmodelspy--orm-модели-sqlalchemy), [fsm.py](./codebase_reference.md#22-servicescore_servicefsmpy--конечный-автомат-152-фз-и-quiz-freshness-guard), [rate_limiter.py](./codebase_reference.md#23-servicescore_servicerate_limiterpy--скользящий-rate-limiter), [student_ui.py](./codebase_reference.md#24-servicescore_servicestudent_uipy--ssr-веб-портал-ученика), [events.py](./codebase_reference.md#51-sharedschemaseventspy--контракты-eventenvelope).

---

### 2.2. [`services/core_service/fsm.py`](file:///c:/Users/Maxim/Desktop/фокусы/хакатоны/макс/твой%20путь/repo/services/core_service/fsm.py) — Конечный автомат, 152-ФЗ и Quiz Freshness Guard
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
* **С чем связан**: Вызывается из [main.py](./codebase_reference.md#21-servicescore_servicemainpy--точка-входа-fastapi-bff-и-воркер-kafka), работает через [database.py](./codebase_reference.md#26-servicescore_servicedbdatabasepy--пул-бд-и-demo-resilience-fallback) и модели [models.py](./codebase_reference.md#27-servicescore_servicedbmodelspy--orm-модели-sqlalchemy).

---

### 2.3. [`services/core_service/rate_limiter.py`](file:///c:/Users/Maxim/Desktop/фокусы/хакатоны/макс/твой%20путь/repo/services/core_service/rate_limiter.py) — Скользящий Rate Limiter
* **Что это**: Ограничитель частоты запросов (10 RPM).
* **Зачем создавался**: Защита от спама, флуда и исчерпания лимитов внешних API нейросетей.
* **Как устроен и как работает**:
  * Реализует алгоритм **Sliding Window Log** за 60 секунд.
  * `check_rate_limit(user_id, limit_rpm=10)`:
    * При доступном Redis выполняет конвейер: `ZREMRANGEBYSCORE` (удаление старше 60 с) $\to$ `ZCARD` (подсчет) $\to$ `ZADD` (добавление текущего) $\to$ `EXPIRE 65`.
    * При превышении вычисляет точный `retry_after = 60 - (now - oldest_score)`.
    * При сбое Redis автоматически переключается на потокобезопасный локальный `collections.deque` с `asyncio.Lock()`.
* **С чем связан**: Вызывается в эндпоинте `/api/user/message` в [main.py](./codebase_reference.md#21-servicescore_servicemainpy--точка-входа-fastapi-bff-и-воркер-kafka). Подробности в [Главе 03: Core Service](./03_core_service.md).

---

### 2.4. [`services/core_service/student_ui.py`](file:///c:/Users/Maxim/Desktop/фокусы/хакатоны/макс/твой%20путь/repo/services/core_service/student_ui.py) — SSR Веб-портал Ученика
* **Что это**: Серверный генератор веб-интерфейса ученика (`GET /student`).
* **Зачем создавался**: Предоставляет полноценную браузерную альтернативу мессенджеру MAX для учеников без смартфона и для демонстрации жюри.
* **Как устроен и как работает**:
  * `render_student_portal() -> str`: Отдает монолитную HTML/CSS/JS разметку с темной/светлой темой.
  * Включает чат с аватарами, быстрые чипсы школьных тем, интерактивный блок квиза с мгновенным подсвечиванием правильного ответа, блок управления загруженными в RAG учебниками. Не требует внешних npm/CDN пакетов.
* **С чем связан**: Вызывается роутером `GET /student` в [main.py](./codebase_reference.md#21-servicescore_servicemainpy--точка-входа-fastapi-bff-и-воркер-kafka).

---

### 2.5. [`services/core_service/metrics.py`](file:///c:/Users/Maxim/Desktop/фокусы/хакатоны/макс/твой%20путь/repo/services/core_service/metrics.py) — Метрики Prometheus
* **Что это**: Сборщик телеметрии и мониторинга производительности.
* **Зачем создавался**: Обеспечивает Observability системы для интеграции с Prometheus и Grafana, а также питает данными дашборд `/health/full`.
* **Как устроен и как работает**:
  * Объявляет метрики `http_requests_total`, `llm_latency_seconds` (гистограмма бакетов от 0.1 до 10 с), `fallback_triggers_total`, `explanations_total`.
  * Ведет локальные кольцевые очереди `_llm_latencies` (maxlen=100) и `_llm_errors_5min`.
  * `record_explanation(latency_ms, source)` и `get_metrics_summary()` рассчитывают скользящее среднее время ответа.
  * `render_prometheus_metrics()` генерирует текст для эндпоинта `/metrics`.
* **С чем связан**: Вызывается в [main.py](./codebase_reference.md#21-servicescore_servicemainpy--точка-входа-fastapi-bff-и-воркер-kafka).

---

### 2.6. [`services/core_service/db/database.py`](file:///c:/Users/Maxim/Desktop/фокусы/хакатоны/макс/твой%20путь/repo/services/core_service/db/database.py) — Пул БД и Demo-Resilience Fallback
* **Что это**: Асинхронный драйвер базы данных.
* **Зачем создавался**: Гарантирует бесперебойную работу сервиса при сбое внешней PostgreSQL СУБД (**Demo-Resilience**).
* **Как устроен и как работает**:
  * `init_db()`: Пытается подключиться к PostgreSQL (`postgresql+asyncpg://...`) с жестким таймаутом в 3 секунды. Если СУБД недоступна — прозрачно переключается на локальный файл `sqlite+aiosqlite:///./core.db`.
  * Создает таблицы через `Base.metadata.create_all`.
  * `get_db_session()`: Предоставляет `AsyncSession` в виде контекстного менеджера с откатом транзакции при ошибках.
* **С чем связан**: Используется всеми сервисами Core Service. Подробно разобран в [Главе 07: Хранилища данных](./07_data_storage_pg_redis.md).

---

### 2.7. [`services/core_service/db/models.py`](file:///c:/Users/Maxim/Desktop/фокусы/хакатоны/макс/твой%20путь/repo/services/core_service/db/models.py) — ORM-модели SQLAlchemy
* **Что это**: Описание схемы реляционных таблиц.
* **Зачем создавался**: Строгая типизация сущностей пользователей, сессий квизов и логов генераций.
* **Как устроен и как работает**:
  * Модели `User` (поля `max_user_id`, `state`, `interest`, `grade`, `is_guest`, `current_quiz_id`), `QuizSession` (тесты, варианты ответов, признак `is_correct`), `ExplanationLog` (время выполнения, источник метафоры).
* **С чем связан**: Используется в [database.py](./codebase_reference.md#26-servicescore_servicedbdatabasepy--пул-бд-и-demo-resilience-fallback), [fsm.py](./codebase_reference.md#22-servicescore_servicefsmpy--конечный-автомат-152-фз-и-quiz-freshness-guard) и [main.py](./codebase_reference.md#21-servicescore_servicemainpy--точка-входа-fastapi-bff-и-воркер-kafka).

---

## 3. Микросервис ML Service (`services/ml_service/`)

ML Service отвечает за формулобезопасный RAG-поиск, генерацию персонализированных метафор, Guardrails и каскадный Fallback. Подробности в [Главе 04: ML Service и RAG](./04_ml_service_and_rag.md).

---

### 3.1. [`services/ml_service/main.py`](file:///c:/Users/Maxim/Desktop/фокусы/хакатоны\макс\твой%20путь\repo\services\ml_service\main.py) — Точка входа и Kafka-консьюмер
* **Что это**: Главный исполнительный файл ML Service (порт 8002).
* **Зачем создавался**: Вычитывает из Kafka запросы на генерацию метафор, запускает пайплайн инференса и отправляет готовый результат.
* **Как устроен и как работает**:
  * `kafka_worker()`: Консьюмер группы `ml_service_group` с отключенным автокоммитом (`enable_auto_commit=False`). Читает `explanation.requested`, передает в `generate_explanation()` из [llm_client.py](./codebase_reference.md#35-servicesml_servicellm_clientpy--оркестрация-llm-промптов), упаковывает результат в `EventEnvelope` (`explanation.ready`) и отправляет обратно в шину.
  * При возникновении неустранимого сбоя вызывает `send_to_dlq()` из [dlq.py](./codebase_reference.md#37-servicesml_servicedlqpy--dead-letter-queue) и все равно коммитит смещение во избежание блокировки очереди.
* **С чем связан**: Слушает топик Kafka `education.events`, вызывает [llm_client.py](./codebase_reference.md#35-servicesml_servicellm_clientpy--оркестрация-llm-промптов), [dlq.py](./codebase_reference.md#37-servicesml_servicedlqpy--dead-letter-queue), [events.py](./codebase_reference.md#51-sharedschemaseventspy--контракты-eventenvelope).

---

### 3.2. [`services/ml_service/rag_engine.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\services\ml_service\rag_engine.py) — Движок BM25 Okapi и стемминг
* **Что это**: Поисковый индекс по чанкам учебников.
* **Зачем создавался**: Извлечение точных цитат из утвержденных школьных учебников без использования тяжелых сторонних векторных библиотек.
* **Как устроен и как работает**:
  * `_tokenize(text)`: Чистит текст, убирает стоп-слова русского языка (`RUSSIAN_STOP_WORDS`), лемматизирует через `pymorphy3` или встроенный эвристический стеммер `_stem_simple`.
  * Класс `BM25Okapi`: Реализует математику Lucene BM25 ($k_1=1.5, b=0.75$) с защитой от отрицательного $IDF$.
  * Класс `RAGEngine`: Проверяет наличие учебника по предмету (`has_subject`), загружает `data/vector_db/{subject}/index.json` с кэшированием по `mtime` и возвращает топ-$k$ чанков через метод `retrieve(query, subject, k=3)`.
* **С чем связан**: Вызывается из [llm_client.py](./codebase_reference.md#35-servicesml_servicellm_clientpy--оркестрация-llm-промптов) и скрипта [diagnose_rag.py](./codebase_reference.md#64-scriptsdiagnose_ragpy--диагностика-точности-rag).

---

### 3.3. [`services/ml_service/metaphor_engine.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\services\ml_service\metaphor_engine.py) — 4-уровневый генератор метафор
* **Что это**: Каскадный оффлайн-движок метафор («План Б»).
* **Зачем создавался**: Гарантирует ответ за 180 мс даже при полном отсутствии интернета или падении нейросети.
* **Как устроен и как работает**:
  * `get_metaphor(topic, interest, grade)`:
    * **Уровень 1**: Поиск по каталогу из 100 метафор через `get_catalog_metaphor()` из [fallback_catalog.py](./codebase_reference.md#34-servicesml_servicefallback_catalogpy--каталог-100-выверенных-метафор).
    * **Уровень 1 (Exact)**: Локальный словарь `EXACT_TOPICS`.
    * **Уровень 2 (Предмет)**: Предметные шаблоны `SUBJECT_CATEGORIES` (алгебра, физика, информатика, биология).
    * **Уровень 3 (General)**: Универсальный общенаучный шаблон.
  * Все формулы автоматически конвертируются через `latex_to_unicode()`.
* **С чем связан**: Вызывается как Fallback из [llm_client.py](./codebase_reference.md#35-servicesml_servicellm_clientpy--оркестрация-llm-промптов).

---

### 3.4. [`services/ml_service/fallback_catalog.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\services\ml_service\fallback_catalog.py) — Каталог 100 выверенных метафор
* **Что это**: Статическая база знаний готовых метафор (170 КБ).
* **Зачем создавался**: 100% защита живой презентации от любых сбоев LLM.
* **Как устроен и как работает**:
  * Словарь `FALLBACK_CATALOG`: 20 ключевых школьных тем × 5 увлечений (Футбол, Баскетбол, Видеоигры, Музыка, Кино).
  * Каждая запись содержит 3-шаговую дидактическую структуру (Метафора $\to$ Формула в Unicode $\to$ Практический вывод) и квиз с 4 вариантами ответа и разбором.
  * `get_catalog_metaphor(topic, interest)`: Нечеткий поиск по синонимам тем.
* **С чем связан**: Импортируется в [metaphor_engine.py](./codebase_reference.md#33-servicesml_servicemetaphor_enginepy--4-уровневый-генератор-метафор).

---

### 3.5. [`services/ml_service/llm_client.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\services\ml_service\llm_client.py) — Оркестрация LLM-промптов
* **Что это**: Клиент к нейросетевым моделям (DeepSeek / Ollama).
* **Зачем создавался**: Соединяет запрос ребенка, контекст RAG и дидактические инструкции в единый промпт.
* **Как устроен и как работает**:
  * `generate_explanation(topic, interest, grade, subject, user_query)`:
    1. Проверка входных Guardrails через `check_guardrails()`.
    2. Если включен `DEMO_MODE=true` или нет `LLM_API_KEY` — мгновенный переход к `get_metaphor()` (180 мс).
    3. Поиск чанков учебника через `rag_engine.retrieve(..., k=3)`.
    4. Отправка в LLM через `httpx.AsyncClient` с таймаутом.
    5. Проверка ответа через `OutputGuardrails.validate()`. При ошибках или опасном контенте — возврат безопасного Fallback.
* **С чем связан**: Вызывается из [main.py](./codebase_reference.md#31-servicesml_servicemainpy--точка-входа-и-kafka-консьюмер), использует [rag_engine.py](./codebase_reference.md#32-servicesml_servicerag_enginepy--движок-bm25-okapi-и-стемминг), [guardrails.py](./codebase_reference.md#36-servicesml_serviceguardrailspy--фильтры-input--output-безопасности), [metaphor_engine.py](./codebase_reference.md#33-servicesml_servicemetaphor_enginepy--4-уровневый-генератор-метафор).

---

### 3.6. [`services/ml_service/guardrails.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\services\ml_service\guardrails.py) — Фильтры Input & Output безопасности
* **Что это**: Двухуровневый шлюз защиты контента.
* **Зачем создавался**: Защита детей от нежелательной информации и защита системы от Prompt Injection.
* **Как устроен и как работает**:
  * `check_guardrails(text)`: Блокирует `INJECTION_PATTERNS` (`ignore instructions`, `jailbreak`, `забудь инструкции`) и опасные слова (оружие, взрывчатка, наркотики).
  * `OutputGuardrails.validate(text)`: Проверяет ответ LLM на запрещенные темы (удары током, насилие), утечки PII (телефоны, email) и ограничение длины в 4000 символов.
* **С чем связан**: Вызывается в [llm_client.py](./codebase_reference.md#35-servicesml_servicellm_clientpy--оркестрация-llm-промптов).

---

### 3.7. [`services/ml_service/dlq.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\services\ml_service\dlq.py) — Dead Letter Queue
* **Что это**: Изолятор фатальных ошибок шины.
* **Зачем создавался**: Исключение «отравленных сообщений» (Poison Pills), способных парализовать очередь Kafka.
* **Как устроен и как работает**:
  * `send_to_dlq(original_event, exc, service_name)`: Собирает исходное событие, сообщение об ошибке и `traceback.format_exc()`, упаковывает в `EventEnvelope` (`event_type="education.events.dlq"`) и отправляет в аварийный топик.
* **С чем связан**: Вызывается в блоках перехвата исключений в [main.py](./codebase_reference.md#31-servicesml_servicemainpy--точка-входа-и-kafka-консьюмер). Подробно разобран в [Главе 06: Шина Kafka](./06_event_bus_kafka.md).

---

### 3.8. [`services/ml_service/metrics.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\services\ml_service\metrics.py) — Метрики RAG
* **Что это**: Счетчик точности поискового RAG-движка.
* **Зачем создавался**: Учет RAG Hit Rate (процента запросов, нашедших точный фрагмент учебника).
* **Как устроен и как работает**:
  * Счетчики `rag_queries_total`, `rag_hits_total`.
  * `record_rag_query(hit: bool)` и `get_rag_metrics_summary()` рассчитывают процент успешных попаданий.
* **С чем связан**: Вызывается в [rag_engine.py](./codebase_reference.md#32-servicesml_servicerag_enginepy--движок-bm25-okapi-и-стемминг).

---

## 4. Микросервис Bot Service (`services/bot_service/`)

Bot Service связывает экосистему мессенджера MAX (`@t569_hakaton_max_bot`) с платформой. Подробный разбор UX диалога см. в [Главе 05: Bot Service](./05_bot_service_and_max.md).

---

### 4.1. [`services/bot_service/main.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\services\bot_service\main.py) — Шлюз MAX и диспетчер сообщений
* **Что это**: Главный исполнительный файл чат-бота (порт 8001).
* **Зачем создавался**: Прием вебхуков, ведение диалога со школьником, отправка инлайн-кнопок и трансляция событий в шину.
* **Как устроен и как работает**:
  * `classify_intent(text)`: Эвристический анализатор намерений (`command`, `vague`, `chitchat`, `educational`).
  * `send_message_with_retry()`: Надежная отправка с 3 попытками и экспоненциальным бэкоффом.
  * `kafka_consumer_worker()`: Вычитывает готовые ответы `explanation.ready` из Kafka, отменяет Watchdog, конвертирует LaTeX в Unicode через `latex_to_unicode()`, нарезает через `split_for_max(limit=4000)` и отправляет в чат.
  * Команды: `/start` (инициализация FSM), `/profile` (успеваемость), `/reset` (сброс), `/hobby` (смена хобби).
  * Коллбэки: `consent_*` (152-ФЗ), `interest_*` (хобби), `quiz_*` (ответы на тесты).
* **С чем связан**: Использует [idempotency.py](./codebase_reference.md#42-servicesbot_serviceidempotencypy--дедупликация-вебхуков-set-nx), [watchdog.py](./codebase_reference.md#43-servicesbot_servicewatchdogpy--watchdog-таймеры-на-45-секунд), [keyboards.py](./codebase_reference.md#44-servicesbot_servicekeyboardspy--инлайн-клавиатуры), [text_formatter.py](./codebase_reference.md#53-sharedutilstext_formatterpy--конвертер-latex--unicode-и-сплиттер).

---

### 4.2. [`services/bot_service/idempotency.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\services\bot_service\idempotency.py) — Дедупликация вебхуков SET NX
* **Что это**: Фильтр повторных входящих сообщений.
* **Зачем создавался**: Мессенджеры работают по семантике At-Least-Once Delivery. Без дедупликации один вопрос привел бы к дублированию ответов и лишним расходам токенов.
* **Как устроен и как работает**:
  * `is_duplicate_message(message_id, user_id, text)`:
    * Формирует ключ `ingress_msg:{id}` (TTL 3600 с) или `ingress_msg:{sha256}` (TTL 60 с).
    * В Redis выполняет атомарный `SET key 1 EX ttl NX`. Если ключ уже был, возвращает `True` (дубликат отсекается).
    * При недоступности Redis использует локальный кэш `_local_cache` с автоочисткой по таймстемпу.
* **С чем связан**: Вызывается при каждом входящем сообщении в [main.py](./codebase_reference.md#41-servicesbot_servicemainpy--шлюз-max-и-диспетчер-сообщений).

---

### 4.3. [`services/bot_service/watchdog.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\services\bot_service\watchdog.py) — Watchdog-таймеры на 45 секунд
* **Что это**: Таймер удержания внимания ребенка.
* **Зачем создавался**: Если генерация LLM длится более 10–15 секунд, ребенок считает, что бот завис. Watchdog информирует о процессе и удерживает контакт.
* **Как устроен и как работает**:
  * `register_watchdog(correlation_id, user_id, bot, timeout_sec=45)`: Запускает `asyncio.Task` и дублирует ключ в Redis `SET active_watchdog:{corr_id} EX 45`.
  * При срабатывании отправляет ободряющее сообщение: *«Генерация подробного объяснения требует чуть больше времени...»*.
  * `cancel_watchdog(correlation_id)`: Штатно отменяет задачу при получении ответа из Kafka.
* **С чем связан**: Вызывается при отправке вопроса и при получении ответа в [main.py](./codebase_reference.md#41-servicesbot_servicemainpy--шлюз-max-и-диспетчер-сообщений).

---

### 4.4. [`services/bot_service/keyboards.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\services\bot_service\keyboards.py) — Инлайн-клавиатуры
* **Что это**: Фабрика кнопочных интерфейсов для MAX.
* **Зачем создавался**: Исключение ручного ввода и опечаток ребенка, ускорение прохождения квизов.
* **Как устроен и как работает**:
  * Функции `get_consent_keyboard()` (152-ФЗ), `get_interests_keyboard()` (хобби), `get_quiz_keyboard(quiz_id, options)` (варианты теста), `get_after_explanation_keyboard()` (навигация после ответа), `get_profile_keyboard()`.
* **С чем связан**: Используется всеми хэндлерами в [main.py](./codebase_reference.md#41-servicesbot_servicemainpy--шлюз-max-и-диспетчер-сообщений).

---

## 5. Общие библиотеки и контракты (`shared/`)

Связующие модули между всеми сервисами платформы.

---

### 5.1. [`shared/schemas/events.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\shared\schemas\events.py) — Контракты EventEnvelope
* **Что это**: Схемы Pydantic v2 для шины Apache Kafka.
* **Зачем создавался**: Обеспечение строгой типизации данных и контракта версионирования между сервисами (см. [Главу 06: Шина Kafka](./06_event_bus_kafka.md)).
* **Как устроен и как работает**:
  * Класс `EventEnvelope`: базовый контейнер (`event_id`, `event_type`, `version="1.0"`, `timestamp`, `correlation_id`, `causation_id`, `producer`, `payload`).
  * Модели полезной нагрузки: `UserMessagePayload`, `ExplanationRequestPayload`, `ExplanationResponsePayload`, `QuizResponsePayload`, `QuizAnswerPayload`, `DLQPayload`.
* **С чем связан**: Импортируется во всех трех микросервисах.

---

### 5.2. [`shared/utils/logger.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\shared\utils\logger.py) — Структурированный JSON-логгер и 152-ФЗ
* **Что это**: Централизованный логгер с маскированием персональных данных.
* **Зачем создавался**: Обеспечение комплаенса 152-ФЗ (недопущение утечки PII в логи) и сквозной трассировки через `correlation_id`.
* **Как устроен и как работает**:
  * `correlation_id_ctx`: Переменная контекста `contextvars.ContextVar`.
  * `mask_pii(text)`: Заменяет телефонные номера (`+7 (***) ***-**-12`) и email-адреса на маскированные шаблоны.
  * `StructuredFormatter`: Форматирует каждую запись лога в JSON со сквозным `correlation_id`.
  * `setup_logger(name)`: Настройка логгера.
* **С чем связан**: Используется во всех Python-модулях репозитория.

---

### 5.3. [`shared/utils/text_formatter.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\shared\utils\text_formatter.py) — Конвертер LaTeX -> Unicode и сплиттер
* **Что это**: Парсер математических выражений и сплиттер сообщений.
* **Зачем создавался**: Мессенджер MAX не имеет встроенного KaTeX-рендерера, сырой LaTeX выглядит нечитаемо.
* **Как устроен и как работает**:
  * `latex_to_unicode(text)`: Заменяет степени (`x^2 -> x²`), индексы (`x_1 -> x₁`), дроби (`\frac{a}{b} -> (a / b)`), корни (`\sqrt{D} -> √(D)`), греческие буквы ($\Delta, \alpha, \omega$) и операторы ($\times, \pm, \leq$).
  * `split_for_max(text, limit=4000)`: Делит длинный текст на чанки по границам параграфов и предложений без разрыва слов.
* **С чем связан**: Используется в [llm_client.py](./codebase_reference.md#35-servicesml_servicellm_clientpy--оркестрация-llm-промптов), [metaphor_engine.py](./codebase_reference.md#33-servicesml_servicemetaphor_enginepy--4-уровневый-генератор-метафор) и [bot_service/main.py](./codebase_reference.md#41-servicesbot_servicemainpy--шлюз-max-и-диспетчер-сообщений).

---

## 6. Скрипты автоматизации и эксплуатации (`scripts/`)

---

### 6.1. [`scripts/ingest_textbook.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\ingest_textbook.py) — Формулобезопасный чанкинг и индексатор
* **Что это**: Утилита нарезки и индексации школьных учебников в формате PDF.
* **Зачем создавался**: Решает фундаментальную проблему RAG в точных науках — разрыв математических формул при нарезке текста.
* **Как устроен и как работает**:
  * `get_formula_spans(text)`: Находит диапазоны `$..$`, `$$..$$`, `\begin{..}..\end{..}`.
  * `split_text_into_chunks(text, 1000, 200)`: Нарезает текст чанками по 1000 символов с перекрытием 200. Если граница попадает внутрь формулы — сдвигает ее за пределы формульного спана.
  * `ingest_textbook(pdf_path, subject, output_dir)`: Извлекает текст через `pypdf`, нарезает и сохраняет `index.json`.
* **С чем связан**: Вызывается также из API веб-кабинета `/api/student/upload_textbook`.

---

### 6.2. [`scripts/seed_demo_data.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\seed_demo_data.py) — Генератор демо-данных для жюри
* **Что это**: Скрипт наполнения базы данных.
* **Зачем создавался**: Создает реалистичную картину активности класса (20+ учеников, ответы на квизы, динамика за неделю) перед выходом на защиту.
* **Как устроен и как работает**: Заполняет таблицы `users`, `quiz_sessions`, `explanation_logs` в PostgreSQL/SQLite.

---

### 6.3. [`scripts/pre_demo_check.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\pre_demo_check.py) — Предзащитная автопроверка портов
* **Что это**: Healthcheck-сканер перед защитой.
* **Зачем создавался**: Мгновенная верификация доступности портов 8000, 8001, 8002, 9092, 5432, 6379 и генерация отчета готовности.

---

### 6.4. [`scripts/diagnose_rag.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\diagnose_rag.py) — Диагностика точности RAG
* **Что это**: Инспектор поискового индекса BM25.
* **Зачем создавался**: Проверяет покрытие учебников чанками и тестирует релевантность выдачи на контрольных вопросах.

---

### 6.5. [`scripts/build_fallback_catalog.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\build_fallback_catalog.py) — Сборщик базы метафор
* **Что это**: Генератор статического каталога [fallback_catalog.py](./codebase_reference.md#34-servicesml_servicefallback_catalogpy--каталог-100-выверенных-метафор).
* **Зачем создавался**: Компиляция и валидация 100 метафор по матрице «20 тем × 5 увлечений».

---

### 6.6. [`scripts/check_topics.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\check_topics.py) — Валидатор покрытия тем
* **Что это**: Тест на полноту охвата программы 5–7 классов.

---

### 6.7. [`scripts/create_sample_pdf.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\create_sample_pdf.py) — Генератор тестового PDF
* **Что это**: Создает легковесный PDF с формулами для быстрых автотестов чанкинга без тяжелых учебников.

---

### 6.8. [`scripts/generate_comprehensive_textbook.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\generate_comprehensive_textbook.py) — Генератор полного учебника
* **Что это**: Создает 30-страничный учебник алгебры с доказательствами теорем и формулами для нагрузочного тестирования BM25.

---

### 6.9. [`scripts/generate_final_report.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\generate_final_report.py) — Финальный отчет метрик
* **Что это**: Агрегатор показателей точности RAG, скорости ответа и надежности Fallback для презентации команды.

---

### 6.10. [`scripts/run_all_local.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\run_all_local.py) — Локальный мультипроцессный раннер
* **Что это**: Запуск всех 3 микросервисов параллельно в отдельных подпроцессах без Docker.

---

### 6.11. [`scripts/test_llm_real.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\test_llm_real.py) — Тест реального инференса LLM
* **Что это**: Проверка соединения с удаленным API DeepSeek и локальным Ollama.

---

### 6.12. [`scripts/start.sh` / `start.bat`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\start.sh) — Скрипты единого запуска
* **Что это**: Запуск инфраструктуры Docker Compose и микросервисов в одну команду.

---

### 6.13. [`scripts/stop.sh` / `stop.bat`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\stop.sh) — Скрипты остановки
* **Что это**: Корректный останов сервисов с сохранением баз данных и топиков.

---

### 6.14. [`scripts/deploy.sh`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\deploy.sh) — Скрипт развертывания
* **Что это**: Автоматизация деплоя на выделенный сервер хакатона.

---

### 6.15. [`scripts/backup.sh`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\scripts\backup.sh) — Автоматический бэкап базы данных
* **Что это**: Создание дампов PostgreSQL через `pg_dump`.

---

## 7. Набор автоматических тестов (`tests/`)

* **7.1. [`tests/test_fsm.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_fsm.py)** — Проверяет граф переходов FSM, логику согласия 152-ФЗ и работу Quiz Freshness Guard при клике на старые тесты.
* **7.2. [`tests/test_chunking.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_chunking.py)** — Проверяет, что формулы `$..$`, `$$..$$`, `\begin{..}` никогда не разрываются посередине при нарезке на чанки 1000/200.
* **7.3. [`tests/test_guardrails.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_guardrails.py)** — Проверяет блокировку Prompt Injection (`ignore instructions`, `jailbreak`) и фильтрацию опасных тем.
* **7.4. [`tests/test_idempotency.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_idempotency.py)** — Проверяет отсечение дублирующихся сообщений в окнах 3600 с и 60 с.
* **7.5. [`tests/test_text_formatter.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_text_formatter.py)** — Проверяет корректность конвертации LaTeX в Unicode ($x^2 \to x²$, $\sqrt{D} \to √(D)$).
* **7.6. [`tests/test_web_api.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_web_api.py)** — Интеграционные тесты эндпоинтов Core Service (`/health`, `/api/user/*`, `/api/quiz/*`) через `fastapi.testclient.TestClient`.
* **7.7. [`tests/test_rag_quality.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_rag_quality.py)** — Проверка релевантности ранжирования BM25 Okapi.
* **7.8. [`tests/test_rag_e2e.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_rag_e2e.py)** — Сквозной тест от загрузки PDF до поиска чанков.
* **7.9. [`tests/test_fallback_catalog.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_fallback_catalog.py)** — Проверяет целостность всех 100 метафор в каталоге.
* **7.10. [`tests/test_bot_handlers.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_bot_handlers.py)** — Мок-тесты хэндлеров команд и коллбэков бота в MAX.
* **7.11. [`tests/test_dlq.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_dlq.py)** — Проверка перенаправления сбойных пакетов в Dead Letter Queue.
* **7.12. [`tests/test_e2e_kafka.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_e2e_kafka.py)** — Тест сквозной передачи событий через Kafka.
* **7.13. [`tests/test_e2e_pipeline.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\tests\test_e2e_pipeline.py)** — Полный цикл «Вопрос $\to$ RAG $\to$ Метафора $\to$ Квиз $\to$ Оценка».

---

## 8. Корневые конфигурации и спецификации

* **8.1. [`docker-compose.yml`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\docker-compose.yml)** — Описание контейнеров: Kafka 3.7.0 в режиме KRaft (без ZooKeeper), `kafka-init` (автосоздание топиков `education.events` и `education.events.dlq`), PostgreSQL 15 Alpine, Redis 7 Alpine.
* **8.2. [`DATA-API.yaml`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\DATA-API.yaml)** — Официальная спецификация API для автоматизированной проверки жюри хакатона.
* **8.3. [`openapi.json`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\openapi.json)** — Спецификация OpenAPI 3.1 для Swagger/ReDoc.
* **8.4. [`requirements.txt`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\requirements.txt)** — Python-зависимости (FastAPI, uvicorn, aiokafka, redis, sqlalchemy, asyncpg, aiosqlite, pypdf, httpx, prometheus-client, pydantic, pymorphy3).
* **8.5. [`.env.example`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\.env.example)** — Шаблон переменных окружения (`MAX_BOT_TOKEN`, `LLM_API_KEY`, `DATABASE_URL` и др.).
* **8.6. [`mock_ml_service.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\mock_ml_service.py)** — Автономный мок ML-сервиса для изоляции фронтенд-тестов.
* **8.7. [`test_bot.py`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\test_bot.py)** — Интерактивный терминальный симулятор для ручного тестирования бота.
* **8.8. [`README.md`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\README.md)** — Главный паспорт проекта с описанием команды, архитектуры и ссылками.
* **8.9. [`LICENSE`](file:///c:/Users/Maxim/Desktop/фокусы\хакатоны\макс\твой%20путь\repo\LICENSE)** — Лицензия MIT.

---

## 9. Сквозная матрица взаимодействий (Who Calls What)

| Исходный шаг | Вызывающий компонент | Целевой метод / Функция | Назначение действия |
| :--- | :--- | :--- | :--- |
| Сообщение в чате | Мессенджер MAX | `bot_service.idempotency.is_duplicate_message` | Проверка дедупликации через Redis SET NX |
| Классификация | `bot_service.main` | `bot_service.main.classify_intent` | Определение намерения (команда/учеба/оффтоп) |
| Запуск таймера | `bot_service.main` | `bot_service.watchdog.register_watchdog` | Регистрация таймера ожидания на 45 сек |
| Передача в шину | `bot_service.main` | Kafka `education.events` (`bot.command.received`) | Публикация запроса в очередь сообщений |
| Чтение шины | `core_service.main` | `core_service.fsm.get_or_create_user` | Проверка статуса FSM и интереса в БД |
| Защита от DoS | `core_service.main` | `core_service.rate_limiter.check_rate_limit` | Скользящее окно 10 RPM в Redis ZSET |
| Запрос в ML | `core_service.main` | Kafka `education.events` (`explanation.requested`)| Передача обогащенного запроса в ML Service |
| RAG Поиск | `ml_service.main` | `ml_service.rag_engine.RAGEngine.retrieve` | Поиск 3 чанков в учебнике через BM25 Okapi |
| Синтез ответа | `ml_service.main` | `ml_service.llm_client.generate_explanation` | Промпт в DeepSeek/Ollama или Fallback |
| Безопасность | `ml_service.llm_client`| `ml_service.guardrails.OutputGuardrails.validate`| Проверка токсичности и утечек PII |
| Формулы | `ml_service.llm_client`| `shared.utils.text_formatter.latex_to_unicode` | Конвертация формул LaTeX в Unicode |
| Ответ готов | `ml_service.main` | Kafka `education.events` (`explanation.ready`) | Публикация результата в Kafka |
| Доставка в чат | `bot_service.main` | `bot_service.watchdog.cancel_watchdog` | Снятие Watchdog-таймера и отправка текста |
| Клик по квизу | Мессенджер MAX | `core_service.fsm.verify_quiz_answer` | Проверка Quiz Freshness Guard и начисление XP |
| Аналитика | Браузер Учителя | `core_service.main.export_teacher_csv` | Выгрузка отчета в Excel (CSV с UTF-8 BOM) |

---

[⬅️ Вернуться к оглавлению книги](./README.md) · [Глава 02: Архитектура системы](./02_architecture_overview.md) · [Глава 08: Спецификация API](./08_api_and_swagger.md)
