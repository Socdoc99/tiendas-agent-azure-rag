from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: str | None = Field(default=None, max_length=100)
    store_id: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)

    def as_search_filters(self) -> dict[str, str | None]:
        return self.model_dump()


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    filters: ChatFilters = Field(default_factory=ChatFilters)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=8)


class Citation(BaseModel):
    source_id: str
    document_id: str
    document_name: str
    page: int | None = None
    chunk_number: int


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    request_id: str
    retrieved_chunks: int
    latency_ms: int
