import logging
from time import perf_counter

from fastapi import APIRouter, Request

from app.api.dependencies import get_services
from app.core.config import Settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm import NO_ANSWER, format_context, used_citations

router = APIRouter(prefix="/api/v1", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    started = perf_counter()
    settings: Settings = request.app.state.settings
    services = get_services(request)
    chunks = await services.retriever.retrieve(body.message, body.filters.as_search_filters())
    request_id = request.state.request_id
    if not chunks:
        answer = NO_ANSWER
        citations = []
    else:
        context, available_citations = format_context(chunks)
        history = (
            body.history[-settings.max_chat_history_messages :]
            if settings.max_chat_history_messages
            else []
        )
        messages = [{"role": item.role, "content": item.content} for item in history]
        messages.append({"role": "user", "content": body.message})
        answer = await services.llm.generate(
            messages=messages,
            context=context,
            request_id=request_id,
        )
        citations = used_citations(answer, available_citations)
        if not citations:
            answer = NO_ANSWER
    latency_ms = round((perf_counter() - started) * 1000)
    logger.info(
        "chat_completed",
        extra={"request_id": request_id, "retrieved_chunks": len(chunks), "latency_ms": latency_ms},
    )
    return ChatResponse(
        answer=answer,
        citations=citations,
        request_id=request_id,
        retrieved_chunks=len(chunks),
        latency_ms=latency_ms,
    )
