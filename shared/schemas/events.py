import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    """Единый формат события по требованиям архитектуры v5.0."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    version: str = "1.0"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: Optional[str] = None
    producer: str = "unknown"
    payload: Dict[str, Any]


class UserMessagePayload(BaseModel):
    max_user_id: str
    text: str
    message_id: Optional[str] = None
    interest: Optional[str] = None
    grade: Optional[int] = None
    is_guest: bool = False


class ExplanationRequestPayload(BaseModel):
    max_user_id: str
    topic: str
    interest: str = "общий"
    grade: int = 7
    difficulty: str = "medium"
    is_guest: bool = False


class ExplanationResponsePayload(BaseModel):
    max_user_id: str
    text: str
    topic: str
    source: str = "llm"  # "llm" | "fallback_exact" | "fallback_subject" | "fallback_general"
    analogies: List[str] = Field(default_factory=list)
    quiz_suggested: bool = True


class QuizOption(BaseModel):
    index: int
    text: str


class QuizResponsePayload(BaseModel):
    max_user_id: str
    quiz_id: str
    topic: str
    question: str
    options: List[str]
    correct_option_index: int
    explanation: str


class QuizAnswerPayload(BaseModel):
    max_user_id: str
    quiz_id: str
    selected_option_index: int


class DLQPayload(BaseModel):
    original_event: Dict[str, Any]
    error: str
    stack_trace: str
    service: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
