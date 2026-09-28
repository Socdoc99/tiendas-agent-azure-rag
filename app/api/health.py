from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Report process health without calling external services."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    """Report whether required service configuration is present."""
    settings: Settings = request.app.state.settings
    missing = settings.missing_runtime_settings()
    dependencies = {
        "search": "configured" if settings.azure_search_endpoint else "not_configured",
        "storage": "configured" if settings.azure_storage_account_url else "not_configured",
        "keyvault": "configured" if settings.azure_key_vault_url else "not_configured",
        "llm": "configured"
        if settings.openai_chat_model and settings.openai_embedding_model
        else "not_configured",
    }
    status = "ready" if not missing else "not_ready"
    status_code = 200 if not missing else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": status, "dependencies": dependencies, "missing_settings": missing},
    )
