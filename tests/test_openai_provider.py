from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage

from app.agent.graph import (
    AgentGraphError,
    build_agent_graph,
    run_agent_question,
)
from app.core.config import Settings
from app.llm import LLMProviderError
from app.llm.openai_provider import OpenAIProvider, _create_chat_model
from app.tenant import TenantContext

BUSINESS_ID = "11111111-1111-1111-1111-111111111111"
ESTABLISHMENT_ID = "22222222-2222-2222-2222-222222222222"


class FakeProvider:
    def __init__(self, model) -> None:
        self.model = model
        self.calls = 0
        self.closed = False

    def get_chat_model(self):
        self.calls += 1
        return self.model

    def close(self) -> None:
        self.closed = True


class FakeChatModel:
    def __init__(self, *, invoke_error: Exception | None = None) -> None:
        self.invoke_error = invoke_error
        self.bind_kwargs: dict[str, object] = {}
        self.tools: list[object] = []

    def bind_tools(self, tools, **kwargs):
        self.tools = tools
        self.bind_kwargs = kwargs
        return self

    def invoke(self, messages):
        if self.invoke_error:
            raise self.invoke_error
        return AIMessage(content="Respuesta de prueba")


def _tenant() -> TenantContext:
    from uuid import UUID

    return TenantContext(
        business_id=UUID(BUSINESS_ID),
        establishment_id=UUID(ESTABLISHMENT_ID),
        timezone="America/Bogota",
    )


def test_openai_provider_uses_configured_model_and_named_key_vault_secret() -> None:
    settings = Settings(
        openai_chat_model="gpt-5-mini",
        openai_api_key_secret_name="openai-api-key",
        azure_key_vault_url="https://kv-tiendas-sbx-k7m4p2.vault.azure.net/",
    )
    secrets = Mock()
    secrets.get_secret_value.return_value = "test-only-secret-value"
    model = object()
    factory = Mock(return_value=model)
    provider = OpenAIProvider(settings, secrets=secrets, model_factory=factory)

    assert provider.get_chat_model() is model
    assert provider.get_chat_model() is model
    secrets.get_secret_value.assert_called_once_with("openai-api-key")
    factory.assert_called_once_with(
        model="gpt-5-mini",
        api_key="test-only-secret-value",
        timeout=settings.openai_timeout_seconds,
        max_retries=0,
    )


def test_openai_provider_rejects_missing_model_without_secret_lookup() -> None:
    settings = Settings(
        openai_chat_model=None,
        azure_key_vault_url="https://kv-tiendas-sbx-k7m4p2.vault.azure.net/",
    )
    secrets = Mock()
    provider = OpenAIProvider(settings, secrets=secrets, model_factory=Mock())

    with pytest.raises(LLMProviderError, match="OPENAI_CHAT_MODEL"):
        provider.get_chat_model()

    secrets.get_secret_value.assert_not_called()


def test_openai_provider_rejects_missing_key_vault_configuration() -> None:
    settings = Settings(openai_chat_model="gpt-5-mini", azure_key_vault_url=None)
    secrets = Mock()
    provider = OpenAIProvider(settings, secrets=secrets, model_factory=Mock())

    with pytest.raises(LLMProviderError, match="Key Vault configuration"):
        provider.get_chat_model()

    secrets.get_secret_value.assert_not_called()


def test_openai_provider_constructs_langchain_model_without_network_call() -> None:
    settings = Settings(
        openai_chat_model="gpt-5-mini",
        azure_key_vault_url="https://kv-tiendas-sbx-k7m4p2.vault.azure.net/",
    )
    secrets = Mock()
    secrets.get_secret_value.return_value = "test-only-not-a-credential"
    provider = OpenAIProvider(settings, secrets=secrets, model_factory=_create_chat_model)

    model = provider.get_chat_model()

    assert model.model_name == "gpt-5-mini"
    assert model.max_retries == 0
    provider.close()


def test_openai_provider_wraps_secret_lookup_failure_without_details() -> None:
    settings = Settings(
        openai_chat_model="gpt-5-mini",
        azure_key_vault_url="https://kv-tiendas-sbx-k7m4p2.vault.azure.net/",
    )
    secrets = Mock()
    secrets.get_secret_value.side_effect = RuntimeError("AccessDenied private detail")
    provider = OpenAIProvider(settings, secrets=secrets, model_factory=Mock())

    with pytest.raises(LLMProviderError) as raised:
        provider.get_chat_model()

    assert "AccessDenied" not in str(raised.value)
    assert "private detail" not in str(raised.value)


def test_graph_accepts_injected_provider_and_keeps_tool_contract() -> None:
    settings = Settings(business_timezone="America/Bogota")
    model = FakeChatModel()
    provider = FakeProvider(model)
    graph = build_agent_graph(settings, _tenant(), provider=provider)

    result = run_agent_question(graph, "Hola")

    assert result.final_answer == "Respuesta de prueba"
    assert provider.calls == 1
    assert model.bind_kwargs == {"strict": True, "parallel_tool_calls": False}
    assert [tool.name for tool in model.tools] == ["query_database"]


def test_provider_request_failure_is_controlled_and_does_not_leak_details() -> None:
    model = FakeChatModel(invoke_error=RuntimeError("private API response body"))
    provider = FakeProvider(model)
    graph = build_agent_graph(Settings(), _tenant(), provider=provider)

    with pytest.raises(AgentGraphError) as raised:
        run_agent_question(graph, "Hola")

    assert str(raised.value) == "The model provider request failed."
    assert "private API response body" not in str(raised.value)
