"""Order Gateway: bridge between API layer and matching core."""

from mini_exchange.order_gateway.clock import Clock, utc_now
from mini_exchange.order_gateway.command_factory import OrderCommandFactory
from mini_exchange.order_gateway.errors import (
    ExpiredOrderError,
    GatewayStateError,
    IdempotencyConflictError,
    InvalidBrokerError,
    OrderGatewayError,
    OrderNotFoundError,
)
from mini_exchange.order_gateway.models import (
    ExpireOrderCommand,
    GatewayCommandType,
    GatewayOrder,
    GatewayOrderStatus,
    GatewaySubmitOrder,
    GatewayTrade,
    OrderMetadata,
    SubmitOrderCommand,
)
from mini_exchange.order_gateway.sequencer import MonotonicSequencer
from mini_exchange.order_gateway.service import OrderGatewayService
from mini_exchange.order_gateway.validation import (
    build_submit_fingerprint,
    make_order_id,
    validate_broker_id,
)

__all__ = [
    "Clock",
    "ExpireOrderCommand",
    "ExpiredOrderError",
    "GatewayCommandType",
    "GatewayOrder",
    "GatewayOrderStatus",
    "GatewayStateError",
    "GatewaySubmitOrder",
    "GatewayTrade",
    "IdempotencyConflictError",
    "InvalidBrokerError",
    "MonotonicSequencer",
    "OrderCommandFactory",
    "OrderGatewayError",
    "OrderGatewayService",
    "OrderMetadata",
    "OrderNotFoundError",
    "SubmitOrderCommand",
    "build_submit_fingerprint",
    "make_order_id",
    "utc_now",
    "validate_broker_id",
]
