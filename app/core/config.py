from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "sbx"
    azure_region: str | None = None

    azure_search_endpoint: str | None = None
    azure_search_index: str = "idx-tiendas-knowledge-v1"
    azure_storage_account_url: str | None = None
    azure_storage_container: str = "knowledge"
    azure_key_vault_url: str | None = None
    openai_api_key_secret_name: str = "openai-api-key"

    openai_chat_model: str | None = None
    openai_embedding_model: str | None = None
    embedding_dimensions: int = 1536

    chunk_size_tokens: int = 800
    chunk_overlap_tokens: int = 120
    rag_top_k: int = 8
    rag_vector_k: int = 30
    max_chat_history_messages: int = 8
    max_query_length: int = 4000
    max_upload_mb: int = 25
    applicationinsights_connection_string: str | None = None
    log_level: str = "INFO"

    def missing_runtime_settings(self) -> list[str]:
        required = {
            "AZURE_SEARCH_ENDPOINT": self.azure_search_endpoint,
            "AZURE_SEARCH_INDEX": self.azure_search_index,
            "AZURE_STORAGE_ACCOUNT_URL": self.azure_storage_account_url,
            "AZURE_KEY_VAULT_URL": self.azure_key_vault_url,
            "OPENAI_CHAT_MODEL": self.openai_chat_model,
            "OPENAI_EMBEDDING_MODEL": self.openai_embedding_model,
        }
        return [name for name, value in required.items() if not value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
