from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.rag.chunk import split_text
from src.rag.dtos import DocumentResponse
from src.rag.embed import embed_texts
from src.rag.extract import extract_docx, extract_pdf
from src.rag.model import RagChunk, RagDocument

MAX_BYTES = 20 * 1024 * 1024
EXTRACTORS = {"pdf": extract_pdf, "docx": extract_docx}


class RagController:
    @staticmethod
    def ingest(db: Session, name: str, filename: str, data: bytes) -> DocumentResponse:
        file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if file_type not in EXTRACTORS:
            raise HTTPException(400, "Only .pdf and .docx files are supported")
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "File is larger than 20 MB")

        try:
            pages = EXTRACTORS[file_type](data)
        except Exception:
            raise HTTPException(400, "Could not read the file")

        pieces = [(page, chunk) for page, text in pages for chunk in split_text(text)]
        if not pieces:
            raise HTTPException(422, "No extractable text found (scanned PDFs are not supported)")

        vectors = embed_texts([chunk for _, chunk in pieces])

        document = RagDocument(
            name=name,
            filename=filename,
            file_type=file_type,
            page_count=len(pages) if file_type == "pdf" else None,
        )
        db.add(document)
        db.flush()
        db.add_all(
            RagChunk(document_id=document.id, chunk_index=i, page_number=page, content=chunk, embedding=vector)
            for i, ((page, chunk), vector) in enumerate(zip(pieces, vectors))
        )
        db.commit()
        return DocumentResponse(
            id=document.id,
            name=document.name,
            filename=document.filename,
            file_type=document.file_type,
            page_count=document.page_count,
            chunk_count=len(pieces),
        )
