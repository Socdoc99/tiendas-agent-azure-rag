from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError

from app.api.dependencies import get_services
from app.core.config import Settings
from app.core.exceptions import DocumentValidationError
from app.schemas.documents import DocumentMetadata, DocumentStatus

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("", response_model=DocumentStatus, status_code=201)
async def upload_document(
    request: Request,
    file: Annotated[UploadFile, File()],
    metadata: Annotated[str | None, Form()] = None,
) -> DocumentStatus:
    settings: Settings = request.app.state.settings
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    try:
        parsed_metadata = DocumentMetadata.model_validate_json(metadata or "{}")
    except ValidationError as exc:
        raise DocumentValidationError("Document metadata is invalid.") from exc
    result = await get_services(request).ingestion.upload(
        filename=file.filename or "",
        content_type=file.content_type,
        data=content,
        metadata=parsed_metadata,
    )
    return DocumentStatus(
        document_id=result["document_id"],
        document_name=result["document_name"],
        status=result["status"],
        file_hash=result["file_hash"],
        file_size=result["file_size"],
        chunk_count=result.get("chunk_count", 0),
        updated_at=result.get("updated_at"),
    )


@router.post("/{document_id}/index", response_model=DocumentStatus)
async def index_document(document_id: str, request: Request) -> DocumentStatus:
    result = await get_services(request).ingestion.index(document_id)
    manifest = await get_services(request).ingestion.get_manifest(document_id)
    return DocumentStatus(
        document_id=document_id,
        document_name=manifest["document_name"],
        status=result["status"],
        file_hash=result["file_hash"],
        file_size=manifest["file_size"],
        chunk_count=result["chunk_count"],
        updated_at=manifest.get("indexed_at"),
    )


@router.get("/{document_id}", response_model=DocumentStatus)
async def get_document(document_id: str, request: Request) -> DocumentStatus:
    manifest = await get_services(request).ingestion.get_manifest(document_id)
    return DocumentStatus(
        document_id=manifest["document_id"],
        document_name=manifest["document_name"],
        status=manifest["status"],
        file_hash=manifest["file_hash"],
        file_size=manifest["file_size"],
        chunk_count=manifest.get("chunk_count", 0),
        updated_at=manifest.get("indexed_at") or manifest.get("updated_at"),
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str, request: Request) -> Response:
    await get_services(request).ingestion.delete(document_id)
    return Response(status_code=204)
