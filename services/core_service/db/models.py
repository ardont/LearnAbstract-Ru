from datetime import datetime, timezone
import json
from typing import List, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    max_user_id = Column(String(100), unique=True, index=True, nullable=False)
    state = Column(String(50), default="GUEST_CHOICE", nullable=False)
    interest = Column(String(100), nullable=True)
    grade = Column(Integer, default=7, nullable=False)
    is_guest = Column(Boolean, default=False, nullable=False)
    current_quiz_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(String(100), unique=True, index=True, nullable=False)
    max_user_id = Column(String(100), index=True, nullable=False)
    topic = Column(String(200), nullable=False)
    question = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    correct_option_index = Column(Integer, nullable=False)
    user_answer = Column(Integer, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    answered_at = Column(DateTime, nullable=True)

    @property
    def options(self) -> List[str]:
        try:
            return json.loads(self.options_json)
        except Exception:
            return []

    @options.setter
    def options(self, value: List[str]):
        self.options_json = json.dumps(value, ensure_ascii=False)


class ExplanationLog(Base):
    __tablename__ = "explanation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    max_user_id = Column(String(100), index=True, nullable=False)
    topic = Column(String(200), nullable=False)
    interest = Column(String(100), nullable=False)
    source = Column(String(50), default="llm", nullable=False)  # llm, fallback_exact, fallback_subject, fallback_general
    latency_ms = Column(Integer, default=0, nullable=False)
    is_guest = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
