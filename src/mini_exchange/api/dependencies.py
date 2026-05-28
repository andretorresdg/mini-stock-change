"""FastAPI dependency injection."""

from fastapi import Request

from mini_exchange.api.services.order_gateway import OrderGatewayService


def get_order_gateway_service(request: Request) -> OrderGatewayService:
    """Retrieve the OrderGatewayService from app state."""
    return request.app.state.order_gateway_service  # type: ignore[no-any-return]
