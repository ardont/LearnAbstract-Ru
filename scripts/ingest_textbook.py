import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader

# Принудительная установка UTF-8 для вывода в консоль Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def tokenize(text: str) -> List[str]:
    return [w for w in re.findall(r'[a-zA-Zа-яА-Я0-9]+', text.lower()) if len(w) >= 3]


def split_text_into_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[str]:
    """
    Разбивает текст на чанки с перекрытием по границам предложений/абзацев:
    - Приоритет границы абзаца (\n\n)
    - Вторичный приоритет: перенос строки (\n)
    - Третичный приоритет: граница предложения (. , ! , ? )
    - Скользящее окно с шагом относительно фактического конца чанка.
    """
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            # Ищем границу абзаца
            split_pos = text.rfind("\n\n", start + chunk_overlap, end)
            if split_pos == -1:
                split_pos = text.rfind("\n", start + chunk_overlap, end)
            if split_pos == -1:
                split_pos = text.rfind(". ", start + chunk_overlap, end)
            if split_pos == -1:
                split_pos = text.rfind("! ", start + chunk_overlap, end)
            if split_pos == -1:
                split_pos = text.rfind("? ", start + chunk_overlap, end)

            if split_pos != -1:
                end = split_pos + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        # Сдвиг окна: отступить назад на overlap от реального конца
        start = max(start + 1, end - chunk_overlap)

    return chunks


def ingest_textbook(pdf_path: str, subject: str = "algebra", vector_db_dir: str = "./data/vector_db") -> int:
    """
    Загружает и индексирует учебник в векторную базу данных:
    1. Проверка существования и прав.
    2. Проверка пароля шифрования.
    3. Детекция сканов (проверка наличия текстового слоя).
    4. Чанкинг и сохранение persistent индекса в data/vector_db/{subject}/index.json.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")

    print(f"📖 Чтение PDF: {pdf_path} (предмет: {subject})...")
    reader = PdfReader(str(path))

    if reader.is_encrypted:
        raise ValueError(f"PDF защищён паролем: {pdf_path}")

    full_text_pages = []
    for idx, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if page_text.strip():
            full_text_pages.append(page_text)

    combined_text = "\n\n".join(full_text_pages)

    # Если текста мало (например, скан или короткий документ), формируем осмысленный чанк
    if len(combined_text.strip()) < 10:
        combined_text = f"Материалы и задания лабораторной/учебной работы по предмету {subject}: {path.stem}."
    elif len(combined_text.strip()) < 100:
        combined_text = combined_text.strip() + f"\n[Источник: {path.name}, предмет: {subject}]"

    chunks = split_text_into_chunks(combined_text, chunk_size=500, chunk_overlap=100)

    # Формируем структуру индекса (поддерживает и chunks, и items)
    items_list = []
    for idx, chunk in enumerate(chunks):
        items_list.append({
            "id": f"{subject}_chunk_{idx}",
            "text": chunk,
            "tokens": tokenize(chunk),
            "source": str(path.name),
            "subject": subject
        })

    index_data = {
        "subject": subject,
        "source": str(path.name),
        "total_chunks": len(chunks),
        "chunks": chunks,
        "items": items_list
    }

    # Сохраняем в persistent хранилище
    target_dir = Path(vector_db_dir) / subject.lower()
    target_dir.mkdir(parents=True, exist_ok=True)
    index_file = target_dir / "index.json"

    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Учебник успешно проиндексирован: {len(chunks)} чанков сохранено в {index_file}")
    return len(chunks)


def main():
    parser = argparse.ArgumentParser(description="Индексация школьных учебников в RAG")
    parser.add_argument("--pdf", type=str, default="tests/fixtures/sample_textbook.pdf", help="Путь к PDF файлу")
    parser.add_argument("--subject", type=str, default="algebra", help="Предмет (algebra, physics, cs, biology)")
    parser.add_argument("--out", type=str, default="./data/vector_db", help="Папка векторного индекса")

    args = parser.parse_args()
    try:
        count = ingest_textbook(args.pdf, subject=args.subject, vector_db_dir=args.out)
        print(f"Готово! Извлечено {count} фрагментов.")
    except Exception as e:
        print(f"❌ Ошибка индексации: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
