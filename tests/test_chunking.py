import tempfile
from pathlib import Path
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from scripts.ingest_textbook import split_text_into_chunks, ingest_textbook


def test_chunking_short_text():
    """1. Короткий текст (меньше chunk_size=1000) должен давать ровно 1 чанк."""
    text = "Квадратные уравнения — это фундамент школьной алгебры 8 класса."
    chunks = split_text_into_chunks(text, chunk_size=1000, chunk_overlap=200)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunking_long_text():
    """2. Длинный текст должен разбиваться на множество чанков с перекрытием."""
    paragraph = "Теория дискриминанта позволяет находить корни уравнения вида ax² + bx + c = 0. " * 30
    long_text = "\n\n".join([paragraph for _ in range(5)])
    assert len(long_text) > 5000

    chunks = split_text_into_chunks(long_text, chunk_size=1000, chunk_overlap=200)
    assert len(chunks) >= 5
    for chunk in chunks:
        assert len(chunk) <= 1200  # Допустимый предел с учетом границ слов и формул
        assert len(chunk) > 0


def test_chunking_preserves_formulas():
    """3. Текст с математическими формулами ($...$, $$...$$, \\begin{...}) не должен разрывать формулы пополам."""
    filler = "Академический материал по высшей математике и школьной алгебре. " * 15
    f1 = "$x_{1,2} = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$"
    f2 = "$$D = b^2 - 4ac$$"
    f3 = "\\begin{matrix} 1 & 0 \\\\ 0 & 1 \\end{matrix}"

    text = f"{filler} Формула корней: {f1}. {filler} Дискриминант: {f2}. {filler} Матрица: {f3}. {filler}"
    chunks = split_text_into_chunks(text, chunk_size=800, chunk_overlap=150)

    for i, chunk in enumerate(chunks):
        # Количество знаков $ должно быть четным (формула не обрезана наполовину)
        dollar_count = chunk.count("$")
        assert dollar_count % 2 == 0, f"Формула со знаком $ разорвана в чанке {i}: {chunk}"

        # Теги LaTeX окружений должны быть сбалансированы
        if "\\begin{" in chunk:
            assert "\\end{" in chunk, f"LaTeX окружение разорвано в чанке {i}: {chunk}"


def test_chunking_splits_by_paragraphs():
    """4. Текст с явными абзацами должен разделяться по границам абзацев, не разрывая слова."""
    p1 = "Первый абзац подробно объясняет определение параболы как графика квадратичной функции."
    p2 = "Второй абзац рассматривает вершину параболы и координаты x_0 = -b / (2a)."
    p3 = "Третий абзац описывает направление ветвей параболы в зависимости от знака коэффициента a."

    text = f"{p1}\n\n{p2}\n\n{p3}"
    chunks = split_text_into_chunks(text, chunk_size=120, chunk_overlap=20)

    assert len(chunks) >= 3
    # Проверяем, что чанки начинаются и заканчиваются целыми словами
    for chunk in chunks:
        words = chunk.split()
        assert len(words) > 0
        w_start = words[0].strip(".,!?:;()[]{}\"'").replace('_', '')
        w_end = words[-1].strip(".,!?:;()[]{}\"'").replace('_', '')
        assert w_start.isalnum() or words[0].startswith("$")
        assert w_end.isalnum() or words[-1].endswith("$")


def test_chunking_empty_text():
    """5. Пустой текст или текст из одних пробелов должен возвращать 0 чанков."""
    assert split_text_into_chunks("") == []
    assert split_text_into_chunks("   \n\n\t  ") == []
    assert split_text_into_chunks(None) == []


def test_chunking_pdf_20_plus_pages(tmp_path):
    """6. Загрузка реального PDF на 20+ страниц должна давать > 100 чанков."""
    pdf_path = tmp_path / "comprehensive_25pages.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)

    for p in range(1, 26):
        for i in range(40):
            c.drawString(
                40,
                780 - i * 18,
                f"Page {p} Line {i}: Теория квадратичной функции, вычисление корней через дискриминант D = b^2 - 4ac, вершины параболы и теорема Виета. " * 2
            )
        c.showPage()
    c.save()

    vdb_dir = tmp_path / "vector_db"
    count = ingest_textbook(str(pdf_path), subject="algebra", vector_db_dir=str(vdb_dir))
    assert count > 100, f"Ожидалось > 100 чанков, получено: {count}"
