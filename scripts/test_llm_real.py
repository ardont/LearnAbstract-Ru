import asyncio
import json
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
        {
            "topic": "Квадратные уравнения",
            "hobby": "Футбол",
            "subject": "algebra",
            "formula_keywords": ["x²", "ax²", "b²", "D =", "x =", "дискриминант"],
        },
        {
            "topic": "Закон Ома",
            "hobby": "Видеоигры",
            "subject": "physics",
            "formula_keywords": ["I =", "U =", "R", "Ом", "напряжен", "ток"],
        },
        {
            "topic": "Теорема Пифагора",
            "hobby": "Космос",
            "subject": "geometry",
            "formula_keywords": ["a²", "b²", "c²", "гипотенуз", "катет"],
        },
        {
            "topic": "Фотосинтез",
            "hobby": "Музыка",
            "subject": "biology",
            "formula_keywords": ["CO₂", "H₂O", "O₂", "углекисл", "хлорофилл", "глюкоз"],
        },
    ]

    results = []

    for tc in test_cases:
        topic = tc["topic"]
        hobby = tc["hobby"]
        subject = tc["subject"]

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
        latency_ms = res.get("latency_ms", int(elapsed * 1000))
        quiz = res.get("quiz")

        print(f"Источник: [{source}] | Задержка: {latency_ms}ms ({elapsed:.2f}s)")
        print(f"Ответ (первые 200 симв.):\n{text[:200]}...")

        # Assertions
        assert elapsed < 30.0, f"Задержка слишком велика ({elapsed:.2f}s > 30s)"
        assert len(text) > 80, f"Ответ слишком короткий ({len(text)} символов)"
        assert quiz is not None, "Квиз должен быть сгенерирован"
        assert len(quiz.get("options", [])) >= 3, "Квиз должен содержать минимум 3 опции"

        # Formula / keyword check
        found_kw = [kw for kw in tc["formula_keywords"] if kw.lower() in text.lower()]
        assert len(found_kw) > 0, f"В тексте для темы '{topic}' не найдено ключевых формул/терминов из {tc['formula_keywords']}"
        print(f"Найденные формулы/ключевые термины: {found_kw}")
        print("✅ Проверка пройдена!")

        results.append({
            "topic": topic,
            "hobby": hobby,
            "subject": subject,
            "source": source,
            "latency_ms": latency_ms,
            "elapsed_seconds": round(elapsed, 3),
            "text_length": len(text),
            "quiz_present": bool(quiz),
            "found_keywords": found_kw,
            "passed": True
        })

    # Save output to C:/tmp/llm_test_results.json
    output_path = "C:/tmp/llm_test_results.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": time.time(), "test_results": results}, f, ensure_ascii=False, indent=2)
    print(f"\n📁 Результаты сохранены в: {output_path}")

    print("\n" + "=" * 65)
    print("  🎉 ВСЕ 4 ТЕСТОВЫХ КЕЙСА ГЕНЕРАЦИИ УСПЕШНО ВЫПОЛНЕНЫ!")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

