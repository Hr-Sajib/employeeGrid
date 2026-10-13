import asyncio
import re
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.agent.graph import run_agent
from src.usage import limits
from src.usage.controller import UsageController
from src.utils.trace import run_summary
from src.chat.dtos import ChatRequest, ChatResponse
from src.chat.model import Conversation, Message, Role


def for_agent(role: str, content: str) -> str:
    """Past answers carry [E1] markers and a Sources block that belong to that turn only. Drop them so
    the model does not cite evidence that no longer exists."""
    if role != "assistant":
        return content
    content = re.sub(r"\n\nSources:\n.*$", "", content, flags=re.S)
    return re.sub(r"\s*\[[EDC]\d+\]", "", content)


class ChatController:
    @staticmethod
    def prepare(db: Session, req: ChatRequest, user) -> tuple[UUID, list[dict]]:
        if req.conversation_id:
            conversation = db.get(Conversation, req.conversation_id)
            if not conversation or conversation.user_id != user.id:   # someone else's chat looks like it does not exist
                raise HTTPException(404, "Conversation not found")
        else:
            conversation = Conversation(user_id=user.id)
            db.add(conversation)
            db.flush()

        db.add(Message(conversation_id=conversation.id, role=Role.user, content=req.message))
        db.commit()

        history = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id, Message.role != Role.tool)
            .order_by(Message.created_at)
            .all()
        )
        return conversation.id, [{"role": m.role.value, "content": for_agent(m.role.value, m.content)} for m in history]

    @staticmethod
    def save_reply(db: Session, conversation_id: UUID, reply: str, usage_row=None) -> None:
        db.add(Message(conversation_id=conversation_id, role=Role.assistant, content=reply))
        if usage_row:
            db.add(usage_row)   # saved in the same commit, so it costs no extra database round trip
        db.commit()

    @staticmethod
    async def chat(db: Session, req: ChatRequest, user, on_step=None) -> ChatResponse:
        await asyncio.to_thread(limits.check, db, user)
        conversation_id, messages = await asyncio.to_thread(ChatController.prepare, db, req, user)
        try:
            reply = await run_agent(messages, conversation_id, on_step)
        except Exception:
            row = UsageController.build(user, conversation_id, req.message, run_summary(), "error")
            await asyncio.to_thread(UsageController.save, db, row)
            raise
        run = run_summary()
        limits.add_cost(user.id, run["cost"])
        row = UsageController.build(user, conversation_id, req.message, run, "ok")
        await asyncio.to_thread(ChatController.save_reply, db, conversation_id, reply, row)
        return ChatResponse(conversation_id=conversation_id, reply=reply)
