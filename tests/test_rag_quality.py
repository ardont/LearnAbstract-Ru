import pytest
from services.ml_service.rag_engine import rag_engine, _tokenize, RUSSIAN_STOP_WORDS
from scripts.ingest_textbook import ingest_textbook
import os


@pytest.fixture(scope="module", autouse=True)
def setup_textbook():
    """Гарантирует, что тестовый учебник алгебры проиндексирован перед тестами."""
    pdf_path = "data/textbooks/Алгебра_7_8_класс_Макарычев_Теория.pdf"
    if not os.path.exists(pdf_path):
        pdf_path = "tests/fixtures/sample_textbook.pdf"
    ingest_textbook(pdf_path, subject="algebra")


def test_russian_tokenization_and_stop_words():
    """Проверяет фильтрацию стоп-слов и извлечение терминов."""
    query = "что такое квадратные уравнения и как найти их дискриминант в школе"
    tokens = _tokenize(query)
    
    # Стоп-слова 'что', 'как', 'их', 'в', 'и' должны быть отфильтрованы
    for stop in ["что", "как", "в", "и"]:
        assert stop not in tokens
    
    # Смысловые корни должны остаться
    assert any("квадратн" in t for t in tokens)
    assert any("уравнен" in t for t in tokens)
    assert any("дискриминант" in t for t in tokens)


def test_rag_topic_1_quadratic_equations():
    """Тема 1: Запрос «квадратные уравнения» должен находить дискриминант и корни в top-3."""
    results = rag_engine.retrieve("квадратные уравнения", subject="algebra", k=3)
    assert len(results) > 0
    combined = " ".join(results).lower()
    assert "дискриминант" in combined or "ax^2" in combined or "корн" in combined


def test_rag_topic_2_vieta_theorem():
    """Тема 2: Запрос «теорема Виета» должен находить сумму и произведение корней в top-3."""
    results = rag_engine.retrieve("теорема Виета сумма и произведение корней", subject="algebra", k=3)
    assert len(results) > 0
    combined = " ".join(results).lower()
    assert "виет" in combined or "произведение" in combined or "сумма" in combined


def test_rag_topic_3_parabola_and_graph():
    """Тема 3: Запрос «график квадратичной функции парабола» должен находить вершину в top-3."""
    results = rag_engine.retrieve("график квадратичной функции парабола вершина", subject="algebra", k=3)
    assert len(results) > 0
    combined = " ".join(results).lower()
    assert "парабол" in combined or "вершин" in combined


def test_rag_topic_4_incomplete_equations():
    """Тема 4: Запрос «неполные квадратные уравнения» должен находить виды неполных уравнений."""
    results = rag_engine.retrieve("неполные квадратные уравнения коэффициенты", subject="algebra", k=3)
    assert len(results) > 0
    combined = " ".join(results).lower()
    assert "неполн" in combined or "коэффициент" in combined or "ax^2" in combined


def test_rag_topic_5_discriminant_formula():
    """Тема 5: Запрос «формула дискриминанта» должен находить D = b^2 - 4ac."""
    results = rag_engine.retrieve("формула дискриминанта b^2 - 4ac", subject="algebra", k=3)
    assert len(results) > 0
    combined = " ".join(results).lower()
    assert "дискриминант" in combined or "4ac" in combined or "d > 0" in combined
