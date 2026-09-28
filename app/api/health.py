from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.core.exceptions import ServiceError
from app.services.blob_storage import AzureBlobStore
from app.services.search import AzureSearchService
from app.services.secret_provider import KeyVaultSecretProvider

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Report process health without calling external services."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    """Check configuration and inexpensive access to the required Azure services."""
    settings: Settings = request.app.state.settings
    missing = settings.missing_runtime_settings()
    dependencies: dict[str, str] = {}
    for name, factory, check in (
        ("search", AzureSearchService, "check_connection"),
        ("storage", AzureBlobStore, "check_connection"),
        ("keyvault", KeyVaultSecretProvider, "get_openai_api_key"),
    ):
        try:
            client = factory(settings)
            await getattr(client, check)()
            dependencies[name] = "ok"
        except ServiceError:
            dependencies[name] = "unavailable"
        except Exception:
            dependencies[name] = "unavailable"
    dependencies["llm"] = (
        "configured"
        if settings.openai_chat_model and settings.openai_embedding_model
        else "not_configured"
    )
    is_ready = not missing and all(
        dependencies.get(name) == "ok" for name in ("search", "storage", "keyvault")
    )
    status = "ready" if is_ready else "not_ready"
    status_code = 200 if is_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": status, "dependencies": dependencies, "missing_settings": missing},
    )
