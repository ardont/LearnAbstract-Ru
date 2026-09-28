import asyncio
import os
import sys
import time
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from services.ml_service.llm_client import generate_explanation


async def main():
    print("\n" + "=" * 65)
    print("  🧪 ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ ОБЪЯСНЕНИЙ (LLM / FALLBACK / RAG)")
    print("=" * 65)

    test_cases = [
        ("Квадратные уравнения", "Футбол", "algebra"),
        ("Закон Ома", "Видеоигры", "physics"),
        ("Фотосинтез", "Кино", "biology"),
        ("Теорема Пифагора", "Космос", "algebra"),
    ]

    for topic, hobby, subject in test_cases:
        print(f"\nТема: «{topic}» | Хобби: {hobby} | Предмет: {subject}")
        print("-" * 50)
        t0 = time.time()
        res = await generate_explanation(
            topic=topic,
            interest=hobby,
            grade=7,
            subject=subject,
            user_query=f"Объясни мне {topic} через {hobby}"
        )
        elapsed = time.time() - t0

        text = res.get("text", "")
        source = res.get("source", "unknown")
        latency = res.get("latency_ms", int(elapsed * 1000))

        print(f"Источник: [{source}] | Задержка: {latency}ms")
        print(f"Ответ:\n{text[:300]}...")

        assert len(text) > 50, "Ответ слишком короткий"
        assert res.get("quiz") is not None, "Квиз должен быть сгенерирован"
        print("✅ Проверка пройдена!")

    print("\n" + "=" * 65)
    print("  🎉 ВСЕ ТЕСТОВЫЕ КЕЙСЫ ГЕНЕРАЦИИ УСПЕШНО ВЫПОЛНЕНЫ!")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
