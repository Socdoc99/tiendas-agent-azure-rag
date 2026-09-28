import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.config import Settings
from app.core.exceptions import DocumentNotFoundError, DocumentValidationError, StorageError
from app.schemas.documents import DocumentMetadata
from app.services.blob_storage import AzureBlobStore
from app.services.document_processing import extract_pages, split_pages
from app.services.embeddings import OpenAIEmbeddingProvider
from app.services.search import AzureSearchService

ALLOWED_TYPES = {"pdf", "docx", "txt", "md"}
MAX_EMBEDDING_BATCH = 16


class DocumentIngestionService:
    def __init__(
        self,
        settings: Settings,
        blob_store: AzureBlobStore,
        search: AzureSearchService,
        embeddings: OpenAIEmbeddingProvider,
    ) -> None:
        self.settings = settings
        self.blob_store = blob_store
        self.search = search
        self.embeddings = embeddings

    async def upload(
        self, *, filename: str, content_type: str | None, data: bytes, metadata: DocumentMetadata
    ) -> dict[str, Any]:
        safe_name = _safe_filename(filename)
        extension = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
        if extension not in ALLOWED_TYPES:
            raise DocumentValidationError("Only PDF, DOCX, TXT, and Markdown files are accepted.")
        if not data:
            raise DocumentValidationError("The uploaded document is empty.")
        if len(data) > self.settings.max_upload_mb * 1024 * 1024:
            raise DocumentValidationError("The document exceeds the configured upload limit.")
        _validate_content_type(extension, content_type)

        document_id = metadata.document_id or uuid4().hex
        _validate_document_id(document_id)
        metadata = metadata.model_copy(update={"document_id": document_id})
        file_hash = hashlib.sha256(data).hexdigest()
        raw_path = f"raw/{document_id}/original.{extension}"
        manifest_path = f"manifests/{document_id}.json"
        existing = await self.blob_store.read_bytes(manifest_path)
        if existing:
            try:
                previous = json.loads(existing)
            except json.JSONDecodeError as exc:
                raise StorageError("The document manifest is not valid JSON.") from exc
            if previous.get("file_hash") == file_hash:
                return previous
            previous_path = previous.get("blob_path")
        else:
            previous_path = None

        timestamp = datetime.now(UTC).isoformat()
        manifest = {
            "document_id": document_id,
            "document_name": safe_name,
            "extension": extension,
            "content_type": content_type or "application/octet-stream",
            "file_size": len(data),
            "file_hash": file_hash,
            "blob_path": raw_path,
            "metadata": metadata.model_dump(mode="json"),
            "status": "uploaded",
            "updated_at": timestamp,
            "superseded_blob_path": previous_path,
        }
        await self.blob_store.upload_document(
            raw_path,
            data,
            content_type or "application/octet-stream",
            {"document_id": document_id, "sha256": file_hash},
        )
        await self.blob_store.upload_manifest(manifest_path, manifest)
        return manifest

    async def index(self, document_id: str) -> dict[str, Any]:
        _validate_document_id(document_id)
        manifest = await self.get_manifest(document_id)
        raw = await self.blob_store.read_bytes(manifest["blob_path"])
        if raw is None:
            raise StorageError("The managed document source file is missing from Blob Storage.")
        if hashlib.sha256(raw).hexdigest() != manifest["file_hash"]:
            raise StorageError("The managed document hash does not match its manifest.")

        pages = extract_pages(raw, manifest["extension"])
        if not pages:
            raise DocumentValidationError("The document contains no extractable text.")
        metadata = DocumentMetadata.model_validate(manifest["metadata"])
        version = metadata.version or manifest["file_hash"][:12]
        chunks = split_pages(
            pages,
            document_id=document_id,
            version=version,
            chunk_size=self.settings.chunk_size_tokens,
            overlap=self.settings.chunk_overlap_tokens,
        )
        if not chunks:
            raise DocumentValidationError("The document contains no indexable text.")

        vector_size = self.settings.embedding_dimensions
        if vector_size is None:
            raise DocumentValidationError("Set EMBEDDING_DIMENSIONS before indexing documents.")
        vectors: list[list[float]] = []
        for offset in range(0, len(chunks), MAX_EMBEDDING_BATCH):
            batch = chunks[offset : offset + MAX_EMBEDDING_BATCH]
            vectors.extend(await self.embeddings.embed_texts([chunk.content for chunk in batch]))
        if len(vectors) != len(chunks) or any(len(vector) != vector_size for vector in vectors):
            raise DocumentValidationError("Embedding dimensions do not match the configured index.")

        documents = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            documents.append(
                {
                    "id": hashlib.sha256(
                        f"{document_id}:{version}:{chunk.chunk_number}:{chunk.content_hash}".encode()
                    ).hexdigest(),
                    "document_id": document_id,
                    "document_name": manifest["document_name"],
                    "content": chunk.content,
                    "content_vector": vector,
                    "content_hash": chunk.content_hash,
                    "page": chunk.page,
                    "chunk_number": chunk.chunk_number,
                    "category": metadata.category,
                    "department": metadata.department,
                    "country": metadata.country,
                    "store_id": metadata.store_id,
                    "language": metadata.language,
                    "version": version,
                    "is_active": metadata.is_active,
                    "source_path": manifest["blob_path"],
                    "source_url": metadata.source_url,
                    "created_at": datetime.now(UTC),
                    "allowed_groups": metadata.allowed_groups,
                }
            )

        existing_chunks = await self.search.get_document_chunks(document_id)
        await self.search.upload_chunks(documents)
        active_ids = {document["id"] for document in documents}
        stale_ids = [chunk["id"] for chunk in existing_chunks if chunk["id"] not in active_ids]
        await self.search.delete_chunk_ids(stale_ids)
        superseded_path = manifest.get("superseded_blob_path")
        if superseded_path and superseded_path != manifest["blob_path"]:
            await self.blob_store.delete_blob(superseded_path)

        manifest.update(
            status="indexed",
            chunk_count=len(documents),
            indexed_at=datetime.now(UTC).isoformat(),
        )
        manifest.pop("superseded_blob_path", None)
        await self.blob_store.upload_manifest(f"manifests/{document_id}.json", manifest)
        return {
            "document_id": document_id,
            "status": "indexed",
            "chunk_count": len(documents),
            "file_hash": manifest["file_hash"],
        }

    async def get_manifest(self, document_id: str) -> dict[str, Any]:
        _validate_document_id(document_id)
        content = await self.blob_store.read_bytes(f"manifests/{document_id}.json")
        if content is None:
            raise DocumentNotFoundError("The requested managed document was not found.")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise StorageError("The document manifest is not valid JSON.") from exc

    async def delete(self, document_id: str) -> None:
        manifest = await self.get_manifest(document_id)
        await self.search.delete_document_chunks(document_id)
        await self.blob_store.delete_blob(manifest["blob_path"])
        await self.blob_store.delete_blob(f"manifests/{document_id}.json")


def _safe_filename(filename: str) -> str:
    name = filename.replace("\\", "/").split("/")[-1].strip()
    if not name or name in {".", ".."}:
        raise DocumentValidationError("A valid filename is required.")
    return name[:255]


def _validate_document_id(document_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", document_id) or ".." in document_id:
        raise DocumentValidationError("document_id contains unsupported characters.")


def _validate_content_type(extension: str, content_type: str | None) -> None:
    allowed = {
        "pdf": {"application/pdf", "application/octet-stream"},
        "docx": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
        },
        "txt": {"text/plain", "application/octet-stream"},
        "md": {"text/markdown", "text/plain", "application/octet-stream"},
    }
    if content_type and content_type not in allowed[extension]:
        raise DocumentValidationError("The file content type does not match its extension.")
