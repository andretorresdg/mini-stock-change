"""FastAPI application factory."""

from fastapi import FastAPI

from mini_exchange.api.routers.health import router as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(title="Mini Exchange API")
    application.include_router(health_router)
    return application
