"""Order endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse

from mini_exchange.api.dependencies import get_order_gateway_service
from mini_exchange.api.schemas import (
    ErrorResponse,
    OrderResponse,
    SubmitOrderRequest,
)
from mini_exchange.api.services.order_gateway import (
    ExpiredOrderError,
    IdempotencyConflictError,
    OrderGatewayError,
    OrderGatewayService,
    OrderNotFoundError,
)

router = APIRouter(prefix="/api/v1", tags=["orders"])

_BROKER_PATH = Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._\-]+$")


@router.post(
    "/brokers/{broker_id}/orders",
    response_model=OrderResponse,
    status_code=201,
)
def submit_order(
    broker_id: Annotated[str, _BROKER_PATH],
    body: SubmitOrderRequest,
    service: Annotated[OrderGatewayService, Depends(get_order_gateway_service)],
) -> OrderResponse | JSONResponse:
    """Submit a new order for the given broker."""
    try:
        return service.submit_order(broker_id, body)
    except IdempotencyConflictError as exc:
        error = ErrorResponse(code="IDEMPOTENCY_CONFLICT", message=str(exc))
        return JSONResponse(
            status_code=409,
            content=error.model_dump(),
        )
    except ExpiredOrderError as exc:
        error = ErrorResponse(code="EXPIRED_ORDER", message=str(exc))
        return JSONResponse(
            status_code=400,
            content=error.model_dump(),
        )
    except OrderGatewayError as exc:
        error = ErrorResponse(code="ORDER_GATEWAY_ERROR", message=str(exc))
        return JSONResponse(
            status_code=400,
            content=error.model_dump(),
        )


@router.get(
    "/brokers/{broker_id}/orders/{order_id}",
    response_model=OrderResponse,
)
def get_order(
    broker_id: Annotated[str, _BROKER_PATH],
    order_id: Annotated[str, Path(min_length=1, max_length=128)],
    service: Annotated[OrderGatewayService, Depends(get_order_gateway_service)],
) -> OrderResponse | JSONResponse:
    """Retrieve the current status of an order."""
    try:
        return service.get_order(broker_id, order_id)
    except OrderNotFoundError:
        error = ErrorResponse(code="ORDER_NOT_FOUND", message="order not found")
        return JSONResponse(
            status_code=404,
            content=error.model_dump(),
        )
