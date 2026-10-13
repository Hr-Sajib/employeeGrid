import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Uuid
from src.utils.db import Base


class UsageLog(Base):
    """One row per chat message the agent handled. It never stores the answer, only numbers about the run."""
    __tablename__ = "usage_log"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    conversation_id = Column(Uuid)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    question = Column(String(500))
    needs_employee_data = Column(Boolean)
    needs_documents = Column(Boolean)
    path = Column(String)                  # e.g. "router -> employee_data -> synthesizer -> verifier"
    verdict = Column(String)               # pass | fallback | None when the run crashed
    retries = Column(Integer, default=0)
    status = Column(String)                # ok | error
    total_ms = Column(Integer)
    llm_calls = Column(Integer)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    cost_usd = Column(Float, default=0.0)
