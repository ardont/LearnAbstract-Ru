import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader

# Принудительная установка UTF-8 для вывода в консоль Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


from services.ml_service.rag_engine import _tokenize as tokenize


def get_formula_spans(text: str) -> List[Tuple[int, int]]:
    """Находит диапазоны математических формул, которые нельзя разрывать."""
    spans = []
    # Блочные формулы $$ ... $$
    for m in re.finditer(r'\$\$[^\$]+\$\$', text, re.DOTALL):
        spans.append((m.start(), m.end()))
    # Строчные формулы $ ... $
    for m in re.finditer(r'\$[^\$]+\$', text):
        spans.append((m.start(), m.end()))
    # Окружения LaTeX \begin{...} ... \end{...}
    for m in re.finditer(r'\\begin\{[a-zA-Z0-9*]+\}.*?\\end\{[a-zA-Z0-9*]+\}', text, re.DOTALL):
        spans.append((m.start(), m.end()))
    return sorted(spans, key=lambda x: x[0])


def split_text_into_chunks(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Разбивает текст на чанки по 1000 символов с overlap 200:
    - Защита формул ($...$, $$...$$, \\begin{...}): формулы не режутся пополам.
    - Защита слов: слова не режутся пополам.
    - Приоритет границ: \\n\\n (абзац) -> \\n (строка) -> [.!?] (предложение) -> пробел.
    """
    if not text or not text.strip():
        return []

    clean_text = text.strip()
    text_len = len(clean_text)

    if text_len <= chunk_size:
        return [clean_text]

    formula_spans = get_formula_spans(clean_text)

    def is_inside_formula(pos: int) -> bool:
        return any(s < pos < e for s, e in formula_spans)

    chunks = []
    start = 0

    while start < text_len:
        if text_len - start <= chunk_size:
            chunk = clean_text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        max_end = min(start + chunk_size, text_len)
        min_split = max(start + 1, max_end - (chunk_size - chunk_overlap))

        split_pos = -1

        # 1. Приоритет: граница абзаца (\n\n)
        for m in re.finditer(r'\n\n+', clean_text[min_split:max_end]):
            pos = min_split + m.end()
            if not is_inside_formula(pos):
                split_pos = pos

        # 2. Вторичный приоритет: перевод строки (\n)
        if split_pos == -1:
            for m in re.finditer(r'\n+', clean_text[min_split:max_end]):
                pos = min_split + m.end()
                if not is_inside_formula(pos):
                    split_pos = pos

        # 3. Третичный приоритет: граница предложения (. ! ?)
        if split_pos == -1:
            for m in re.finditer(r'[\.\!\?]\s+', clean_text[min_split:max_end]):
                pos = min_split + m.end()
                if not is_inside_formula(pos):
                    split_pos = pos

        # 4. Граница слова (пробельные символы)
        if split_pos == -1:
            for m in re.finditer(r'\s+', clean_text[min_split:max_end]):
                pos = min_split + m.end()
                if not is_inside_formula(pos):
                    split_pos = pos

        # Если граница внутри формулы, сдвигаем до начала или конца формулы
        if split_pos == -1:
            for s, e in formula_spans:
                if s < max_end < e:
                    if s > start:
                        split_pos = s
                    else:
                        split_pos = e
                    break

        if split_pos == -1 or split_pos <= start:
            split_pos = max_end

        chunk = clean_text[start:split_pos].strip()
        if chunk:
            chunks.append(chunk)

        next_start = max(start + 1, split_pos - chunk_overlap)

        # Не начинаем чанк внутри формулы
        for s, e in formula_spans:
            if s <= next_start < e:
                if s > start and (split_pos - s) <= chunk_size:
                    next_start = s
                else:
                    next_start = e

        # Не режем слово пополам при переходе на следующий чанк
        if not is_inside_formula(next_start):
            if next_start < text_len and clean_text[next_start].isalnum() and next_start > 0 and clean_text[next_start - 1].isalnum():
                m = re.search(r'\s+', clean_text[next_start:split_pos])
                if m and not is_inside_formula(next_start + m.end()):
                    next_start = next_start + m.end()

        while next_start < text_len and clean_text[next_start].isspace():
            next_start += 1

        if next_start <= start:
            next_start = split_pos

        start = next_start

    return chunks


def ingest_textbook(pdf_path: str, subject: str = "algebra", vector_db_dir: str = "./data/vector_db") -> int:
    """
    Загружает и индексирует учебник в векторную базу данных:
    1. Чтение PDF с постраничным извлечением текста.
    2. Проверка шифрования и детекция сканов.
    3. Чанкинг на 1000 символов с overlap 200, с сохранением page_number и chunk_id.
    4. Сохранение persistent индекса в data/vector_db/{subject}/index.json.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")

    print(f"📖 Чтение PDF: {pdf_path} (предмет: {subject})...")
    reader = PdfReader(str(path))

    if reader.is_encrypted:
        raise ValueError(f"PDF защищён паролем: {pdf_path}")

    items_list = []
    all_chunks = []
    chunk_counter = 0

    # Обрабатываем каждую страницу отдельно, чтобы точно знать page_number
    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue

        page_chunks = split_text_into_chunks(page_text, chunk_size=1000, chunk_overlap=200)
        for chunk in page_chunks:
            chunk_id = f"{subject}_p{page_num}_c{chunk_counter}"
            chunk_item = {
                "id": chunk_id,
                "text": chunk,
                "tokens": tokenize(chunk),
                "source": str(path.name),
                "subject": subject,
                "page_number": page_num,
                "char_count": len(chunk)
            }
            items_list.append(chunk_item)
            all_chunks.append(chunk)
            chunk_counter += 1

    # Если текста мало (например, скан), создаем информативный fallback-чанк
    if not all_chunks:
        fallback_chunk = f"Материалы и задания учебного курса по предмету {subject}: {path.stem}."
        chunk_id = f"{subject}_p1_c0"
        items_list.append({
            "id": chunk_id,
            "text": fallback_chunk,
            "tokens": tokenize(fallback_chunk),
            "source": str(path.name),
            "subject": subject,
            "page_number": 1,
            "char_count": len(fallback_chunk)
        })
        all_chunks.append(fallback_chunk)

    index_data = {
        "subject": subject,
        "source": str(path.name),
        "total_chunks": len(all_chunks),
        "chunks": all_chunks,
        "items": items_list
    }

    target_dir = Path(vector_db_dir) / subject.lower()
    target_dir.mkdir(parents=True, exist_ok=True)
    index_file = target_dir / "index.json"

    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Учебник успешно проиндексирован: {len(all_chunks)} чанков сохранено в {index_file}")
    return len(all_chunks)


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
