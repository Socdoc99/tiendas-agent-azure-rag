import asyncio
import json
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

from app.core.azure import get_azure_credential
from app.core.config import Settings
from app.core.exceptions import StorageError


class AzureBlobStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._container = None

    @property
    def container(self):
        if self._container is None:
            if not self.settings.azure_storage_account_url:
                raise StorageError("Azure Blob Storage account URL is not configured.")
            self._container = BlobServiceClient(
                account_url=self.settings.azure_storage_account_url,
                credential=get_azure_credential(),
            ).get_container_client(self.settings.azure_storage_container)
        return self._container

    async def check_connection(self) -> None:
        try:
            await asyncio.to_thread(self.container.get_container_properties)
        except Exception as exc:
            raise StorageError("The configured Blob Storage container is unavailable.") from exc

    async def upload_document(
        self, path: str, data: bytes, content_type: str, metadata: dict[str, str]
    ) -> None:
        try:
            await asyncio.to_thread(
                self.container.upload_blob,
                name=path,
                data=data,
                overwrite=True,
                metadata=metadata,
                content_settings=ContentSettings(content_type=content_type),
            )
        except Exception as exc:
            raise StorageError("The document could not be saved to private Blob Storage.") from exc

    async def upload_manifest(self, path: str, manifest: dict[str, Any]) -> None:
        encoded = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
        await self.upload_document(
            path, encoded, "application/json", {"document_id": str(manifest["document_id"])}
        )

    async def read_bytes(self, path: str) -> bytes | None:
        try:
            blob = self.container.get_blob_client(path)
            downloader = await asyncio.to_thread(blob.download_blob)
            return await asyncio.to_thread(downloader.readall)
        except ResourceNotFoundError:
            return None
        except Exception as exc:
            raise StorageError("A managed document could not be read from Blob Storage.") from exc

    async def delete_blob(self, path: str) -> bool:
        try:
            blob = self.container.get_blob_client(path)
            await asyncio.to_thread(blob.delete_blob, delete_snapshots="include")
            return True
        except ResourceNotFoundError:
            return False
        except Exception as exc:
            raise StorageError(
                "A managed document could not be deleted from Blob Storage."
            ) from exc
