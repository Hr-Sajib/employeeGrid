import logging
import socketio
from fastapi import HTTPException
from pydantic import ValidationError
from src.auth.security import decode_token
from src.chat.controller import ChatController
from src.chat.dtos import ChatRequest
from src.utils.db import Session
from src.utils.settings import settings

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=[settings.PUBLIC_ORIGIN] if settings.PUBLIC_ORIGIN else None)   # no setting: same-origin only
socket_app = socketio.ASGIApp(sio, socketio_path="ws/socket.io")


@sio.event
async def connect(sid, environ, auth):
    try:
        user = decode_token((auth or {}).get("token", ""))
    except HTTPException:
        raise socketio.exceptions.ConnectionRefusedError("unauthorized")
    await sio.save_session(sid, {"user": user})


@sio.event
async def chat(sid, data):
    try:
        user = (await sio.get_session(sid))["user"]
        req = ChatRequest(**data)
        with Session() as db:
            res = await ChatController.chat(db, req, user, lambda step: sio.emit("step", step, to=sid))
        await sio.emit("reply", {"conversation_id": str(res.conversation_id), "reply": res.reply}, to=sid)
    except ValidationError as e:
        await sio.emit("error", {"detail": str(e)}, to=sid)
    except HTTPException as e:
        await sio.emit("error", {"detail": e.detail}, to=sid)
    except Exception:
        logger.exception("chat event failed")
        await sio.emit("error", {"detail": "Something went wrong. Please try again."}, to=sid)
