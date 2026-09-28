import json

import pytest

from app.core.config import Settings
from app.schemas.documents import DocumentMetadata
from app.services.ingestion import DocumentIngestionService


class FakeBlobStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def read_bytes(self, path: str) -> bytes | None:
        return self.objects.get(path)

    async def upload_document(
        self, path: str, data: bytes, content_type: str, metadata: dict
    ) -> None:
        self.objects[path] = data

    async def upload_manifest(self, path: str, manifest: dict) -> None:
        self.objects[path] = json.dumps(manifest).encode()

    async def delete_blob(self, path: str) -> bool:
        return self.objects.pop(path, None) is not None


class FakeSearch:
    def __init__(self) -> None:
        self.documents: dict[str, dict] = {}

    async def get_document_chunks(self, document_id: str) -> list[dict]:
        return [doc for doc in self.documents.values() if doc["document_id"] == document_id]

    async def upload_chunks(self, documents: list[dict]) -> None:
        self.documents.update({doc["id"]: doc for doc in documents})

    async def delete_chunk_ids(self, chunk_ids: list[str]) -> int:
        for chunk_id in chunk_ids:
            self.documents.pop(chunk_id, None)
        return len(chunk_ids)

    async def delete_document_chunks(self, document_id: str) -> int:
        old = await self.get_document_chunks(document_id)
        return await self.delete_chunk_ids([item["id"] for item in old])


class FakeEmbeddings:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.25, 0.5, 0.75] for _ in texts]


@pytest.mark.asyncio
async def test_upload_and_index_document_is_idempotent() -> None:
    settings = Settings(
        _env_file=None,
        embedding_dimensions=3,
        chunk_size_tokens=20,
        chunk_overlap_tokens=4,
    )
    blob = FakeBlobStore()
    search = FakeSearch()
    service = DocumentIngestionService(settings, blob, search, FakeEmbeddings())
    metadata = DocumentMetadata(document_id="operations-manual", category="manual")
    content = ("Abrir la tienda siguiendo el procedimiento. " * 40).encode()

    uploaded = await service.upload(
        filename="manual.txt",
        content_type="text/plain",
        data=content,
        metadata=metadata,
    )
    indexed = await service.index("operations-manual")
    repeated_upload = await service.upload(
        filename="manual.txt",
        content_type="text/plain",
        data=content,
        metadata=metadata,
    )

    assert uploaded["status"] == "uploaded"
    assert indexed["status"] == "indexed"
    assert indexed["chunk_count"] > 1
    assert repeated_upload["status"] == "indexed"
    assert len(search.documents) == indexed["chunk_count"]
    assert all(doc["is_active"] for doc in search.documents.values())
    assert "raw/operations-manual/original.txt" in blob.objects
