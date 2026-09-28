"""Create the configured Azure AI Search index from the local development shell."""

import os
import sys
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.azure import get_azure_credential
from app.core.config import Settings
from app.services.search_index import build_search_index


def main() -> int:
    settings = Settings()
    required = {
        "AZURE_SEARCH_ENDPOINT": settings.azure_search_endpoint,
        "OPENAI_EMBEDDING_MODEL": settings.openai_embedding_model,
        "EMBEDDING_DIMENSIONS": settings.embedding_dimensions,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        print("Missing configuration: " + ", ".join(missing), file=sys.stderr)
        return 2

    admin_key = os.environ.get("AZURE_SEARCH_ADMIN_KEY")
    credential = AzureKeyCredential(admin_key) if admin_key else get_azure_credential()
    client = SearchIndexClient(settings.azure_search_endpoint, credential)
    try:
        client.create_or_update_index(
            build_search_index(settings.azure_search_index, settings.embedding_dimensions)
        )
    finally:
        client.close()
    print(
        f"Search index {settings.azure_search_index} is ready "
        f"with {settings.embedding_dimensions} vector dimensions."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
