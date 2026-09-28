from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest

from app.core.config import Settings
from app.main import create_app
from app.services.llm import NO_ANSWER


class FakeRetriever:
    def __init__(self, chunks: list[dict]) -> None:
        self.chunks = chunks
        self.query = None
        self.filters = None

    async def retrieve(self, query: str, filters: dict) -> list[dict]:
        self.query = query
        self.filters = filters
        return self.chunks


class FakeLLM:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.called = False

    async def generate(self, **kwargs) -> str:
        self.called = True
        return self.answer


@pytest.mark.asyncio
async def test_chat_returns_valid_citations_and_request_id() -> None:
    retriever = FakeRetriever(
        [
            {
                "document_id": "manual-v1",
                "document_name": "Manual.pdf",
                "page": 4,
                "chunk_number": 2,
                "category": "manual",
                "content": "Abrir la tienda.",
            }
        ]
    )
    llm = FakeLLM("La tienda se abre con el procedimiento [S1].")
    app = create_app(Settings(_env_file=None))
    app.state.services = SimpleNamespace(retriever=retriever, llm=llm)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/chat",
            json={
                "message": "Como se abre?",
                "filters": {"country": "CO"},
                "history": [{"role": "user", "content": "Hola"}],
            },
        )

    assert response.status_code == 200
    assert response.json()["citations"][0]["source_id"] == "S1"
    assert response.json()["retrieved_chunks"] == 1
    UUID(response.json()["request_id"])
    assert retriever.filters["country"] == "CO"
    assert llm.called


@pytest.mark.asyncio
async def test_chat_uses_no_answer_without_evidence_or_model_call() -> None:
    retriever = FakeRetriever([])
    llm = FakeLLM("This must not be returned.")
    app = create_app(Settings(_env_file=None))
    app.state.services = SimpleNamespace(retriever=retriever, llm=llm)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/chat", json={"message": "Pregunta"})

    assert response.status_code == 200
    assert response.json()["answer"] == NO_ANSWER
    assert response.json()["citations"] == []
    assert not llm.called
