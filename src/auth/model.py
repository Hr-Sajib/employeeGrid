import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Uuid
from src.utils.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="viewer")   # "admin" or "viewer"
    created_at = Column(DateTime, default=datetime.utcnow)
