import asyncio
import os
import signal
import sys
from uvicorn import Config, Server

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.core_service.main import app as core_app
from services.ml_service.main import app as ml_app
from services.bot_service.main import main as run_bot


async def main():
    print("\n" + "=" * 65)
    print("  🚀 ЗАПУСК ВСЕХ СЕРВИСОВ: «ТВОЙ ПУТЬ: АБСТРАКТНЫЙ РЕПЕТИТОР» v5.0")
    print("=" * 65)
    print("  📊 Панель Учителя:     http://localhost:8000/teacher (teacher / change_me_in_production)")
    print("  📑 Swagger UI / Docs:  http://localhost:8000/docs")
    print("  🟢 Живой мониторинг:   http://localhost:8000/health/full")
    print("  📈 Prometheus Метрики: http://localhost:8000/metrics")
    print("  🧠 ML Service Health:  http://localhost:8002/health")
    print("  🤖 Bot Service Health: http://localhost:8001/health")
    print("=" * 65 + "\n")

    # Конфигурация серверов
    core_config = Config(app=core_app, host="0.0.0.0", port=8000, log_level="warning")
    core_server = Server(core_config)

    ml_config = Config(app=ml_app, host="0.0.0.0", port=8002, log_level="warning")
    ml_server = Server(ml_config)

    tasks = [
        asyncio.create_task(core_server.serve(), name="core_service"),
        asyncio.create_task(ml_server.serve(), name="ml_service"),
        asyncio.create_task(run_bot(), name="bot_service")
    ]

    def stop_all(sig, frame):
        print("\nПолучен сигнал остановки. Корректное завершение всех процессов...")
        core_server.should_exit = True
        ml_server.should_exit = True
        for t in tasks:
            t.cancel()

    signal.signal(signal.SIGINT, stop_all)
    signal.signal(signal.SIGTERM, stop_all)

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        print(f"Остановка сервисов: {e}")
    finally:
        print("Все сервисы остановлены.")


if __name__ == "__main__":
    asyncio.run(main())
