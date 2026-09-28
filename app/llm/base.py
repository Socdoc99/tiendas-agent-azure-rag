"""Provider interface consumed by the LangGraph orchestration."""

from typing import Protocol

from langchain_core.language_models.chat_models import BaseChatModel


class LLMProviderError(RuntimeError):
    """Safe error raised when a model provider cannot be initialized."""


class LLMProvider(Protocol):
    """Factory for a tool-capable chat model, independent of its vendor."""

    def get_chat_model(self) -> BaseChatModel:
        """Return a configured model implementing LangChain's chat interface."""

    def close(self) -> None:
        """Release provider resources when the graph owns the provider."""
