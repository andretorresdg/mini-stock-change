"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mini_exchange.api.routers.health import router as health_router
from mini_exchange.api.routers.orders import router as orders_router
from mini_exchange.order_gateway.service import OrderGatewayService

# MVP allows only local frontend origins.
# Production should configure exact deployed origins
# through environment config.
_LOCAL_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app(
    order_gateway: OrderGatewayService | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(title="Mini Exchange API")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_LOCAL_ORIGINS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    # MVP keeps one in-memory gateway instance in the app.
    # Production should use durable state before running multiple
    # workers to avoid split-brain or lost commands.
    application.state.order_gateway = order_gateway or OrderGatewayService()
    application.include_router(health_router)
    application.include_router(orders_router)
    return application
