#!/usr/bin/env bash
# ==============================================================================
# «Твой Путь: Абстрактный Репетитор» — Скрипт быстрого запуска всей системы
# Команда: Firstapp (Акмаева Элиза, Хайрутдинов Рамис, Шибаев Сергей)
# ==============================================================================
set -e

echo "🚀 [1/5] Проверка зависимостей и окружения..."
if ! command -v docker &> /dev/null; then
    echo "⚠️ Docker не найден. Установите Docker & Docker Compose для запуска инфраструктуры."
fi

mkdir -p data/textbooks data/vector_db backups screenshots presentation

# Проверка наличия .env
if [ ! -f .env ]; then
    echo "📄 Файл .env не найден. Копирование из .env.example..."
    cp .env.example .env
fi

echo "🐳 [2/5] Запуск инфраструктурных сервисов (Kafka KRaft, Postgres, Redis)..."
if command -v docker &> /dev/null; then
    docker compose up -d kafka kafka-init postgres redis 2>/dev/null || echo "ℹ️ Docker compose пропущен или уже запущен"
fi

echo "⏳ [3/5] Ожидание готовности брокера и БД (3 сек)..."
sleep 3

echo "📦 [4/5] Применение миграций и загрузка демонстрационных данных (5-7 классы)..."
python scripts/seed_demo_data.py || true

echo "✨ [5/5] Запуск микросервисов (Core :8000, ML :8002, Bot :8001)..."
echo "=========================================================================="
echo "  🎓 Портал Ученика:     http://localhost:8000/student"
echo "  📊 Дашборд Учителя:    http://localhost:8000/teacher (teacher / change_me_in_production)"
echo "  📑 Swagger UI / Docs:  http://localhost:8000/docs"
echo "  🟢 Health Мониторинг:  http://localhost:8000/health/full"
echo "  📈 Метрики:            http://localhost:8000/metrics"
echo "  🤖 Чат-бот в MAX:      https://max.ru/t569_hakaton_max_bot"
echo "=========================================================================="

python scripts/run_all_local.py
