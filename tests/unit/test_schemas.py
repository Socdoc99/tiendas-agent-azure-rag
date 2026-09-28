import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest
from app.schemas.documents import DocumentMetadata


def test_chat_request_accepts_expected_filters_and_history() -> None:
    request = ChatRequest.model_validate(
        {
            "message": "¿Cuál es el procedimiento de apertura?",
            "filters": {"country": "CO", "department": "operaciones"},
            "history": [{"role": "user", "content": "Hola"}],
        }
    )

    assert request.filters.country == "CO"
    assert request.history[0].role == "user"


def test_chat_request_rejects_oversized_history() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(
            message="Pregunta",
            history=[{"role": "user", "content": "Hola"}] * 9,
        )


def test_document_metadata_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        DocumentMetadata.model_validate({"unknown": "value"})
