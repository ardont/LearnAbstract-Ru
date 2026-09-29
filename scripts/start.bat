@echo off
chcp 65001 > nul
echo ==============================================================================
echo  «Твой Путь: Абстрактный Репетитор» - Запуск всей системы
echo  Команда: Firstapp (Акмаева Элиза, Хайрутдинов Рамис, Шибаев Сергей)
echo ==============================================================================

if not exist data\textbooks mkdir data\textbooks
if not exist data\vector_db mkdir data\vector_db
if not exist backups mkdir backups
if not exist screenshots mkdir screenshots
if not exist presentation mkdir presentation

if not exist .env (
    echo [INFO] Создание .env из .env.example...
    copy .env.example .env
)

echo [1/3] Запуск Docker Compose (Kafka, Postgres, Redis)...
docker compose up -d kafka kafka-init postgres redis 2>nul

echo [2/3] Инициализация БД и демо-данных (5-7 классы)...
python scripts\seed_demo_data.py

echo [3/3] Запуск сервисов Core, ML и MAX Bot...
python scripts\run_all_local.py
