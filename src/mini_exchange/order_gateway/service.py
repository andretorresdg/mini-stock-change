"""Order Gateway service: synchronous single-writer submit flow."""

from __future__ import annotations

from threading import RLock

from mini_exchange.order_gateway.clock import Clock, utc_now
from mini_exchange.order_gateway.command_factory import OrderCommandFactory
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
from mini_exchange.orderbook.engine import MatchingEngine
from mini_exchange.orderbook.models import OrderStatus

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

            report = self._engine.submit_limit_order(
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

            core_order = report.accepted_order
            status = (
                metadata.status_override
                if metadata.status_override is not None
                else _CORE_STATUS_MAP[core_order.status]
            )

            trades = tuple(
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
                for t in report.trades
            )

            return GatewayOrder(
                order_id=cmd.order_id,
                broker_id=cmd.broker_id,
                document_number=cmd.document_number,
                client_order_id=cmd.client_order_id,
                side=cmd.side,
                symbol=cmd.symbol,
                price=cmd.price,
                quantity=cmd.quantity,
                remaining_quantity=core_order.remaining,
                filled_quantity=core_order.filled_quantity,
                status=status,
                valid_until=cmd.valid_until,
                trades=trades,
            )

    def command_log(self) -> tuple[SubmitOrderCommand | ExpireOrderCommand, ...]:
        """Return the full command log as an immutable tuple."""
        return tuple(self._command_log)
