import contextvars
import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ContextVar для передачи correlation_id между асинхронными задачами
correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)

# Шаблоны для маскирования PII (152-ФЗ)
PHONE_PATTERN = re.compile(r'(\+?7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}')
EMAIL_PATTERN = re.compile(r'([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)')
TOKEN_PATTERN = re.compile(r'([A-Za-z0-9_-]{20,})')


def mask_pii(text: str) -> str:
    """Маскирует персональные данные (номера телефонов, email, длинные токены) в логах."""
    if not isinstance(text, str):
        return text

    # Маскирование телефонов: +7 (***) ***-**-12
    text = PHONE_PATTERN.sub(lambda m: m.group(0)[:4] + '***-**-' + m.group(0)[-2:], text)
    # Маскирование email: a***@domain.com
    text = EMAIL_PATTERN.sub(lambda m: m.group(1)[0] + '***@' + m.group(2), text)
    return text


class StructuredFormatter(logging.Formatter):
    """JSON-форматтер с автоматическим маскированием PII и добавлением correlation_id."""

    def format(self, record: logging.LogRecord) -> str:
        corr_id = correlation_id_ctx.get() or getattr(record, "correlation_id", None)
        message = record.getMessage()

        # Маскируем PII в сообщении
        safe_message = mask_pii(message)

        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": safe_message,
        }

        if corr_id:
            log_data["correlation_id"] = corr_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Настройка структурированного логгера для сервисов."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)

    logger.propagate = False
    return logger
