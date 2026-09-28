import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.ml_service.rag_engine import rag_engine
from scripts.ingest_textbook import ingest_textbook


def test_rag_retrieval_algebra():
    # 1. Индексируем тестовый учебник
    pdf_path = "tests/fixtures/sample_textbook.pdf"
    assert os.path.exists(pdf_path), "Фикстура tests/fixtures/sample_textbook.pdf должна существовать"
    
    count = ingest_textbook(pdf_path, subject="algebra")
    assert count > 0

    # 2. Проверяем наличие предмета
    assert rag_engine.has_subject("algebra") is True

    # 3. Извлекаем фрагменты по запросу
    docs = rag_engine.retrieve("квадратные уравнения дискриминант формула", subject="algebra", k=2)
    assert len(docs) > 0

    combined = " ".join(docs).lower()
    assert "квадратн" in combined
    assert "дискриминант" in combined or "ax^2" in combined


def test_rag_graceful_degradation_missing_subject():
    # Проверка устойчивости: неизвестный предмет не вызывает исключений
    assert rag_engine.has_subject("astronomy_unknown_subject") is False
    docs = rag_engine.retrieve("пульсары и квазары", subject="astronomy_unknown_subject", k=3)
    assert docs == []
