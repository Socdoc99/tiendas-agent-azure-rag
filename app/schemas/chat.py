from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: str | None = None
    store_id: str | None = None
    department: str | None = None
    category: str | None = None


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    filters: ChatFilters = Field(default_factory=ChatFilters)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=8)
