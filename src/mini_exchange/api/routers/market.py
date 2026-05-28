"""Market data endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from mini_exchange.api.adapters import (
    book_snapshot_to_response,
    market_trades_to_response,
)
from mini_exchange.api.dependencies import get_order_gateway_service
from mini_exchange.api.schemas import BookSnapshotResponse, MarketTradesResponse
from mini_exchange.order_gateway.service import OrderGatewayService

router = APIRouter(prefix="/api/v1/market", tags=["market"])

_SYMBOL_PATH = Path(min_length=1, max_length=16, pattern=r"^[A-Za-z0-9._\-]+$")


@router.get(
    "/{symbol}/trades",
    response_model=MarketTradesResponse,
)
def get_market_trades(
    symbol: Annotated[str, _SYMBOL_PATH],
    service: Annotated[OrderGatewayService, Depends(get_order_gateway_service)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> MarketTradesResponse:
    """Return recent market trades for a symbol, newest first."""
    result = service.get_market_trades(symbol, limit=limit)
    return market_trades_to_response(result)


@router.get(
    "/{symbol}/book",
    response_model=BookSnapshotResponse,
)
def get_book_snapshot(
    symbol: Annotated[str, _SYMBOL_PATH],
    service: Annotated[OrderGatewayService, Depends(get_order_gateway_service)],
    depth: Annotated[int | None, Query(ge=1, le=50)] = None,
) -> BookSnapshotResponse:
    """Return the current order book snapshot for a symbol."""
    result = service.get_book_snapshot(symbol, depth=depth)
    return book_snapshot_to_response(result)
