from pydantic import BaseModel, ConfigDict, Field


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=20)
    store_id: str | None = Field(default=None, max_length=100)
    language: str = Field(default="es", max_length=20)
    version: str | None = Field(default=None, max_length=100)
    is_active: bool = True
    source_url: str | None = Field(default=None, max_length=2048)
    allowed_groups: list[str] = Field(default_factory=list, max_length=100)
