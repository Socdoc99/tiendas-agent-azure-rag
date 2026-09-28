"""Public request and response contracts for the chat endpoint."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from app.agent.graph import MAX_QUERY_DATABASE_ATTEMPTS

MAX_MESSAGE_LENGTH = 4000


class ChatRequest(BaseModel):
    """User input accepted by the HTTP API."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID | None = None
    message: StrictStr = Field(max_length=MAX_MESSAGE_LENGTH)

    @field_validator("message", mode="before")
    @classmethod
    def strip_and_require_message(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("message must be a string")
        message = value.strip()
        if not message:
            raise ValueError("message must not be empty")
        return message


class ChatResponse(BaseModel):
    """Safe public response for one completed user turn."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    answer: str = Field(min_length=1)
    query_count: int = Field(ge=0, le=MAX_QUERY_DATABASE_ATTEMPTS)
