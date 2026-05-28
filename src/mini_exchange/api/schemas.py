"""API request and response schemas."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mini_exchange.orderbook.models import Side

_DOCUMENT_RE = re.compile(r"^[A-Za-z0-9.\-/]+$")
_SYMBOL_RE = re.compile(r"^[A-Z0-9._\-]+$")


class ApiOrderSide(StrEnum):
    """External API representation of order side."""

    BID = "BID"
    ASK = "ASK"

    def to_core_side(self) -> Side:
        """Convert to internal Side enum."""
        if self == ApiOrderSide.BID:
            return Side.BUY
        return Side.SELL

    @classmethod
    def from_core_side(cls, core_side: Side) -> ApiOrderSide:
        """Convert from internal Side enum."""
        if core_side == Side.BUY:
            return cls.BID
        return cls.ASK


class ApiOrderStatus(StrEnum):
    """External API representation of order status."""

    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class SubmitOrderRequest(BaseModel):
    """Request body for submitting a new order."""

    model_config = ConfigDict(extra="forbid")

    client_order_id: str | None = None
    document_number: Annotated[str, Field(min_length=3, max_length=32)]
    side: ApiOrderSide
    valid_until: datetime
    symbol: Annotated[str, Field(max_length=16)]
    price: Annotated[int, Field(strict=True, gt=0)]
    quantity: Annotated[int, Field(strict=True, gt=0)]

    @field_validator("client_order_id")
    @classmethod
    def _validate_client_order_id(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            msg = "client_order_id must not be empty or whitespace"
            raise ValueError(msg)
        if len(stripped) > 128:
            msg = "client_order_id must be at most 128 characters"
            raise ValueError(msg)
        return stripped

    @field_validator("document_number")
    @classmethod
    def _validate_document_number(cls, v: str) -> str:
        if not v.strip():
            msg = "document_number must not be empty or whitespace"
            raise ValueError(msg)
        if not _DOCUMENT_RE.match(v):
            msg = "document_number contains invalid characters"
            raise ValueError(msg)
        return v

    @field_validator("symbol")
    @classmethod
    def _validate_symbol(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            msg = "symbol must not be empty or whitespace"
            raise ValueError(msg)
        if not _SYMBOL_RE.match(v):
            msg = "symbol contains invalid characters"
            raise ValueError(msg)
        return v

    @field_validator("valid_until")
    @classmethod
    def _validate_valid_until(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            msg = "valid_until must be timezone-aware"
            raise ValueError(msg)
        return v.astimezone(UTC)


class TradeResponse(BaseModel):
    """Response schema for a single trade."""

    model_config = ConfigDict(extra="forbid")

    trade_id: str
    sequence: int
    symbol: str
    buyer_order_id: str
    seller_order_id: str
    buyer_broker_id: str
    seller_broker_id: str
    price: int
    quantity: int


class OrderResponse(BaseModel):
    """Response schema for an order with its trades."""

    model_config = ConfigDict(extra="forbid")

    order_id: str
    broker_id: str
    client_order_id: str | None
    document_number: str
    side: ApiOrderSide
    symbol: str
    price: int
    quantity: int
    remaining_quantity: int
    filled_quantity: int
    status: ApiOrderStatus
    valid_until: datetime
    trades: tuple[TradeResponse, ...]


class MarketTradeResponse(BaseModel):
    """Response schema for a single public market trade."""

    model_config = ConfigDict(extra="forbid")

    trade_id: str
    sequence: int
    symbol: str
    price: int
    quantity: int


class MarketTradesResponse(BaseModel):
    """Response schema for the market trades list."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    trades: tuple[MarketTradeResponse, ...]


class BookLevelResponse(BaseModel):
    """Response schema for a single order book price level."""

    model_config = ConfigDict(extra="forbid")

    price: int
    quantity: int


class BookSnapshotResponse(BaseModel):
    """Response schema for an order book snapshot."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    bids: tuple[BookLevelResponse, ...]
    asks: tuple[BookLevelResponse, ...]


class ErrorResponse(BaseModel):
    """Response schema for errors."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
