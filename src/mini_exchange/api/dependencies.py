"""FastAPI dependency injection."""

from fastapi import Request

from mini_exchange.order_gateway.service import OrderGatewayService


def get_order_gateway_service(request: Request) -> OrderGatewayService:
    """Retrieve the OrderGatewayService from app state."""
    service = getattr(request.app.state, "order_gateway", None)
    if not isinstance(service, OrderGatewayService):
        msg = "OrderGatewayService not configured on app state"
        raise RuntimeError(msg)
    return service
