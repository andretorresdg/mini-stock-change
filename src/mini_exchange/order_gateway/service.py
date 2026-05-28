"""Order Gateway service: synchronous single-writer submit flow."""

from __future__ import annotations

from threading import RLock

from mini_exchange.order_gateway.clock import Clock, utc_now
from mini_exchange.order_gateway.command_factory import OrderCommandFactory
from mini_exchange.order_gateway.errors import OrderNotFoundError
from mini_exchange.order_gateway.models import (
    ExpireOrderCommand,
    GatewayOrder,
    GatewayOrderStatus,
    GatewaySubmitOrder,
    GatewayTrade,
    OrderMetadata,
    SubmitOrderCommand,
)
from mini_exchange.order_gateway.sequencer import MonotonicSequencer
from mini_exchange.order_gateway.validation import validate_broker_id
from mini_exchange.orderbook.engine import MatchingEngine
from mini_exchange.orderbook.models import OrderStatus, Trade

_CORE_STATUS_MAP: dict[OrderStatus, GatewayOrderStatus] = {
    OrderStatus.OPEN: GatewayOrderStatus.OPEN,
    OrderStatus.PARTIALLY_FILLED: GatewayOrderStatus.PARTIALLY_FILLED,
    OrderStatus.FILLED: GatewayOrderStatus.FILLED,
    OrderStatus.CANCELED: GatewayOrderStatus.CANCELED,
}


class OrderGatewayService:
    """Synchronous order gateway with single-writer semantics.

    # MVP uses one in-process RLock as the single-writer boundary.
    # Production would use a durable FIFO command log or guarantee
    # one active engine writer per partition.
    """

    __slots__ = (
        "_command_factory",
        "_command_log",
        "_engine",
        "_lock",
        "_metadata_by_order_id",
    )

    def __init__(
        self,
        engine: MatchingEngine | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._engine = engine or MatchingEngine()
        effective_clock = clock or utc_now
        self._command_factory = OrderCommandFactory(
            command_sequencer=MonotonicSequencer(),
            order_id_sequencer=MonotonicSequencer(),
            clock=effective_clock,
        )
        self._lock = RLock()
        # MVP metadata is in memory.
        # Production should persist metadata transactionally alongside
        # the command log to survive restarts and enable queries.
        self._metadata_by_order_id: dict[str, OrderMetadata] = {}
        self._command_log: list[SubmitOrderCommand | ExpireOrderCommand] = []

    def submit_order(self, request: GatewaySubmitOrder) -> GatewayOrder:
        """Submit an order through the gateway into the matching engine."""
        with self._lock:
            cmd = self._command_factory.create_submit_order_command(request)
            self._command_log.append(cmd)

            self._engine.submit_limit_order(
                symbol=cmd.symbol,
                broker_id=cmd.broker_id,
                side=cmd.side,
                price=cmd.price,
                quantity=cmd.quantity,
                order_id=cmd.order_id,
            )

            metadata = OrderMetadata(
                order_id=cmd.order_id,
                broker_id=cmd.broker_id,
                document_number=cmd.document_number,
                client_order_id=cmd.client_order_id,
                side=cmd.side,
                valid_until=cmd.valid_until,
                symbol=cmd.symbol,
                price=cmd.price,
                quantity=cmd.quantity,
            )
            self._metadata_by_order_id[cmd.order_id] = metadata

            return self._build_order_response(metadata)

    def get_order(self, broker_id: str, order_id: str) -> GatewayOrder:
        """Retrieve the current state of an order for the given broker."""
        with self._lock:
            validate_broker_id(broker_id)
            metadata = self._metadata_by_order_id.get(order_id)
            # Wrong broker gets OrderNotFoundError intentionally
            # to avoid leaking whether another broker's order exists.
            if metadata is None or metadata.broker_id != broker_id:
                msg = "order not found"
                raise OrderNotFoundError(msg)
            return self._build_order_response(metadata)

    def command_log(self) -> tuple[SubmitOrderCommand | ExpireOrderCommand, ...]:
        """Return the full command log as an immutable tuple."""
        return tuple(self._command_log)

    def _build_order_response(self, metadata: OrderMetadata) -> GatewayOrder:
        core_order = self._engine.book(metadata.symbol).get_order(metadata.order_id)
        assert core_order is not None
        status = self._map_status(metadata, core_order.status)
        trades = self._trades_for_order(metadata.symbol, metadata.order_id)

        return GatewayOrder(
            order_id=metadata.order_id,
            broker_id=metadata.broker_id,
            document_number=metadata.document_number,
            client_order_id=metadata.client_order_id,
            side=metadata.side,
            symbol=metadata.symbol,
            price=metadata.price,
            quantity=metadata.quantity,
            remaining_quantity=core_order.remaining,
            filled_quantity=core_order.filled_quantity,
            status=status,
            valid_until=metadata.valid_until,
            trades=trades,
        )

    def _map_status(
        self, metadata: OrderMetadata, core_status: OrderStatus
    ) -> GatewayOrderStatus:
        if metadata.status_override is not None:
            return metadata.status_override
        return _CORE_STATUS_MAP[core_status]

    def _trades_for_order(self, symbol: str, order_id: str) -> tuple[GatewayTrade, ...]:
        book_trades: tuple[Trade, ...] = self._engine.book(symbol).trades
        return tuple(
            GatewayTrade(
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
            for t in book_trades
            if t.buyer_order_id == order_id or t.seller_order_id == order_id
        )
