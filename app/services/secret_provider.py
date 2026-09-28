import asyncio

from azure.keyvault.secrets import SecretClient

from app.core.azure import get_azure_credential
from app.core.config import Settings
from app.core.exceptions import DependencyUnavailableError


class KeyVaultSecretProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: SecretClient | None = None
        self._secret_cache: dict[str, str] = {}

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

    def get_secret_value(self, secret_name: str) -> str:
        """Resolve a named secret without logging or exposing its value."""
        if secret_name in self._secret_cache:
            return self._secret_cache[secret_name]
        if not secret_name.strip():
            raise DependencyUnavailableError("A required Key Vault secret name is not configured.")
        try:
            secret = self.client.get_secret(secret_name)
        except Exception as exc:
            raise DependencyUnavailableError(
                "A required secret is unavailable in Key Vault."
            ) from exc
        if not secret.value:
            raise DependencyUnavailableError("A required Key Vault secret is empty.")
        self._secret_cache[secret_name] = secret.value
        return secret.value

    async def get_openai_api_key(self) -> str:
        return await asyncio.to_thread(
            self.get_secret_value, self.settings.openai_api_key_secret_name
        )
