"""In-memory order gateway service."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mini_exchange.api.schemas import (
    ApiOrderSide,
    ApiOrderStatus,
    OrderResponse,
    SubmitOrderRequest,
    TradeResponse,
)
from mini_exchange.orderbook import MatchingEngine, OrderStatus

if TYPE_CHECKING:
    from collections.abc import Callable

_BROKER_ID_RE = re.compile(r"^[A-Za-z0-9._\-]+$")


class OrderGatewayError(Exception):
    """Base error for the order gateway service."""


class ExpiredOrderError(OrderGatewayError):
    """Raised when an order has expired at submission time."""


class OrderNotFoundError(OrderGatewayError):
    """Raised when an order is not found or inaccessible."""


class IdempotencyConflictError(OrderGatewayError):
    """Raised when client_order_id is reused with different parameters."""


_STATUS_MAP: dict[OrderStatus, ApiOrderStatus] = {
    OrderStatus.OPEN: ApiOrderStatus.OPEN,
    OrderStatus.PARTIALLY_FILLED: ApiOrderStatus.PARTIALLY_FILLED,
    OrderStatus.FILLED: ApiOrderStatus.FILLED,
    OrderStatus.CANCELED: ApiOrderStatus.CANCELED,
}


@dataclass(frozen=True, slots=True)
class OrderMetadata:
    """API-level metadata not tracked by the matching core."""

    broker_id: str
    client_order_id: str | None
    document_number: str
    side: ApiOrderSide
    symbol: str
    valid_until: datetime
    price: int
    quantity: int


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


_IdempotencyKey = tuple[str, str]
_Fingerprint = tuple[str, str, str, str, str, str, int, int]


class OrderGatewayService:
    """Adapts broker-facing requests to the deterministic matching engine."""

    __slots__ = (
        "_clock",
        "_engine",
        "_expired_orders",
        "_idempotency",
        "_metadata",
        "_order_trades",
    )

    def __init__(
        self,
        engine: MatchingEngine | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._engine = engine or MatchingEngine()
        self._clock = clock or _utc_now
        self._metadata: dict[str, OrderMetadata] = {}
        self._order_trades: dict[str, list[str]] = defaultdict(list)
        self._idempotency: dict[_IdempotencyKey, tuple[_Fingerprint, str]] = {}
        self._expired_orders: set[str] = set()

    def submit_order(
        self, broker_id: str, request: SubmitOrderRequest
    ) -> OrderResponse:
        """Submit a new order through the gateway."""
        self._validate_broker_id(broker_id)
        now = self._clock()
        if request.valid_until <= now:
            msg = "order has expired"
            raise ExpiredOrderError(msg)

        self._expire_resting_orders(now)

        if request.client_order_id is not None:
            key: _IdempotencyKey = (broker_id, request.client_order_id)
            fingerprint = self._make_fingerprint(broker_id, request)
            existing = self._idempotency.get(key)
            if existing is not None:
                stored_fp, order_id = existing
                if stored_fp != fingerprint:
                    msg = "client_order_id already used with different parameters"
                    raise IdempotencyConflictError(msg)
                return self._build_response(order_id)

        core_side = request.side.to_core_side()
        report = self._engine.submit_limit_order(
            symbol=request.symbol,
            broker_id=broker_id,
            side=core_side,
            price=request.price,
            quantity=request.quantity,
        )
        order = report.accepted_order
        self._metadata[order.order_id] = OrderMetadata(
            broker_id=broker_id,
            client_order_id=request.client_order_id,
            document_number=request.document_number,
            side=request.side,
            symbol=request.symbol,
            valid_until=request.valid_until,
            price=request.price,
            quantity=request.quantity,
        )
        for trade in report.trades:
            self._order_trades[trade.buyer_order_id].append(trade.trade_id)
            self._order_trades[trade.seller_order_id].append(trade.trade_id)

        if request.client_order_id is not None:
            key = (broker_id, request.client_order_id)
            fingerprint = self._make_fingerprint(broker_id, request)
            self._idempotency[key] = (fingerprint, order.order_id)

        return self._build_response(order.order_id)

    @staticmethod
    def _make_fingerprint(broker_id: str, request: SubmitOrderRequest) -> _Fingerprint:
        return (
            broker_id,
            request.client_order_id or "",
            request.document_number,
            request.side.value,
            request.valid_until.isoformat(),
            request.symbol,
            request.price,
            request.quantity,
        )

    def get_order(self, broker_id: str, order_id: str) -> OrderResponse:
        """Get the current status of an order."""
        meta = self._metadata.get(order_id)
        if meta is None or meta.broker_id != broker_id:
            msg = "order not found"
            raise OrderNotFoundError(msg)
        self._expire_resting_orders(self._clock())
        return self._build_response(order_id)

    def _expire_resting_orders(self, now: datetime) -> None:
        """Cancel resting orders whose valid_until has passed."""
        for order_id, meta in self._metadata.items():
            if order_id in self._expired_orders:
                continue
            if meta.valid_until > now:
                continue
            core_order = self._engine.book(meta.symbol).get_order(order_id)
            assert core_order is not None
            if not core_order.is_active:
                continue
            self._engine.cancel_order(meta.symbol, order_id)
            self._expired_orders.add(order_id)

    def _build_response(self, order_id: str) -> OrderResponse:
        meta = self._metadata[order_id]
        core_order = self._engine.book(meta.symbol).get_order(order_id)
        assert core_order is not None
        all_trades = self._engine.book(meta.symbol).trades
        order_trade_ids = set(self._order_trades.get(order_id, []))
        trades = tuple(
            TradeResponse(
                trade_id=t.trade_id,
                sequence=t.sequence,
                symbol=t.symbol,
                buyer_order_id=t.buyer_order_id,
                seller_order_id=t.seller_order_id,
                buyer_broker_id=t.buyer_broker_id,
                seller_broker_id=t.seller_broker_id,
                price=t.price,
                quantity=t.quantity,
            )
            for t in all_trades
            if t.trade_id in order_trade_ids
        )
        if order_id in self._expired_orders:
            status = ApiOrderStatus.EXPIRED
        else:
            status = _STATUS_MAP[core_order.status]
        return OrderResponse(
            order_id=order_id,
            broker_id=meta.broker_id,
            client_order_id=meta.client_order_id,
            document_number=meta.document_number,
            side=meta.side,
            symbol=meta.symbol,
            price=meta.price,
            quantity=meta.quantity,
            remaining_quantity=core_order.remaining,
            filled_quantity=core_order.filled_quantity,
            status=status,
            valid_until=meta.valid_until,
            trades=trades,
        )

    @staticmethod
    def _validate_broker_id(broker_id: str) -> None:
        if not broker_id or not broker_id.strip():
            msg = "broker_id must not be empty"
            raise OrderGatewayError(msg)
        if len(broker_id) > 64:
            msg = "broker_id must be at most 64 characters"
            raise OrderGatewayError(msg)
        if not _BROKER_ID_RE.match(broker_id):
            msg = "broker_id contains invalid characters"
            raise OrderGatewayError(msg)
