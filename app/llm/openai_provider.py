"""OpenAI chat-model provider backed by a Key Vault secret."""

from collections.abc import Callable
from typing import Any, Protocol

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import Settings
from app.llm.base import LLMProviderError
from app.services.secret_provider import KeyVaultSecretProvider


class SecretResolver(Protocol):
    def get_secret_value(self, secret_name: str) -> str: ...


ChatModelFactory = Callable[..., BaseChatModel]


def _create_chat_model(**kwargs: Any) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(**kwargs)


class OpenAIProvider:
    """Create one configurable ChatOpenAI model without exposing its API key."""

    def __init__(
        self,
        settings: Settings,
        *,
        secrets: SecretResolver | None = None,
        model_factory: ChatModelFactory = _create_chat_model,
    ) -> None:
        self.settings = settings
        self.secrets = secrets or KeyVaultSecretProvider(settings)
        self.model_factory = model_factory
        self._model: BaseChatModel | None = None

    def get_chat_model(self) -> BaseChatModel:
        if self._model is not None:
            return self._model

        model_name = self.settings.openai_chat_model
        if not isinstance(model_name, str) or not model_name.strip():
            raise LLMProviderError("OPENAI_CHAT_MODEL is not configured.")
        secret_name = self.settings.openai_api_key_secret_name
        if not secret_name.strip() or not self.settings.azure_key_vault_url:
            raise LLMProviderError("OpenAI Key Vault configuration is incomplete.")

        try:
            api_key = self.secrets.get_secret_value(secret_name)
            if not isinstance(api_key, str) or not api_key.strip():
                raise ValueError("The configured secret is empty.")
            self._model = self.model_factory(
                model=model_name.strip(),
                api_key=api_key,
                timeout=self.settings.openai_timeout_seconds,
                max_retries=0,
            )
        except LLMProviderError:
            raise
        except Exception as error:
            raise LLMProviderError("The OpenAI provider could not be initialized.") from error
        return self._model

    def close(self) -> None:
        """Close the synchronous OpenAI client if the model created one."""

        if self._model is None:
            return
        client = getattr(self._model, "client", None)
        close = getattr(client, "close", None)
        if callable(close):
            close()
        self._model = None
