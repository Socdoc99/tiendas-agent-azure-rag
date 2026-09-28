from datetime import datetime

from pydantic import BaseModel, Field


class SearchChunk(BaseModel):
    id: str
    document_id: str
    document_name: str
    content: str
    page: int | None = None
    chunk_number: int
    category: str | None = None
    department: str | None = None
    country: str | None = None
    store_id: str | None = None
    language: str | None = None
    version: str | None = None
    is_active: bool = True
    source_path: str | None = None
    source_url: str | None = None
    created_at: datetime | None = None
    allowed_groups: list[str] = Field(default_factory=list)
