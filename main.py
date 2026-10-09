import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from fastapi.responses import FileResponse
from src.utils.db import Base, engine
from src.chat.route import chat_routes
from src.employee_data.route import employee_routes
from src.rag.route import rag_routes
from src.chat.socket import socket_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
Base.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 FastAPI server starting...")
    logger.info("📊 Database tables created/verified")
    yield
    logger.info("🛑 FastAPI server shutting down...")


app = FastAPI(lifespan=lifespan)
app.include_router(chat_routes)
app.include_router(employee_routes)
app.include_router(rag_routes)
app.mount("/ws", socket_app)


@app.get("/chat-ui", include_in_schema=False)
def chat_ui():
    return FileResponse("src/chat/test.html")
