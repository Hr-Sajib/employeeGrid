from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.auth.deps import get_current_user
from src.auth.security import CurrentUser
from src.chat.controller import ChatController
from src.chat.dtos import ChatRequest, ChatResponse
from src.utils.db import get_db

chat_routes = APIRouter(prefix="/chat", tags=["chat"])


@chat_routes.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return await ChatController.chat(db, req, user)
