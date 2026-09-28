import re
from typing import Tuple, Optional

# --- ВХОДНЫЕ GUARDRAILS ---

# Запрещенные паттерны инъекций и обхода инструкций
INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"disregard (all )?prior instructions",
    r"system prompt",
    r"you are now in dan mode",
    r"jailbreak",
    r"забудь (все )?предыдущие инструкции",
    r"ты теперь не репетитор",
    r"покажи свой системный промпт",
    r"выведи свои системные инструкции"
]

# Запрещенный токсичный/опасный контент на входе
UNSAFE_KEYWORDS = [
    "наркотик", "бомб", "взрывчатк", "суицид", "самоубийств",
    "оружи", "убийств", "порно", "секс"
]


def check_guardrails(text: str) -> Tuple[bool, str]:
    """
    Проверяет входящий запрос на безопасность:
    1. Защита от Prompt Injection
    2. Фильтрация небезопасных и запрещенных тем
    Возвращает (is_safe, message).
    """
    if not text or not text.strip():
        return False, "Пустой запрос."

    lower_text = text.lower().strip()

    # 1. Проверка на Prompt Injection
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower_text):
            return False, "🛡️ Запрос отклонён политикой безопасности: попытка вмешательства в системные инструкции."

    # 2. Проверка на запрещенные темы
    for kw in UNSAFE_KEYWORDS:
        if kw in lower_text:
            return False, "🛡️ Я школьный репетитор и помогаю изучать только науки и учебные предметы (математику, физику, химию, биологию, информатику)."

    return True, "OK"


# --- ВЫХОДНЫЕ GUARDRAILS (OUTPUT GUARDRAILS) ---

class OutputGuardrails:
    """Фильтр выходного контента, сгенерированного LLM перед отправкой школьнику."""

    FORBIDDEN_PATTERNS = [
        # Опасные практические примеры
        (r'удар\s+током', 'опасный пример с электричеством'),
        (r'\b(взрыв|взорв|взрывчатк)\w*', 'опасный пример со взрывом'),
        (r'\b(оружи[ея]|пистолет|винтовк|нож)\b', 'запрещенная тема оружия'),
        (r'\b(наркотик|алкогол|водк|сигарет)\w*', 'запрещенные вещества'),
        (r'\b(суицид|самоубийств)\w*', 'запрещенный суицидальный контент'),
        # Токсичность и оскорбления
        (r'\b(дурак|идиот|тупиц|дебил|кретин)\w*', 'токсичная лексика'),
        # Утечки PII (номера телефонов, email)
        (r'\b(\+?7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}\b', 'номер телефона'),
        (r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', 'email адрес')
    ]

    MAX_LENGTH = 4000

    @classmethod
    def validate(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Возвращает (is_valid, reason).
        Если is_valid == False — ответ LLM отклоняется и заменяется на безопасный Fallback.
        """
        if not text:
            return False, "Пустой ответ модели"

        if len(text) > cls.MAX_LENGTH:
            return False, f"Превышена допустимая длина сообщения: {len(text)} > {cls.MAX_LENGTH}"

        for pattern, reason in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, f"Обнаружено нарушение: {reason}"

        return True, None
