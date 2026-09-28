from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_services
from app.core.config import Settings
from app.schemas.chat import ChatFilters

router = APIRouter(prefix="/api/v1/debug", tags=["search-debug"])


class SearchDebugRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=4000)
    filters: ChatFilters = Field(default_factory=ChatFilters)


@router.post("/search")
async def debug_search(body: SearchDebugRequest, request: Request) -> dict:
    settings: Settings = request.app.state.settings
    if settings.environment.lower() == "prod":
        raise HTTPException(status_code=404, detail="Not found")
    chunks = await get_services(request).retriever.retrieve(
        body.query, body.filters.as_search_filters()
    )
    return {
        "results": [
            {
                "document": chunk.get("document_name"),
                "page": chunk.get("page"),
                "chunk": chunk.get("chunk_number"),
                "content": chunk.get("content"),
                "score": chunk.get("score"),
            }
            for chunk in chunks
        ]
    }
