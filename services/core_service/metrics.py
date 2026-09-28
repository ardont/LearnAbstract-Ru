import time
from collections import deque
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Prometheus метрики
PROMETHEUS_HTTP_REQUESTS = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint", "status"]
)
PROMETHEUS_LLM_LATENCY = Histogram(
    "llm_latency_seconds", "Latency of LLM generation in seconds",
    buckets=[0.1, 0.3, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
)
PROMETHEUS_FALLBACK_TRIGGERS = Counter(
    "fallback_triggers_total", "Total fallback metaphor triggers", ["level"]
)
PROMETHEUS_EXPLANATIONS_TOTAL = Counter(
    "explanations_total", "Total explanations served", ["source"]
)
PROMETHEUS_ACTIVE_USERS = Gauge(
    "active_users_count", "Currently active users count"
)

# Локальные счетчики для /health/full
_llm_latencies: deque = deque(maxlen=100)
_llm_errors_5min: deque = deque()
_total_explanations_count = 0
_fallback_triggers_count = 0


def record_explanation(latency_ms: int, source: str) -> None:
    global _total_explanations_count, _fallback_triggers_count
    _total_explanations_count += 1
    _llm_latencies.append(latency_ms)

    PROMETHEUS_EXPLANATIONS_TOTAL.labels(source=source).inc()
    PROMETHEUS_LLM_LATENCY.observe(latency_ms / 1000.0)

    if source.startswith("fallback"):
        _fallback_triggers_count += 1
        level = source.replace("fallback_", "")
        PROMETHEUS_FALLBACK_TRIGGERS.labels(level=level).inc()


def record_llm_error() -> None:
    now = time.time()
    _llm_errors_5min.append(now)


def get_llm_errors_last_5min() -> int:
    now = time.time()
    threshold = now - 300.0
    while _llm_errors_5min and _llm_errors_5min[0] < threshold:
        _llm_errors_5min.popleft()
    return len(_llm_errors_5min)


def get_metrics_summary() -> Dict[str, Any]:
    avg_latency = (
        round(sum(_llm_latencies) / len(_llm_latencies), 1)
        if _llm_latencies else 0.0
    )
    return {
        "total_explanations": _total_explanations_count,
        "fallback_triggers_total": _fallback_triggers_count,
        "avg_latency_ms": avg_latency,
        "llm_errors_last_5min": get_llm_errors_last_5min()
    }


def render_prometheus_metrics() -> bytes:
    return generate_latest()
