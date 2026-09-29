@echo off
chcp 65001 > nul
echo [INFO] Остановка Python-сервисов...
taskkill /F /FI "WINDOWTITLE eq *run_all_local.py*" 2>nul
echo [INFO] Остановка Docker контейнеров (volumes сохранены)...
docker compose stop
echo [OK] Все сервисы остановлены.
