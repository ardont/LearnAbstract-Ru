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

# Стоп-слова русского языка для качественной фильтрации RAG
RUSSIAN_STOP_WORDS = {
    "и", "в", "во", "на", "с", "со", "по", "для", "из", "изо", "к", "ко", "о", "об", "обо",
    "а", "но", "да", "или", "что", "это", "как", "так", "все", "всё", "они", "она", "он", "оно",
    "мы", "вы", "я", "ты", "бы", "ли", "же", "от", "до", "при", "за", "над", "под", "перед",
    "только", "уже", "если", "где", "куда", "откуда", "который", "какой", "чей", "чем", "причем",
    "есть", "был", "была", "были", "будет", "быть"
}

# Опциональная загрузка pymorphy3 для нормализации словоформ
_morph = None
try:
    import pymorphy3
    _morph = pymorphy3.MorphAnalyzer()
    logger.info("pymorphy3 успешно подключен для лемматизации RAG.")
except Exception:
    logger.info("pymorphy3 не установлен. Используется автономный regex-токенизатор со стеммингом.")


def _stem_simple(token: str) -> str:
    """Легковесный русский стеммер для базового усечения окончаний (когда нет pymorphy3)."""
    if len(token) <= 4:
        return token
    # Срезаем типичные окончания падежей и спряжений
    for suffix in ("ами", "ями", "ов", "ев", "ей", "ия", "ие", "ий", "ый", "ой", "ая", "ое", "ые", "ым", "ом", "ам", "ем", "ать", "ить", "ет", "ут", "ют", "ит", "ат", "ят"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[:-len(suffix)]
    return token


def _tokenize(text: str) -> List[str]:
    """
    Улучшенная русско-латинская токенизация:
    1. Поиск слов длиной от 3 символов (кириллица, латиница, цифры).
    2. Фильтрация русских стоп-слов.
    3. Лемматизация через pymorphy3 или эвристический стемминг.
    """
    if not text:
        return []

    raw_words = re.findall(r'[a-zA-Zа-яёА-ЯЁ0-9]+', text.lower())
    tokens = []
    for w in raw_words:
        if len(w) < 3 or w in RUSSIAN_STOP_WORDS:
            continue
        if _morph:
            try:
                lemma = _morph.parse(w)[0].normal_form
                tokens.append(lemma)
                continue
            except Exception:
                pass
        tokens.append(_stem_simple(w))

    return tokens


class BM25Okapi:
    """Чистая автономная реализация алгоритма BM25 Okapi без внешних тяжелых зависимостей."""

    def __init__(self, corpus_tokens: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus_tokens)
        self.doc_lens = [len(doc) for doc in corpus_tokens]
        self.avgdl = sum(self.doc_lens) / self.corpus_size if self.corpus_size > 0 else 1.0

        # Считаем DF (Document Frequency) для каждого токена
        self.df = Counter()
        for doc in corpus_tokens:
            unique_tokens = set(doc)
            for t in unique_tokens:
                self.df[t] += 1

        # Вычисляем IDF
        self.idf = {}
        for term, freq in self.df.items():
            # Стандартная формула Lucene / Okapi BM25 с защитой от отрицательных значений
            self.idf[term] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query_tokens: List[str], doc_tokens_list: List[List[str]]) -> List[float]:
        scores = []
        q_counter = Counter(query_tokens)

        for idx, doc_tokens in enumerate(doc_tokens_list):
            doc_len = self.doc_lens[idx]
            d_counter = Counter(doc_tokens)
            score = 0.0

            for q_term, q_count in q_counter.items():
                if q_term not in d_counter:
                    continue
                tf = d_counter[q_term]
                idf = self.idf.get(q_term, 0.0)
                # Числитель и знаменатель BM25
                num = tf * (self.k1 + 1.0)
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avgdl))
                score += idf * (num / denom) * q_count

            scores.append(score)

        return scores


class RAGEngine:
    """
    Автономный persistent RAG-движок для школьных учебников:
    - Индексирует чанки учебника в data/vector_db/{subject}/index.json
    - Выполняет точный поиск по алгоритму BM25 Okapi с русской токенизацией
    - Не требует внешних сервисов и GPU, полностью устойчив к сбоям.
    """

    def __init__(self, vector_dir: Path = BASE_VECTOR_DIR):
        self.vector_dir = Path(vector_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def has_subject(self, subject: str) -> bool:
        """Проверяет, существует ли проиндексированный учебник по заданному предмету."""
        idx_path = self.vector_dir / subject.lower() / "index.json"
        return idx_path.exists()

    def _load_index(self, subject: str) -> Optional[Dict[str, Any]]:
        clean_subj = subject.lower()
        idx_path = self.vector_dir / clean_subj / "index.json"
        if not idx_path.exists():
            return None

        try:
            mtime = idx_path.stat().st_mtime
            if clean_subj in self._cache:
                cached_data = self._cache[clean_subj]
                if cached_data.get("mtime") == mtime:
                    return cached_data

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

            # Подготавливаем токены и обучаем модель BM25
            corpus_tokens = []
            for item in items:
                tokens = _tokenize(item.get("text", ""))
                item["tokens"] = tokens
                corpus_tokens.append(tokens)

            bm25_model = BM25Okapi(corpus_tokens) if corpus_tokens else None

            cached_entry = {
                "mtime": mtime,
                "items": items,
                "corpus_tokens": corpus_tokens,
                "bm25": bm25_model
            }
            self._cache[clean_subj] = cached_entry
            return cached_entry

        except Exception as e:
            logger.warning(f"Ошибка загрузки RAG-индекса для {clean_subj}: {e}")
            return None

    def retrieve(self, query: str, subject: str, k: int = 3) -> List[str]:
        """
        Извлекает k наиболее релевантных фрагментов из учебника по предмету через BM25.
        Если учебник не проиндексирован — возвращает пустой список без сбоев.
        """
        clean_subj = subject.lower() if subject else "algebra"
        index_data = self._load_index(clean_subj)

        if not index_data or not index_data["items"] or not index_data["bm25"]:
            record_rag_query(hit=False)
            logger.info(f"RAG retrieve: subject={clean_subj}, k={k}, hits=0 (учебник не проиндексирован)")
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            record_rag_query(hit=False)
            return []

        items = index_data["items"]
        corpus_tokens = index_data["corpus_tokens"]
        bm25: BM25Okapi = index_data["bm25"]

        scores = bm25.get_scores(query_tokens, corpus_tokens)

        # Ранжируем чанки с ненулевым сходством
        scored_chunks = []
        for idx, score in enumerate(scores):
            if score > 0:
                text = items[idx].get("text", "")
                # Дополнительный буст точного вхождения терминов запроса
                exact_boost = 0.0
                text_lower = text.lower()
                for q_word in query.lower().split():
                    if len(q_word) >= 4 and q_word in text_lower:
                        exact_boost += 0.5
                scored_chunks.append((score + exact_boost, text))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_k = [item[1] for item in scored_chunks[:k]]

        is_hit = len(top_k) > 0
        record_rag_query(hit=is_hit)
        logger.info(f"RAG retrieve: subject={clean_subj}, k={k}, hits={len(top_k)}")

        return top_k


# Глобальный инстанс RAG
rag_engine = RAGEngine()
