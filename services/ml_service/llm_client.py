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
    Академический генератор метафор с соблюдением 5 правил RAG-пайплайна:
    1. Если DEMO_MODE=true -> сразу Fallback, RAG не трогать.
    2. Если subject задан и RAG нашёл контекст -> передать в LLM.
    3. Если RAG не нашёл -> LLM без контекста.
    4. Если LLM упал -> Fallback.
    5. Ответ прошёл OutputGuardrails -> вернуть. Не прошёл -> Fallback.
    """
    start_time = time.time()
    query_text = user_query or topic

    # 1. Входные Guardrails безопасности
    is_safe, safety_msg = check_guardrails(query_text)
    if not is_safe:
        return {
            "text": safety_msg,
            "source": "guardrails",
            "latency_ms": int((time.time() - start_time) * 1000),
            "quiz": None,
            "rag_hits": 0,
            "rag_chunks": []
        }

    # Правило 1: Если DEMO_MODE=true или нет API ключа -> сразу Fallback, RAG не трогать!
    if DEMO_MODE or not LLM_API_KEY:
        if DEMO_MODE:
            logger.info(f"[DEMO_MODE=true] Мгновенный переход к Fallback по теме «{topic}» (RAG не опрашивается)")
        else:
            logger.info(f"LLM_API_KEY не задан. Автономный Fallback для темы «{topic}»")

        await asyncio.sleep(0.18)  # Имитация 180 мс ответа для плавности UX
        result = get_metaphor(topic, interest, grade)
        result["latency_ms"] = int((time.time() - start_time) * 1000)
        result["rag_chunks"] = []
        result["rag_hits"] = 0
        result["rag_subject"] = subject or "none"
        return result

    # Правило 2 & 3: Извлечение фрагментов учебника (RAG)
    context_chunks: List[str] = []
    effective_subject = subject or "algebra"
    if subject and rag_engine.has_subject(subject):
        rag_t0 = time.time()
        try:
            context_chunks = rag_engine.retrieve(query_text, subject, k=3)
            rag_ms = int((time.time() - rag_t0) * 1000)
            logger.info(f"RAG retrieve: subject={subject}, k=3, hits={len(context_chunks)}, latency_ms={rag_ms}")
        except Exception as e:
            logger.warning(f"Ошибка RAG при извлечении контекста: {e}. Продолжение без контекста.")
            context_chunks = []
    elif not subject:
        logger.info(f"Предмет не задан. Генерация LLM без RAG-контекста.")

    # Формируем контекстный блок из учебников
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

    # Правило 4: Вызов LLM с перехватом ошибок
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

                # Правило 5: Выходные Guardrails (OutputGuardrails)
                is_valid, reason = OutputGuardrails.validate(raw_text)
                if not is_valid:
                    logger.warning(f"OutputGuardrails заблокировал ответ модели ({reason}). Подмена на безопасный Fallback...")
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
