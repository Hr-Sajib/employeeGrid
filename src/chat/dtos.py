from uuid import UUID
from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str


class ChatResponse(BaseModel):
    conversation_id: UUID
    reply: str
