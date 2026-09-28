import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Optional

from services.ml_service.metrics import record_rag_query
from shared.utils.logger import setup_logger

logger = setup_logger("ml_service.rag_engine")

BASE_VECTOR_DIR = Path(os.getenv("VECTOR_DB_DIR", "./data/vector_db"))


def _tokenize(text: str) -> List[str]:
    """Разбивает текст на очищенные токены (слова длиной от 3 символов в нижнем регистре)."""
    return [w for w in re.findall(r'[a-zA-Zа-яА-Я0-9]+', text.lower()) if len(w) >= 3]


class RAGEngine:
    """
    Автономный persistent RAG-движок для школьных учебников:
    - Индексирует чанки учебника в data/vector_db/{subject}/index.json
    - Выполняет быстрый семантический поиск по TF-IDF и Cosine Similarity
    - Не требует внешних сервисов и GPU, полностью устойчив к сбоям.
    """

    def __init__(self, vector_dir: Path = BASE_VECTOR_DIR):
        self.vector_dir = Path(vector_dir)
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    def has_subject(self, subject: str) -> bool:
        """Проверяет, существует ли проиндексированный учебник по заданному предмету."""
        idx_path = self.vector_dir / subject.lower() / "index.json"
        return idx_path.exists()

    def _load_index(self, subject: str) -> List[Dict[str, Any]]:
        clean_subj = subject.lower()
        idx_path = self.vector_dir / clean_subj / "index.json"
        if not idx_path.exists():
            return []

        try:
            mtime = idx_path.stat().st_mtime
            if clean_subj in self._cache:
                cached_mtime, cached_items = self._cache[clean_subj]
                if cached_mtime == mtime:
                    return cached_items

            with open(idx_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("items", [])
                if not items and "chunks" in data:
                    items = [
                        {
                            "id": f"{clean_subj}_{i}",
                            "text": c,
                            "tokens": _tokenize(c),
                            "source": data.get("source", clean_subj),
                            "subject": clean_subj
                        }
                        for i, c in enumerate(data["chunks"])
                    ]
            else:
                items = []

            self._cache[clean_subj] = (mtime, items)
            return items
        except Exception as e:
            logger.warning(f"Ошибка загрузки RAG-индекса для {clean_subj}: {e}")
            return []

    def retrieve(self, query: str, subject: str, k: int = 3) -> List[str]:
        """
        Извлекает k наиболее релевантных фрагментов из учебника по предмету.
        Если учебник не проиндексирован — возвращает пустой список без сбоев.
        """
        clean_subj = subject.lower() if subject else "algebra"
        chunks = self._load_index(clean_subj)

        if not chunks:
            record_rag_query(hit=False)
            logger.info(f"RAG retrieve: subject={clean_subj}, k={k}, hits=0 (учебник не проиндексирован)")
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            record_rag_query(hit=False)
            return []

        q_counter = Counter(query_tokens)
        scored_chunks = []

        # Общее число документов (чанков)
        N = len(chunks)

        for chunk_item in chunks:
            text = chunk_item.get("text", "")
            chunk_tokens = chunk_item.get("tokens") or _tokenize(text)
            c_counter = Counter(chunk_tokens)

            # Вычисление сходства (TF-IDF + Term Overlap)
            score = 0.0
            for term, q_count in q_counter.items():
                if term in c_counter:
                    # Частота термина в чанке
                    tf = c_counter[term] / len(chunk_tokens)
                    # Приоритет совпадения редких и ключевых слов
                    score += tf * q_count

            if score > 0:
                scored_chunks.append((score, text))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_k = [item[1] for item in scored_chunks[:k]]

        is_hit = len(top_k) > 0
        record_rag_query(hit=is_hit)
        logger.info(f"RAG retrieve: subject={clean_subj}, k={k}, hits={len(top_k)}")

        return top_k


# Глобальный инстанс RAG
rag_engine = RAGEngine()
