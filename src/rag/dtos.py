from uuid import UUID
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: UUID
    name: str
    filename: str
    file_type: str
    page_count: int | None
    chunk_count: int
