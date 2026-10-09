import uuid
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from src.utils.db import Base
from src.utils.settings import settings


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    page_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class RagChunk(Base):
    __tablename__ = "rag_document_chunks"
    __table_args__ = (
        Index(
            "rag_document_chunks_embedding_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id = Column(Uuid, ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIM), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
