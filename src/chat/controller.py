import asyncio
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.agent.graph import run_agent
from src.chat.dtos import ChatRequest, ChatResponse
from src.chat.model import Conversation, Message, Role


class ChatController:
    @staticmethod
    def prepare(db: Session, req: ChatRequest) -> tuple[UUID, list[dict]]:
        if req.conversation_id:
            conversation = db.get(Conversation, req.conversation_id)
            if not conversation:
                raise HTTPException(404, "Conversation not found")
        else:
            conversation = Conversation()
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
        return conversation.id, [{"role": m.role.value, "content": m.content} for m in history]

    @staticmethod
    def save_reply(db: Session, conversation_id: UUID, reply: str) -> None:
        db.add(Message(conversation_id=conversation_id, role=Role.assistant, content=reply))
        db.commit()

    @staticmethod
    async def chat(db: Session, req: ChatRequest) -> ChatResponse:
        conversation_id, messages = await asyncio.to_thread(ChatController.prepare, db, req)
        reply = await run_agent(messages)
        await asyncio.to_thread(ChatController.save_reply, db, conversation_id, reply)
        return ChatResponse(conversation_id=conversation_id, reply=reply)
