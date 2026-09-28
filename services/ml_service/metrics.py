from prometheus_client import Counter

# Prometheus метрики для RAG
PROMETHEUS_RAG_QUERIES = Counter(
    "rag_queries_total", "Общее количество поисковых запросов в базу учебников"
)
PROMETHEUS_RAG_HITS = Counter(
    "rag_hits_total", "Количество запросов с найденным релевантным контекстом из учебника"
)

_local_rag_queries = 0
_local_rag_hits = 0


def record_rag_query(hit: bool = False):
    global _local_rag_queries, _local_rag_hits
    _local_rag_queries += 1
    PROMETHEUS_RAG_QUERIES.inc()
    if hit:
        _local_rag_hits += 1
        PROMETHEUS_RAG_HITS.inc()


def get_rag_metrics_summary() -> dict:
    hit_rate = (
        round((_local_rag_hits / _local_rag_queries) * 100, 1)
        if _local_rag_queries > 0 else 0.0
    )
    return {
        "rag_queries_total": _local_rag_queries,
        "rag_hits_total": _local_rag_hits,
        "rag_hit_rate_pct": hit_rate
    }
