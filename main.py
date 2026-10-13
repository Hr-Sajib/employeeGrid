import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from src.utils.db import Base, engine
from src.utils.settings import DEFAULT_JWT_SECRET, settings
from src.auth.route import auth_routes
from src.chat.route import chat_routes
from src.employee_data.route import employee_routes
from src.rag.route import rag_routes
from src.usage.route import usage_routes
from src.chat.socket import socket_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
Base.metadata.create_all(engine)
# create_all never changes a table that already exists, so a new column on an old table is added here.
# (Alembic is the proper tool for this once the schema keeps changing.)
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations (user_id)"))

if settings.JWT_SECRET == DEFAULT_JWT_SECRET:
    logger.warning("JWT_SECRET is the built-in dev value. Set a long random JWT_SECRET in .env before real use.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 FastAPI server starting...")
    logger.info("📊 Database tables created/verified")
    yield
    logger.info("🛑 FastAPI server shutting down...")


app = FastAPI(lifespan=lifespan)
app.include_router(auth_routes)
app.include_router(chat_routes)
app.include_router(usage_routes)
app.include_router(employee_routes)
app.include_router(rag_routes)
app.mount("/ws", socket_app)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "src" / "ui" / "static"), name="static")


UI_FILE = Path(__file__).parent / "src" / "ui" / "index.html"


@app.get("/healthz", include_in_schema=False)
def healthz():
    """For the container healthcheck. It does not touch the database, so it never keeps a serverless database awake."""
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
@app.get("/chat-ui", include_in_schema=False)
def ui():
    return FileResponse(UI_FILE)
