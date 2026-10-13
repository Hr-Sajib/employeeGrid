from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.chat.controller import ChatController
from src.chat.dtos import ChatRequest, ChatResponse
from src.utils.db import get_db

chat_routes = APIRouter(prefix="/chat", tags=["chat"])


@chat_routes.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    return await ChatController.chat(db, req)
