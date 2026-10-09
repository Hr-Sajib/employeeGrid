import asyncio
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from src.rag.controller import RagController
from src.rag.dtos import DocumentResponse
from src.utils.db import get_db

rag_routes = APIRouter(prefix="/documents", tags=["rag"])


@rag_routes.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    name: str = Form(..., min_length=1),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    data = await file.read()
    return await asyncio.to_thread(RagController.ingest, db, name, file.filename or "", data)
