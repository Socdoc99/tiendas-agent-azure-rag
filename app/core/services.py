from dataclasses import dataclass

from app.core.config import Settings
from app.services.blob_storage import AzureBlobStore
from app.services.embeddings import OpenAIEmbeddingProvider
from app.services.ingestion import DocumentIngestionService
from app.services.llm import OpenAIProvider
from app.services.retrieval import HybridRetriever
from app.services.search import AzureSearchService
from app.services.secret_provider import KeyVaultSecretProvider


@dataclass
class ApplicationServices:
    search: AzureSearchService
    blob_store: AzureBlobStore
    secrets: KeyVaultSecretProvider
    embeddings: OpenAIEmbeddingProvider
    retriever: HybridRetriever
    llm: OpenAIProvider
    ingestion: DocumentIngestionService


def build_application_services(settings: Settings) -> ApplicationServices:
    search = AzureSearchService(settings)
    blob_store = AzureBlobStore(settings)
    secrets = KeyVaultSecretProvider(settings)
    embeddings = OpenAIEmbeddingProvider(settings, secrets)
    return ApplicationServices(
        search=search,
        blob_store=blob_store,
        secrets=secrets,
        embeddings=embeddings,
        retriever=HybridRetriever(settings, search, embeddings),
        llm=OpenAIProvider(settings, secrets),
        ingestion=DocumentIngestionService(settings, blob_store, search, embeddings),
    )
