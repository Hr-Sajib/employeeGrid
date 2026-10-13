import asyncio
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from src.auth.deps import get_current_user, require_admin
from src.rag.controller import RagController
from src.rag.dtos import DocumentResponse
from src.utils.db import get_db

rag_routes = APIRouter(prefix="/documents", tags=["rag"], dependencies=[Depends(get_current_user)])


@rag_routes.post("", response_model=DocumentResponse, status_code=201, dependencies=[Depends(require_admin)])
async def upload_document(
    name: str = Form(..., min_length=1),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    data = await file.read()
    return await asyncio.to_thread(RagController.ingest, db, name, file.filename or "", data)


@rag_routes.get("", response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    return RagController.list_documents(db)


@rag_routes.delete("/{document_id}", dependencies=[Depends(require_admin)])
def delete_document(document_id: UUID, db: Session = Depends(get_db)):
    return RagController.delete(db, document_id)
