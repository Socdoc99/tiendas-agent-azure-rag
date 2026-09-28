from app.core.config import Settings
from app.services.embeddings import OpenAIEmbeddingProvider
from app.services.search import AzureSearchService


class HybridRetriever:
    def __init__(
        self,
        settings: Settings,
        search: AzureSearchService,
        embeddings: OpenAIEmbeddingProvider,
    ) -> None:
        self.settings = settings
        self.search = search
        self.embeddings = embeddings

    async def retrieve(self, query: str, filters: dict[str, str | None]) -> list[dict]:
        vector = await self.embeddings.embed_texts([query])
        if not vector:
            return []
        candidates = await self.search.hybrid_search(
            query,
            vector[0],
            top=max(self.settings.rag_top_k * 3, self.settings.rag_top_k),
            vector_k=self.settings.rag_vector_k,
            filters=filters,
        )
        selected: list[dict] = []
        per_document: dict[str, int] = {}
        for candidate in candidates:
            document_id = candidate.get("document_id", "")
            if per_document.get(document_id, 0) >= 3:
                continue
            per_document[document_id] = per_document.get(document_id, 0) + 1
            selected.append(candidate)
            if len(selected) >= self.settings.rag_top_k:
                break
        return selected
