from fastapi import Request

from app.core.services import ApplicationServices, build_application_services


def get_services(request: Request) -> ApplicationServices:
    services = getattr(request.app.state, "services", None)
    if services is None:
        services = build_application_services(request.app.state.settings)
        request.app.state.services = services
    return services
