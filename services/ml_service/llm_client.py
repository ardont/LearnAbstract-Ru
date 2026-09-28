import os
import time
import asyncio
from typing import Dict, Any, Optional, List
import httpx
from services.ml_service.metaphor_engine import get_metaphor
from services.ml_service.guardrails import check_guardrails, OutputGuardrails
from services.ml_service.rag_engine import rag_engine
from shared.utils.text_formatter import latex_to_unicode
from shared.utils.logger import setup_logger

logger = setup_logger("ml_service.llm_client")

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30.0"))


async def generate_explanation(
    topic: str,
    interest: str = "Футбол",
    grade: int = 7,
    subject: Optional[str] = None,
    user_query: Optional[str] = None
) -> Dict[str, Any]:
    """
    Генерирует академическую аналогию с поддержкой RAG и OutputGuardrails:
    1. Проверка входных Guardrails.
    2. При DEMO_MODE=true — мгновенный возврат из 3-уровневого Fallback (180 мс, RAG не нужен).
    3. При DEMO_MODE=false — извлечение контекста из учебника (RAG), вызов LLM и проверка через OutputGuardrails.
    """
    start_time = time.time()
    query_text = user_query or topic

    # 1. Входные Guardrails
    is_safe, safety_msg = check_guardrails(query_text)
    if not is_safe:
        return {
            "text": safety_msg,
            "source": "guardrails",
            "latency_ms": int((time.time() - start_time) * 1000),
            "quiz": None
        }

    # 2. Извлечение фрагментов учебника (RAG)
    context_chunks: List[str] = []
    effective_subject = subject or "algebra"
    if rag_engine.has_subject(effective_subject):
        try:
            context_chunks = rag_engine.retrieve(query_text, effective_subject, k=3)
        except Exception as e:
            logger.warning(f"Ошибка RAG при извлечении контекста: {e}. Продолжение без контекста.")

    # 3. Пакет Demo-Resilience (DEMO_MODE=true) или отсутствие ключа
    if DEMO_MODE or not LLM_API_KEY:
        if DEMO_MODE:
            logger.info(f"[DEMO_MODE=true] Мгновенная выдача аналогии по теме «{topic}» через «{interest}» (RAG hits: {len(context_chunks)})")
        else:
            logger.info(f"LLM_API_KEY не задан. Использование 3-Tier Fallback для «{topic}» (RAG hits: {len(context_chunks)})")

        await asyncio.sleep(0.18)  # 180 мс академический ответ
        result = get_metaphor(topic, interest, grade)
        result["latency_ms"] = int((time.time() - start_time) * 1000)
        result["rag_chunks"] = context_chunks
        result["rag_hits"] = len(context_chunks)
        result["rag_subject"] = effective_subject
        return result

    # 4. Реальный LLM с поддержкой RAG
    context_block = ""
    if context_chunks:
        context_block = (
            "\n\nИспользуй следующие строгие академические определения и факты из школьного учебника:\n"
            + "\n---\n".join(context_chunks)
            + "\n\n"
        )

    system_prompt = (
        f"Ты — опытный репетитор для школьника {grade} класса. "
        f"Твоя задача: объяснить тему «{topic}», используя яркую, точную и увлекательную метафору из сферы «{interest}». "
        f"Объяснение должно быть математически и физически корректным, с формулами (в LaTeX или читаемом виде). "
        f"Не используй токсичные выражения и опасные примеры."
    )

    user_prompt = f"Вопрос ученика: {query_text}{context_block}"

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            resp = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["choices"][0]["message"]["content"]

                # Шаг 4.3: Выходные Guardrails (OutputGuardrails)
                is_valid, reason = OutputGuardrails.validate(raw_text)
                if not is_valid:
                    logger.warning(f"Выходной фильтр заблокировал ответ модели ({reason}). Подмена на безопасный Fallback...")
                else:
                    clean_text = latex_to_unicode(raw_text)
                    meta_fallback = get_metaphor(topic, interest, grade)

                    return {
                        "text": clean_text,
                        "source": "llm_with_rag" if context_chunks else "llm",
                        "latency_ms": int((time.time() - start_time) * 1000),
                        "quiz": meta_fallback.get("quiz"),
                        "rag_chunks": context_chunks,
                        "rag_hits": len(context_chunks),
                        "rag_subject": effective_subject
                    }
            else:
                logger.warning(f"LLM API вернул статус {resp.status_code}. Переход на Fallback...")

    except Exception as e:
        logger.warning(f"Ошибка обращения к LLM ({e}). Автоматический переход на 3-уровневый Fallback...")

    # Автоматический безопасный Fallback
    fallback_res = get_metaphor(topic, interest, grade)
    fallback_res["latency_ms"] = int((time.time() - start_time) * 1000)
    fallback_res["rag_chunks"] = context_chunks
    fallback_res["rag_hits"] = len(context_chunks)
    fallback_res["rag_subject"] = effective_subject
    return fallback_res
