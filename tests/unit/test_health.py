from uuid import UUID

import httpx
import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.mark.asyncio
async def test_health_does_not_require_external_services() -> None:
    transport = httpx.ASGITransport(app=create_app(Settings(_env_file=None)))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        UUID(response.headers["X-Request-ID"])


@pytest.mark.asyncio
async def test_root_serves_the_chat_ui() -> None:
    transport = httpx.ASGITransport(app=create_app(Settings(_env_file=None)))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

        assert response.status_code == 200
        assert "Asistente documental" in response.text


@pytest.mark.asyncio
async def test_readiness_reports_missing_runtime_configuration() -> None:
    transport = httpx.ASGITransport(app=create_app(Settings(_env_file=None)))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")

        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"
        assert "OPENAI_CHAT_MODEL" in response.json()["missing_settings"]
