#!/bin/bash
# Скрипт создания и ротации резервных копий базы данных (PostgreSQL)

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "🔄 Запуск создания бэкапа базы данных PostgreSQL..."

# Экспорт базы данных
if command -v docker > /dev/null 2>&1 && docker ps | grep -q postgres; then
    docker exec -t $(docker ps -qf "name=postgres") pg_dump -U postgres education | gzip > "${BACKUP_FILE}"
    echo "✅ Бэкап успешно создан через Docker: ${BACKUP_FILE}"
elif command -v pg_dump > /dev/null 2>&1; then
    pg_dump -h localhost -U postgres education | gzip > "${BACKUP_FILE}"
    echo "✅ Бэкап успешно создан локально: ${BACKUP_FILE}"
else
    # Fallback для локальной базы SQLite (если используется Demo-Resilience)
    if [ -f "./core.db" ]; then
        cp ./core.db "${BACKUP_DIR}/core_backup_${TIMESTAMP}.db"
        echo "✅ Создана копия резервной БД SQLite: ${BACKUP_DIR}/core_backup_${TIMESTAMP}.db"
    fi
fi

# Ротация: хранение последних 5 копий
echo "🧹 Очистка старых резервных копий (хранение последних 5)..."
cd "${BACKUP_DIR}" && ls -t db_backup_*.sql.gz 2>/dev/null | tail -n +6 | xargs -r rm --
cd - > /dev/null

echo "🎉 Резервное копирование завершено."
