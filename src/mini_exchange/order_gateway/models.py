"""Order Gateway command models and DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from mini_exchange.orderbook.models import Side


class GatewayOrderStatus(Enum):
    """Order status as seen from the gateway layer."""

    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class GatewayCommandType(Enum):
    """Types of commands processed by the gateway."""

    SUBMIT_ORDER = "SUBMIT_ORDER"
    EXPIRE_ORDER = "EXPIRE_ORDER"


def _validate_non_empty(value: str, name: str) -> None:
    if not value or not value.strip():
        msg = f"{name} must not be empty or whitespace"
        raise ValueError(msg)


def _validate_positive_int(value: object, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        msg = f"{name} must be a positive integer"
        raise TypeError(msg)
    if value <= 0:
        msg = f"{name} must be a positive integer"
        raise ValueError(msg)


def _validate_tz_aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        msg = f"{name} must be timezone-aware"
        raise ValueError(msg)
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class GatewaySubmitOrder:
    """Input DTO for submitting an order through the gateway."""

    broker_id: str
    document_number: str
    client_order_id: str | None
    side: Side
    valid_until: datetime
    symbol: str
    price: int
    quantity: int

    def __post_init__(self) -> None:
        _validate_non_empty(self.broker_id, "broker_id")
        _validate_non_empty(self.document_number, "document_number")
        _validate_non_empty(self.symbol, "symbol")
        if not isinstance(self.side, Side):
            msg = "side must be a valid Side"
            raise TypeError(msg)
        object.__setattr__(
            self, "valid_until", _validate_tz_aware(self.valid_until, "valid_until")
        )
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        _validate_positive_int(self.price, "price")
        _validate_positive_int(self.quantity, "quantity")


@dataclass(frozen=True, slots=True)
class SubmitOrderCommand:
    """Enriched submit order command with sequence and generated ID."""

    command_sequence: int
    received_at: datetime
    command_type: GatewayCommandType
    broker_id: str
    document_number: str
    client_order_id: str | None
    order_id: str
    side: Side
    valid_until: datetime
    symbol: str
    price: int
    quantity: int

    def __post_init__(self) -> None:
        _validate_positive_int(self.command_sequence, "command_sequence")
        object.__setattr__(
            self, "received_at", _validate_tz_aware(self.received_at, "received_at")
        )
        if self.command_type != GatewayCommandType.SUBMIT_ORDER:
            msg = "command_type must be SUBMIT_ORDER"
            raise ValueError(msg)
        _validate_non_empty(self.broker_id, "broker_id")
        _validate_non_empty(self.document_number, "document_number")
        _validate_non_empty(self.order_id, "order_id")
        if not isinstance(self.side, Side):
            msg = "side must be a valid Side"
            raise TypeError(msg)
        object.__setattr__(
            self, "valid_until", _validate_tz_aware(self.valid_until, "valid_until")
        )
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        _validate_non_empty(self.symbol, "symbol")
        _validate_positive_int(self.price, "price")
        _validate_positive_int(self.quantity, "quantity")


@dataclass(frozen=True, slots=True)
class ExpireOrderCommand:
    """Command to expire a resting order."""

    command_sequence: int
    received_at: datetime
    command_type: GatewayCommandType
    order_id: str
    symbol: str
    reason: str

    def __post_init__(self) -> None:
        _validate_positive_int(self.command_sequence, "command_sequence")
        object.__setattr__(
            self, "received_at", _validate_tz_aware(self.received_at, "received_at")
        )
        if self.command_type != GatewayCommandType.EXPIRE_ORDER:
            msg = "command_type must be EXPIRE_ORDER"
            raise ValueError(msg)
        _validate_non_empty(self.order_id, "order_id")
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        _validate_non_empty(self.symbol, "symbol")
        _validate_non_empty(self.reason, "reason")


@dataclass(slots=True)
class OrderMetadata:
    """Broker/API-level metadata tracked by the gateway.

    # Matching quantities (remaining, filled) stay in the matching core.
    # Gateway metadata stores only broker and API concerns such as
    # document_number, client_order_id, valid_until, and status_override.
    """

    order_id: str
    broker_id: str
    document_number: str
    client_order_id: str | None
    side: Side
    valid_until: datetime
    symbol: str
    price: int
    quantity: int
    status_override: GatewayOrderStatus | None = None

    def __post_init__(self) -> None:
        _validate_non_empty(self.order_id, "order_id")
        _validate_non_empty(self.broker_id, "broker_id")
        _validate_non_empty(self.document_number, "document_number")
        _validate_non_empty(self.symbol, "symbol")
        if not isinstance(self.side, Side):
            msg = "side must be a valid Side"
            raise TypeError(msg)
        self.valid_until = _validate_tz_aware(self.valid_until, "valid_until")
        self.symbol = self.symbol.strip().upper()
        _validate_positive_int(self.price, "price")
        _validate_positive_int(self.quantity, "quantity")


@dataclass(frozen=True, slots=True)
class GatewayTrade:
    """Output DTO representing a single trade."""

    trade_id: str
    sequence: int
    symbol: str
    buyer_order_id: str
    seller_order_id: str
    buyer_broker_id: str
    seller_broker_id: str
    price: int
    quantity: int

    def __post_init__(self) -> None:
        _validate_non_empty(self.trade_id, "trade_id")
        _validate_positive_int(self.sequence, "sequence")
        _validate_non_empty(self.symbol, "symbol")
        _validate_non_empty(self.buyer_order_id, "buyer_order_id")
        _validate_non_empty(self.seller_order_id, "seller_order_id")
        _validate_non_empty(self.buyer_broker_id, "buyer_broker_id")
        _validate_non_empty(self.seller_broker_id, "seller_broker_id")
        _validate_positive_int(self.price, "price")
        _validate_positive_int(self.quantity, "quantity")


@dataclass(frozen=True, slots=True)
class GatewayOrder:
    """Output DTO representing an order with its current state."""

    order_id: str
    broker_id: str
    document_number: str
    client_order_id: str | None
    side: Side
    symbol: str
    price: int
    quantity: int
    remaining_quantity: int
    filled_quantity: int
    status: GatewayOrderStatus
    valid_until: datetime
    trades: tuple[GatewayTrade, ...]

    def __post_init__(self) -> None:
        _validate_non_empty(self.order_id, "order_id")
        _validate_non_empty(self.broker_id, "broker_id")
        _validate_non_empty(self.document_number, "document_number")
        _validate_non_empty(self.symbol, "symbol")
        _validate_positive_int(self.price, "price")
        _validate_positive_int(self.quantity, "quantity")
        if not isinstance(self.remaining_quantity, int) or self.remaining_quantity < 0:
            msg = "remaining_quantity must be zero or positive"
            raise ValueError(msg)
        if not isinstance(self.filled_quantity, int) or self.filled_quantity < 0:
            msg = "filled_quantity must be zero or positive"
            raise ValueError(msg)
        if self.remaining_quantity + self.filled_quantity > self.quantity:
            msg = "remaining_quantity + filled_quantity must not exceed quantity"
            raise ValueError(msg)
        object.__setattr__(
            self, "valid_until", _validate_tz_aware(self.valid_until, "valid_until")
        )


@dataclass(frozen=True, slots=True)
class GatewayBookLevel:
    """An aggregated price level in the order book."""

    price: int
    quantity: int

    def __post_init__(self) -> None:
        _validate_positive_int(self.price, "price")
        _validate_positive_int(self.quantity, "quantity")


@dataclass(frozen=True, slots=True)
class GatewayBookSnapshot:
    """A snapshot of the current order book state for one symbol."""

    symbol: str
    bids: tuple[GatewayBookLevel, ...]
    asks: tuple[GatewayBookLevel, ...]

    def __post_init__(self) -> None:
        _validate_non_empty(self.symbol, "symbol")
