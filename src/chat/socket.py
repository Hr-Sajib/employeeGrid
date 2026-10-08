import socketio
from fastapi import HTTPException
from pydantic import ValidationError
from src.chat.controller import ChatController
from src.chat.dtos import ChatRequest
from src.utils.db import Session

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, socketio_path="ws/socket.io")


@sio.event
async def chat(sid, data):
    try:
        req = ChatRequest(**data)
        with Session() as db:
            res = await ChatController.chat(db, req)
        await sio.emit("reply", {"conversation_id": str(res.conversation_id), "reply": res.reply}, to=sid)
    except ValidationError as e:
        await sio.emit("error", {"detail": str(e)}, to=sid)
    except HTTPException as e:
        await sio.emit("error", {"detail": e.detail}, to=sid)
