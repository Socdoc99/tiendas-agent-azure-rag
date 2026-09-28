import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.exceptions import ServiceError
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    application = FastAPI(title="Tiendas Agent", version="0.1.0")
    application.state.settings = app_settings
    application.include_router(health_router)

    @application.middleware("http")
    async def add_request_context(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        started = perf_counter()
        response = await call_next(request)
        latency_ms = round((perf_counter() - started) * 1000)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request_completed",
            extra={
                "request_id": request_id,
                "endpoint": request.url.path,
                "http_status": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response

    @application.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            "service_error",
            extra={"request_id": request_id, "error_type": exc.code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {"code": exc.code, "message": exc.message},
                "request_id": request_id,
            },
        )

    return application


app = create_app()
