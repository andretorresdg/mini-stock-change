"""FastAPI application factory."""

from fastapi import FastAPI

from mini_exchange.api.routers.health import router as health_router
from mini_exchange.api.routers.orders import router as orders_router
from mini_exchange.api.services.order_gateway import OrderGatewayService


def create_app(
    order_gateway_service: OrderGatewayService | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(title="Mini Exchange API")
    application.state.order_gateway_service = (
        order_gateway_service or OrderGatewayService()
    )
    application.include_router(health_router)
    application.include_router(orders_router)
    return application
