"""Adapters between API schemas and Order Gateway DTOs."""

from mini_exchange.api.schemas import (
    ApiOrderSide,
    ApiOrderStatus,
    BookLevelResponse,
    BookSnapshotResponse,
    OrderResponse,
    SubmitOrderRequest,
    TradeResponse,
)
from mini_exchange.order_gateway.models import (
    GatewayBookSnapshot,
    GatewayOrder,
    GatewayOrderStatus,
    GatewaySubmitOrder,
    GatewayTrade,
)

_STATUS_MAP: dict[GatewayOrderStatus, ApiOrderStatus] = {
    GatewayOrderStatus.OPEN: ApiOrderStatus.OPEN,
    GatewayOrderStatus.PARTIALLY_FILLED: ApiOrderStatus.PARTIALLY_FILLED,
    GatewayOrderStatus.FILLED: ApiOrderStatus.FILLED,
    GatewayOrderStatus.CANCELED: ApiOrderStatus.CANCELED,
    GatewayOrderStatus.EXPIRED: ApiOrderStatus.EXPIRED,
}


def to_gateway_submit(broker_id: str, body: SubmitOrderRequest) -> GatewaySubmitOrder:
    """Convert an API submit request into a gateway input DTO."""
    return GatewaySubmitOrder(
        broker_id=broker_id,
        document_number=body.document_number,
        client_order_id=body.client_order_id,
        side=body.side.to_core_side(),
        valid_until=body.valid_until,
        symbol=body.symbol,
        price=body.price,
        quantity=body.quantity,
    )


def trade_to_response(trade: GatewayTrade) -> TradeResponse:
    """Convert a gateway trade DTO into an API trade response."""
    return TradeResponse(
        trade_id=trade.trade_id,
        sequence=trade.sequence,
        symbol=trade.symbol,
        buyer_order_id=trade.buyer_order_id,
        seller_order_id=trade.seller_order_id,
        buyer_broker_id=trade.buyer_broker_id,
        seller_broker_id=trade.seller_broker_id,
        price=trade.price,
        quantity=trade.quantity,
    )


def book_snapshot_to_response(snapshot: GatewayBookSnapshot) -> BookSnapshotResponse:
    """Convert a gateway book snapshot DTO into an API response."""
    return BookSnapshotResponse(
        symbol=snapshot.symbol,
        bids=tuple(
            BookLevelResponse(price=lvl.price, quantity=lvl.quantity)
            for lvl in snapshot.bids
        ),
        asks=tuple(
            BookLevelResponse(price=lvl.price, quantity=lvl.quantity)
            for lvl in snapshot.asks
        ),
    )


def order_to_response(order: GatewayOrder) -> OrderResponse:
    """Convert a gateway order DTO into an API order response."""
    return OrderResponse(
        order_id=order.order_id,
        broker_id=order.broker_id,
        client_order_id=order.client_order_id,
        document_number=order.document_number,
        side=ApiOrderSide.from_core_side(order.side),
        symbol=order.symbol,
        price=order.price,
        quantity=order.quantity,
        remaining_quantity=order.remaining_quantity,
        filled_quantity=order.filled_quantity,
        status=_STATUS_MAP[order.status],
        valid_until=order.valid_until,
        trades=tuple(trade_to_response(t) for t in order.trades),
    )
