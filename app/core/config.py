from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True, extra="ignore"
    )

    environment: str = "sbx"
    azure_region: str | None = None
    business_timezone: str = "America/Bogota"
    demo_business_id: str = ""
    demo_establishment_id: str = ""

    sql_server: str = ""
    sql_database: str = ""
    sql_username: str = ""
    sql_password_secret_name: str = "sql-password"
    sql_driver: str = "ODBC Driver 18 for SQL Server"
    sql_query_timeout_seconds: int = Field(default=15, gt=0, le=120)
    sql_max_rows: int = Field(default=200, gt=0)
    agent_max_database_queries: int = Field(default=10, ge=1, le=10)

    azure_search_endpoint: str | None = None
    azure_search_index: str = "idx-tiendas-knowledge-v1"
    azure_storage_account_url: str | None = None
    azure_storage_container: str = "knowledge"
    azure_key_vault_url: str | None = None
    openai_api_key_secret_name: str = "openai-api-key"

    openai_chat_model: str | None = None
    openai_embedding_model: str | None = None
    embedding_dimensions: int | None = Field(default=None, gt=0)

    chunk_size_tokens: int = 800
    chunk_overlap_tokens: int = 120
    rag_top_k: int = 8
    rag_vector_k: int = 30
    max_chat_history_messages: int = 8
    max_query_length: int = 4000
    max_upload_mb: int = 25
    openai_timeout_seconds: float = Field(default=30, gt=0, le=120)
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
            "EMBEDDING_DIMENSIONS": self.embedding_dimensions,
        }
        return [name for name, value in required.items() if not value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
