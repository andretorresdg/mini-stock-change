"""FastAPI application factory."""

from fastapi import FastAPI

from mini_exchange.api.routers.health import router as health_router
from mini_exchange.api.routers.orders import router as orders_router
from mini_exchange.order_gateway.service import OrderGatewayService


def create_app(
    order_gateway: OrderGatewayService | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(title="Mini Exchange API")
    # MVP keeps one in-memory gateway instance in the app.
    # Production should use durable state before running multiple
    # workers to avoid split-brain or lost commands.
    application.state.order_gateway = order_gateway or OrderGatewayService()
    application.include_router(health_router)
    application.include_router(orders_router)
    return application
