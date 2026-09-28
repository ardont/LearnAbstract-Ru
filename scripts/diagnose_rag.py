import json
import os
import sys
from pathlib import Path
from pypdf import PdfReader

def check_pdf(pdf_path: str):
    print("=" * 60)
    print(f"🔍 ДИАГНОСТИКА PDF: {pdf_path}")
    print("=" * 60)
    p = Path(pdf_path)
    if not p.exists():
        print(f"❌ Файл не найден: {pdf_path}")
        return

    print(f"Размер файла: {p.stat().st_size / 1024 / 1024:.2f} МБ")
    reader = PdfReader(str(p))
    print(f"Всего страниц: {len(reader.pages)}")
    print(f"Зашифрован: {reader.is_encrypted}")

    total_chars = 0
    non_empty_pages = 0
    page_stats = []

    for i, page in enumerate(reader.pages):
        txt = page.extract_text() or ""
        char_len = len(txt.strip())
        if char_len > 0:
            non_empty_pages += 1
            total_chars += char_len
        if i < 5 or char_len > 0:
            page_stats.append((i + 1, char_len))

    print(f"Страниц с текстовым слоем: {non_empty_pages} из {len(reader.pages)}")
    print(f"Всего извлечено символов текста: {total_chars}")
    print("Статистика первых страниц (номер: символов):", page_stats[:10])

    if len(reader.pages) > 0:
        first_txt = reader.pages[0].extract_text() or ""
        print("\n--- Первые 300 символов страницы 1 ---")
        print(repr(first_txt[:300]))


def check_index(index_path: str):
    print("\n" + "=" * 60)
    print(f"📊 ПРОВЕРКА ИНДЕКСА: {index_path}")
    print("=" * 60)
    p = Path(index_path)
    if not p.exists():
        print(f"❌ Индекс не найден: {index_path}")
        return

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        print(f"Всего чанков в индексе: {len(data)}")
        for i, item in enumerate(data[:3]):
            txt = item.get("text", "")
            print(f"\n--- Чанк #{i} ({len(txt)} симв., source={item.get('source')}) ---")
            print(txt[:250])
    elif isinstance(data, dict):
        chunks = data.get("chunks", [])
        print(f"Формат dict, чанков: {len(chunks)}")


if __name__ == "__main__":
    pdf = sys.argv[1] if len(sys.argv) > 1 else "data/textbooks/Современные Компьютерные Науки.pdf"
    idx = sys.argv[2] if len(sys.argv) > 2 else "data/vector_db/algebra/index.json"
    check_pdf(pdf)
    check_index(idx)
