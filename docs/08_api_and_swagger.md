# 📑 Глава 8: Спецификация API и схемы данных (Swagger / DTO)
[⬅️ Глава 7: Хранилища данных](./07_data_storage_pg_redis.md) · [Оглавление](./README.md) · [Вперед: Масштабирование ➡️](./09_scalability_and_production.md)

---

## 1. Архитектура интерфейсов API

Вся экосистема «Твой Путь» построена на контрактах **RESTful HTTP API** с автоматической генерацией OpenAPI 3.1 спецификации.
* **Интерактивный Swagger UI**: `http://localhost:8000/docs`
* **Документация ReDoc**: `http://localhost:8000/redoc`
* **Машиночитаемый JSON**: `http://localhost:8000/openapi.json`
* **Файл для автотестов**: `DATA-API.yaml` в корне репозитория

Все входные и выходные структуры данных строго валидируются библиотекой **Pydantic v2**. Любое несоответствие типов автоматически возвращает понятный ответ `422 Unprocessable Entity` с указанием конкретного невалидного поля.

---

## 2. Разбор 5 групп эндпоинтов Core Service

```
┌────────────────────────────────────────────────────────────────────────┐
│                        ГРУППЫ ЭНДПОИНТОВ СИСТЕМЫ                       │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Monitoring & Ops     │ /health, /health/full, /metrics              │
│ 2. FSM & Routing        │ /api/user/{message, consent, interest, reset}│
│ 3. Quiz Engine          │ /api/quiz/{register, answer}                 │
│ 4. Student Web Portal   │ /student, /api/student/{ask, upload...}      │
│ 5. Teacher Dashboard    │ /teacher, /api/teacher/export_csv            │
└────────────────────────────────────────────────────────────────────────┘
```

### Группа 1: Мониторинг и эксплуатация (`Monitoring`)
* **`GET /health`**  
  *Назначение*: Быстрый liveness probe для Docker / Kubernetes.  
  *Ответ*: `{"status": "ok", "service": "core_service"}`
* **`GET /health/full`**  
  *Назначение*: Комплексный дашборд здоровья для жюри и SRE-инженеров.  
  *Возвращает*:
  * Состояние БД: `"ok (postgres)"` или `"ok (sqlite_fallback)"`.
  * Состояние Redis: `"ok (redis)"` или `"degraded (in-memory fallback)"`.
  * Состояние Kafka: `"ready"`.
  * Метрики RAG: `rag_hits`, `rag_queries`, `rag_hit_rate_percent`, `total_chunks`.
  * Uptime и последние 10 пойманных ошибок приложения (`last_errors`).
* **`GET /metrics`**  
  *Назначение*: Экспорт метрик в стандартном формате Prometheus для Grafana.

---

### Группа 2: Конечный автомат ученика (`FSM & Routing`)
* **`POST /api/user/message`**  
  *Вход*: `UserMessageRequest(max_user_id, text, message_id)`.  
  *Логика*:
  1. Проверяет Sliding Window Rate Limiter (10 RPM). При превышении возвращает `429 Too Many Requests` с указанием секунд до разблокировки.
  2. Проверяет состояние FSM: если пользователь новый (`GUEST_CHOICE`), требует пройти экран 152-ФЗ.
  3. Маршрутизирует запрос в Kafka или локальный пайплайн.
* **`POST /api/user/consent`**  
  *Вход*: `ConsentRequest(max_user_id, accepted)`.  
  *Логика*: Фиксирует согласие с 152-ФЗ. При `accepted = false` включает анонимный режим `is_guest = true`. Переводит FSM в `SELECT_INTEREST`.
* **`POST /api/user/interest`**  
  *Вход*: `InterestRequest(max_user_id, interest)`.  
  *Логика*: Сохраняет хобби (`Футбол`, `Видеоигры`, `Музыка` и др.) и переводит FSM в `IDLE`.
* **`GET /api/user/profile/{user_id}`**  
  *Возвращает*: Полный слепок пользователя (класс, хобби, статус гостя, активный квиз).
* **`POST /api/user/reset`**  
  *Назначение*: Полный сброс сессии пользователя до начального выбора 152-ФЗ.

---

### Группа 3: Микро-квизы (`Quiz`)
* **`POST /api/quiz/register`**  
  *Вход*: `QuizRegisterRequest(max_user_id, quiz_id, topic, question, options, correct_option_index)`.  
  *Логика*: Регистрирует сессию квиза в таблице `quiz_sessions` и выставляет `User.current_quiz_id = quiz_id`.
* **`POST /api/quiz/answer`**  
  *Вход*: `QuizAnswerRequest(max_user_id, quiz_id, selected_option_index)`.  
  *Логика*:
  1. **Quiz Freshness Guard**: Сверяет `user.current_quiz_id == quiz_id`. При несовпадении возвращает `status: "stale"`, предотвращая атак повторного клика.
  2. Проверяет корректность ответа, начисляет XP (+50 за верный, +10 за попытку).
  3. Сохраняет результат в PostgreSQL и сбрасывает `current_quiz_id = None`.

---

### Группа 4: Веб-портал ученика (`Student Portal`)
* **`GET /student`** — Автономный одностраничный веб-кабинет школьника (HTML/CSS/JS без внешних CDN).
* **`POST /api/student/ask`** — Отправка вопроса из веб-интерфейса напрямую в сервис объяснений.
* **`POST /api/student/quiz_answer`** — Прохождение проверочного теста в веб-интерфейсе.
* **`POST /api/student/upload_textbook`** — Загрузка PDF-учебника (Multipart Form Data). Сохраняет файл в `data/textbooks/` и запускает формулобезопасный чанкинг и индексацию BM25.
* **`GET /api/student/textbooks`** — Список загруженных и проиндексированных учебных пособий.

---

### Группа 5: Кабинет Учителя (`Dashboard`)
* **`GET /teacher`**  
  *Безопасность*: Защищен `HTTP Basic Auth` (`secrets.compare_digest`).  
  *Рендеринг*: Серверный HTML с встроенным векторным **SVG-графиком активности** и таблицей успеваемости.
* **`GET /api/teacher/export_csv`**  
  *Выгрузка*: Формирует файл `teacher_report.csv` с префиксом `\ufeff` (UTF-8 BOM), готовый для открытия в Excel.

---

## 3. Спецификация Pydantic Data Transfer Objects (DTO)

```python
class UserMessageRequest(BaseModel):
    max_user_id: str
    text: str
    message_id: Optional[str] = None

class ConsentRequest(BaseModel):
    max_user_id: str
    accepted: bool

class InterestRequest(BaseModel):
    max_user_id: str
    interest: str

class QuizAnswerRequest(BaseModel):
    max_user_id: str
    quiz_id: str
    selected_option_index: int

class StudentAskRequest(BaseModel):
    query: str
    interest: Optional[str] = "Футбол"
    grade: Optional[int] = 7
    subject: Optional[str] = "algebra"
```

---

## 4. Стандарты HTTP-статусов и валидация ошибок

| HTTP Код | Описание | Типовая причина в системе |
| :---: | :--- | :--- |
| **`200 OK`** | Успешная обработка | Запрос выполнен, возвращены данные |
| **`400 Bad Request`** | Ошибка клиента | Неверный шаг FSM (например, вопрос до согласия 152-ФЗ) |
| **`401 Unauthorized`** | Ошибка авторизации | Неверный логин/пароль к дашборду учителя (`/teacher`) |
| **`422 Unprocessable`** | Ошибка валидации схемы | Пропущено обязательное поле в JSON или передан неверный тип данных |
| **`429 Too Many Req`** | Превышен лимит (Rate Limit) | Пользователь отправил более 10 сообщений в минуту (`Retry-After: N`) |
| **`500 Internal Error`**| Серверная ошибка | Неперехваченное исключение (автоматически логируется в `LAST_ERRORS`) |

---

[⬅️ Глава 7: Хранилища данных](./07_data_storage_pg_redis.md) · [Оглавление](./README.md) · [Вперед: Масштабирование ➡️](./09_scalability_and_production.md)
