import asyncio

from azure.keyvault.secrets import SecretClient

from app.core.azure import get_azure_credential
from app.core.config import Settings
from app.core.exceptions import DependencyUnavailableError


class KeyVaultSecretProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: SecretClient | None = None
        self._api_key: str | None = None

    @property
    def client(self) -> SecretClient:
        if self._client is None:
            if not self.settings.azure_key_vault_url:
                raise DependencyUnavailableError("Azure Key Vault is not configured.")
            self._client = SecretClient(
                vault_url=self.settings.azure_key_vault_url,
                credential=get_azure_credential(),
            )
        return self._client

    async def get_openai_api_key(self) -> str:
        if self._api_key:
            return self._api_key
        try:
            secret = await asyncio.to_thread(
                self.client.get_secret, self.settings.openai_api_key_secret_name
            )
        except Exception as exc:
            raise DependencyUnavailableError(
                "The configured OpenAI API key is unavailable in Key Vault."
            ) from exc
        if not secret.value:
            raise DependencyUnavailableError("The configured OpenAI API key is empty.")
        self._api_key = secret.value
        return self._api_key
