# «Твой Путь: Абстрактный Репетитор» (v5.2 Ultimate)

AI-репетитор для школьников, который объясняет сложные школьные темы (математику, физику, химию, программирование) через увлечения ученика (**спорт, видеоигры, музыку, космос, кино**), проверяет понимание через интерактивные квизы и транслирует успеваемость в дашборд учителя.

---

## 🏛️ Архитектура

Проект построен по принципам отказоустойчивой микросервисной архитектуры с пакетом **Demo-Resilience (План «Б»)**:
- **Шина событий**: Apache Kafka 3.7.0 в режиме **KRaft** (топики `education.events` и `education.events.dlq`).
- **Core Service (FastAPI, порт 8000)**: FSM учеников, защита от дублей, Rate Limiting (10 RPM), **Quiz Freshness Guard**, дашборд учителя `/teacher`, мониторинг `/health/full` и Prometheus метрики `/metrics`.
- **ML Service (FastAPI, порт 8002)**: **3-уровневый Fallback** (Точный $\to$ Предметный $\to$ General), **RAG по школьным учебникам**, входные и выходные **OutputGuardrails**, режим `DEMO_MODE=true` (ответ за 180 мс без интернета).
- **Bot Service (порт 8001)**: Telegram/MAX бот на `umaxbot`/`maxbot`, **Watchdog-таймер** (45 сек) с отменой, поддержка согласия **152-ФЗ** и гостевого режима (`is_guest=True`).

---

## 🐧 Быстрый старт на Linux (Linux Quickstart)

### 1. Подготовка окружения
```bash
# Установка Docker и плагина Compose
sudo apt update && sudo apt install -y docker.io docker-compose-plugin python3-pip
sudo usermod -aG docker $USER && newgrp docker

# Клонирование и настройка прав
git clone <URL_РЕПОЗИТОРИЯ> && cd repo
sudo chown -R $USER:$USER ./data ./backups
mkdir -p data/textbooks data/vector_db backups
```

### 2. Конфигурация (.env)
```bash
cp .env.example .env
# Заполните токен бота MAX_BOT_TOKEN и пароль учителя TEACHER_PASSWORD в .env
```

### 3. Запуск инфраструктуры (Docker)
```bash
docker compose up -d kafka kafka-init postgres redis
```

### 4. Подготовка базы знаний учебников (RAG)
```bash
# Генерация тестового учебника по алгебре и индексация
python scripts/create_sample_pdf.py
python scripts/ingest_textbook.py --subject algebra --pdf tests/fixtures/sample_textbook.pdf
```

### 5. Инициализация БД и демо-данных
```bash
python scripts/seed_demo_data.py
```

### 6. Экспресс-проверка перед защитой
```bash
python scripts/pre_demo_check.py
# Критерий готовности: 🚀 ALL SYSTEMS GO! YOU ARE READY TO DEMO!
```

### 7. Запуск всех сервисов
```bash
python scripts/run_all_local.py
```

---

## 🔧 Диагностика и решение проблем (Troubleshooting)

### 1. Ошибка: Kafka не стартует или контейнер в статусе Restarting
- **Причина**: Недостаточно прав или не завершилась инициализация KRaft контроллера.
- **Решение**:
  ```bash
  docker compose logs kafka
  docker compose down -v && docker compose up -d kafka kafka-init
  ```

### 2. Ошибка: Порт занят (Port 8000, 8001, 8002, 9092, 5432 или 6379 already in use)
- **Причина**: На машине уже запущен локальный Postgres, Redis или предыдущий процесс.
- **Решение**:
  ```bash
  sudo lsof -i :8000 -i :8002 -i :9092 -i :5432 -i :6379
  # или в Windows PowerShell:
  Get-NetTCPConnection -LocalPort 8000,8002,9092,5432,6379 | Select-Object OwningProcess
  ```

### 3. Ошибка: Permission denied при записи в ./data или ./backups
- **Причина**: Файлы созданы из-под пользователя `root` внутри контейнера.
- **Решение**:
  ```bash
  sudo chown -R $USER:$USER ./data ./backups
  chmod -R 775 ./data ./backups
  ```

### 4. Ошибка: Переменные из `.env` не подхватываются
- **Причина**: Файл `.env` сохранён с BOM (Byte Order Mark) в кодировке UTF-16 или отсутствует в текущей рабочей директории.
- **Решение**: Сохраните `.env` в кодировке `UTF-8 without BOM`. Убедитесь, что запускаете скрипты из папки `repo/`.

### 5. Ошибка: `ValueError: PDF не содержит распознанного текстового слоя`
- **Причина**: Загруженный PDF-учебник является отсканированным растровым изображением без текстового слоя OCR.
- **Решение**: Загрузите PDF с векторным текстовым слоем или прогоните через `tesseract` перед добавлением в `data/textbooks/`.

---

## 🧪 Запуск тестов
```bash
python -m pytest tests/ -v
```
Все 16 автоматических тестов охватывают FSM, Guardrails, DLQ, Idempotency, RAG, LaTeX-форматирование и сквозной E2E.
