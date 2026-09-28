from uuid import UUID

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.graph import AgentRunResult
from app.chat.models import ChatRequest, ChatResponse
from app.chat.service import ChatAgentUnavailableError, ChatService
from app.chat.store import ConversationNotFoundError


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, graph, question: str, *, history) -> AgentRunResult:
        self.calls.append({"graph": graph, "question": question, "history": list(history)})
        return AgentRunResult(final_answer=f"Respuesta a {question}", query_count=1, attempts=())


def test_chat_persists_only_public_messages_and_reuses_conversation_history() -> None:
    runner = FakeRunner()
    service = ChatService(object(), runner=runner)

    first = service.chat("  Ventas de hoy  ")
    second = service.chat("¿Y ayer?", first.conversation_id)

    assert first.conversation_id == second.conversation_id
    assert runner.calls[0]["question"] == "Ventas de hoy"
    assert runner.calls[0]["history"] == []
    assert [type(message) for message in runner.calls[1]["history"]] == [
        HumanMessage,
        AIMessage,
    ]
    assert [message.role for message in service.store.snapshot(first.conversation_id)] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_chat_rejects_unknown_conversation_without_running_agent() -> None:
    runner = FakeRunner()
    service = ChatService(object(), runner=runner)

    with pytest.raises(ConversationNotFoundError):
        service.chat("Consulta", UUID("33333333-3333-3333-3333-333333333333"))

    assert runner.calls == []


def test_chat_does_not_persist_failed_turn() -> None:
    def fail(*args, **kwargs):
        raise RuntimeError("private details")

    service = ChatService(object(), runner=fail)
    conversation = service.store.create()

    with pytest.raises(ChatAgentUnavailableError):
        service.chat("Consulta", conversation.conversation_id)

    assert service.store.snapshot(conversation.conversation_id) == ()


def test_chat_contracts_exclude_tenant_and_tool_diagnostics() -> None:
    request_schema = ChatRequest.model_json_schema()
    response_schema = ChatResponse.model_json_schema()

    assert set(request_schema["properties"]) == {"conversation_id", "message"}
    assert set(response_schema["properties"]) == {"conversation_id", "answer", "query_count"}
    serialized = str({"request": request_schema, "response": response_schema}).lower()
    for forbidden in ("business_id", "establishment_id", "logical_sql", "semantic_view"):
        assert forbidden not in serialized


def test_agent_turn_history_rejects_tool_messages() -> None:
    # ChatService only forwards public user/assistant turns; tool output is never history.
    service = ChatService(object())
    with pytest.raises(ValueError):
        service._to_langchain_history([ToolMessage(content="internal", tool_call_id="x")])
