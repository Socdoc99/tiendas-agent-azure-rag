from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import Settings
from app.core.exceptions import EmbeddingError
from app.services.secret_provider import KeyVaultSecretProvider


def _is_transient_openai_error(exc: BaseException) -> bool:
    return getattr(exc, "status_code", None) in {429, 500, 502, 503, 504}


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings, secrets: KeyVaultSecretProvider) -> None:
        self.settings = settings
        self.secrets = secrets
        self._client: AsyncOpenAI | None = None

    async def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=await self.secrets.get_openai_api_key(),
                timeout=self.settings.openai_timeout_seconds,
                max_retries=0,
            )
        return self._client

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.settings.openai_embedding_model:
            raise EmbeddingError("Set OPENAI_EMBEDDING_MODEL before requesting embeddings.")
        if self.settings.embedding_dimensions is None:
            raise EmbeddingError("Set EMBEDDING_DIMENSIONS for the configured embedding model.")
        client = await self._get_client()
        try:
            response = await self._create_embeddings(client, texts)
            vectors = [
                item.embedding for item in sorted(response.data, key=lambda item: item.index)
            ]
        except Exception as exc:
            raise EmbeddingError("The embedding provider could not process the text.") from exc
        if len(vectors) != len(texts) or any(
            len(vector) != self.settings.embedding_dimensions for vector in vectors
        ):
            raise EmbeddingError("Embedding output dimensions do not match configuration.")
        return vectors

    @retry(
        retry=retry_if_exception(_is_transient_openai_error),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def _create_embeddings(self, client: AsyncOpenAI, texts: list[str]):
        return await client.embeddings.create(
            model=self.settings.openai_embedding_model,
            input=texts,
            dimensions=self.settings.embedding_dimensions,
        )
