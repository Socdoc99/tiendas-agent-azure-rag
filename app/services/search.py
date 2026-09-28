import asyncio
from typing import Any

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery

from app.core.azure import get_azure_credential
from app.core.config import Settings
from app.core.exceptions import SearchError
from app.services.search_index import build_search_index


class AzureSearchService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._index_client: SearchIndexClient | None = None
        self._search_client: SearchClient | None = None

    @property
    def index_client(self) -> SearchIndexClient:
        if self._index_client is None:
            if not self.settings.azure_search_endpoint:
                raise SearchError("Azure AI Search endpoint is not configured.")
            self._index_client = SearchIndexClient(
                self.settings.azure_search_endpoint, get_azure_credential()
            )
        return self._index_client

    @property
    def search_client(self) -> SearchClient:
        if self._search_client is None:
            if not self.settings.azure_search_endpoint:
                raise SearchError("Azure AI Search endpoint is not configured.")
            self._search_client = SearchClient(
                self.settings.azure_search_endpoint,
                self.settings.azure_search_index,
                get_azure_credential(),
            )
        return self._search_client

    async def check_connection(self) -> None:
        try:
            await asyncio.to_thread(self.index_client.get_index, self.settings.azure_search_index)
        except Exception as exc:
            raise SearchError("Azure AI Search index is unavailable.") from exc

    async def create_or_update_index(self) -> None:
        if self.settings.embedding_dimensions is None:
            raise SearchError("Set EMBEDDING_DIMENSIONS to the configured embedding model size.")
        index = build_search_index(
            self.settings.azure_search_index, self.settings.embedding_dimensions
        )
        try:
            await asyncio.to_thread(self.index_client.create_or_update_index, index)
        except Exception as exc:
            raise SearchError("Azure AI Search index could not be created or updated.") from exc

    async def upload_chunks(self, chunks: list[dict[str, Any]]) -> None:
        if not chunks:
            return
        try:
            result = await asyncio.to_thread(self.search_client.upload_documents, chunks)
        except Exception as exc:
            raise SearchError("Chunks could not be uploaded to Azure AI Search.") from exc
        failures = [item for item in result if not item.succeeded]
        if failures:
            raise SearchError("Azure AI Search rejected one or more document chunks.")

    async def hybrid_search(
        self,
        query: str,
        vector: list[float],
        *,
        top: int,
        vector_k: int,
        filters: dict[str, str | None],
    ) -> list[dict[str, Any]]:
        filter_expression = _build_filter(filters)
        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=vector_k,
            fields="content_vector",
        )
        try:
            results = await asyncio.to_thread(
                self.search_client.search,
                search_text=query,
                vector_queries=[vector_query],
                filter=filter_expression,
                top=top,
                select=[
                    "id",
                    "document_id",
                    "document_name",
                    "content",
                    "page",
                    "chunk_number",
                    "category",
                    "department",
                    "country",
                    "store_id",
                    "language",
                    "version",
                    "source_path",
                    "source_url",
                ],
            )
            documents = await asyncio.to_thread(list, results)
        except Exception as exc:
            raise SearchError("Hybrid search failed.") from exc
        return [
            {**document, "score": document.get("@search.score")}
            for document in documents
        ]

    async def get_document_chunks(self, document_id: str) -> list[dict[str, Any]]:
        filter_expression = f"document_id eq '{_odata_string(document_id)}'"
        try:
            results = await asyncio.to_thread(
                self.search_client.search,
                search_text="*",
                filter=filter_expression,
                select=["id", "document_id", "document_name", "page", "chunk_number"],
            )
            return await asyncio.to_thread(list, results)
        except Exception as exc:
            raise SearchError("Azure AI Search document lookup failed.") from exc

    async def delete_document_chunks(self, document_id: str) -> int:
        chunks = await self.get_document_chunks(document_id)
        if not chunks:
            return 0
        return await self.delete_chunk_ids([chunk["id"] for chunk in chunks])

    async def delete_chunk_ids(self, chunk_ids: list[str]) -> int:
        if not chunk_ids:
            return 0
        try:
            result = await asyncio.to_thread(
                self.search_client.delete_documents,
                documents=[{"id": chunk_id} for chunk_id in chunk_ids],
            )
        except Exception as exc:
            raise SearchError("Managed document chunks could not be deleted.") from exc
        if any(not item.succeeded for item in result):
            raise SearchError("Azure AI Search rejected one or more chunk deletions.")
        return len(chunk_ids)


def _odata_string(value: str) -> str:
    return value.replace("'", "''")


def _build_filter(filters: dict[str, str | None]) -> str:
    clauses = ["is_active eq true"]
    for field in ("country", "store_id", "department", "category"):
        value = filters.get(field)
        if value:
            clauses.append(f"{field} eq '{_odata_string(value)}'")
    return " and ".join(clauses)
