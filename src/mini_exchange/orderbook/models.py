"""Domain models for the mini exchange order book."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Side(Enum):
    """Order side."""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Lifecycle status of an order."""

    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"


@dataclass(slots=True)
class Order:
    """A mutable limit order."""

    order_id: str
    broker_id: str
    document_number: str
    symbol: str
    side: Side
    price: int
    quantity: int
    sequence: int
    remaining: int = field(init=False)
    status: OrderStatus = field(default=OrderStatus.OPEN)

    def __post_init__(self) -> None:
        if not self.order_id:
            msg = "order_id must be non-empty"
            raise ValueError(msg)
        if not self.broker_id:
            msg = "broker_id must be non-empty"
            raise ValueError(msg)
        if not self.document_number:
            msg = "document_number must be non-empty"
            raise ValueError(msg)
        if not self.symbol:
            msg = "symbol must be non-empty"
            raise ValueError(msg)
        if not isinstance(self.side, Side):
            msg = "side must be a valid Side"
            raise TypeError(msg)
        if not isinstance(self.price, int) or self.price <= 0:
            msg = "price must be a positive integer"
            raise ValueError(msg)
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            msg = "quantity must be a positive integer"
            raise ValueError(msg)
        if not isinstance(self.sequence, int) or self.sequence <= 0:
            msg = "sequence must be a positive integer"
            raise ValueError(msg)
        self.remaining = self.quantity

    @property
    def filled_quantity(self) -> int:
        """Quantity that has been filled so far."""
        return self.quantity - self.remaining

    @property
    def is_active(self) -> bool:
        """Whether the order can still receive fills."""
        return self.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)

    def apply_fill(self, quantity: int) -> None:
        """Apply a fill to this order."""
        if not isinstance(quantity, int) or quantity <= 0:
            msg = "fill quantity must be a positive integer"
            raise ValueError(msg)
        if not self.is_active:
            msg = "cannot fill an inactive order"
            raise ValueError(msg)
        if quantity > self.remaining:
            msg = "fill quantity exceeds remaining quantity"
            raise ValueError(msg)
        self.remaining -= quantity
        if self.remaining == 0:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED

    def cancel(self) -> bool:
        """Cancel this order. Returns True if successfully canceled."""
        if not self.is_active:
            return False
        self.status = OrderStatus.CANCELED
        return True


@dataclass(frozen=True, slots=True)
class Trade:
    """An immutable record of a matched trade."""

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
        if not self.trade_id:
            msg = "trade_id must be non-empty"
            raise ValueError(msg)
        if not isinstance(self.sequence, int) or self.sequence <= 0:
            msg = "sequence must be a positive integer"
            raise ValueError(msg)
        if not self.symbol:
            msg = "symbol must be non-empty"
            raise ValueError(msg)
        if not self.buyer_order_id:
            msg = "buyer_order_id must be non-empty"
            raise ValueError(msg)
        if not self.seller_order_id:
            msg = "seller_order_id must be non-empty"
            raise ValueError(msg)
        if not self.buyer_broker_id:
            msg = "buyer_broker_id must be non-empty"
            raise ValueError(msg)
        if not self.seller_broker_id:
            msg = "seller_broker_id must be non-empty"
            raise ValueError(msg)
        if not isinstance(self.price, int) or self.price <= 0:
            msg = "price must be a positive integer"
            raise ValueError(msg)
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            msg = "quantity must be a positive integer"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    """Result of submitting an order to the exchange."""

    accepted_order: Order
    trades: tuple[Trade, ...]
