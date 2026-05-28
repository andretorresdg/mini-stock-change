"""Tests for OrderGatewayService submit flow."""

from datetime import UTC, datetime, timedelta

import pytest

from mini_exchange.order_gateway.errors import ExpiredOrderError, InvalidBrokerError
from mini_exchange.order_gateway.models import (
    GatewayCommandType,
    GatewayOrderStatus,
    GatewaySubmitOrder,
    SubmitOrderCommand,
)
from mini_exchange.order_gateway.service import OrderGatewayService
from mini_exchange.orderbook.models import Side

_NOW = datetime(2030, 6, 15, 12, 0, 0, tzinfo=UTC)
_FUTURE = _NOW + timedelta(hours=1)


def _clock() -> datetime:
    return _NOW


def _service() -> OrderGatewayService:
    return OrderGatewayService(clock=_clock)


def _ask(
    symbol: str = "AAPL",
    price: int = 100,
    quantity: int = 10,
    broker_id: str = "seller",
    **kwargs: object,
) -> GatewaySubmitOrder:
    defaults = {
        "broker_id": broker_id,
        "document_number": "DOC-S",
        "client_order_id": None,
        "side": Side.SELL,
        "valid_until": _FUTURE,
        "symbol": symbol,
        "price": price,
        "quantity": quantity,
    }
    defaults.update(kwargs)
    return GatewaySubmitOrder(**defaults)  # type: ignore[arg-type]


def _bid(
    symbol: str = "AAPL",
    price: int = 100,
    quantity: int = 10,
    broker_id: str = "buyer",
    **kwargs: object,
) -> GatewaySubmitOrder:
    defaults = {
        "broker_id": broker_id,
        "document_number": "DOC-B",
        "client_order_id": None,
        "side": Side.BUY,
        "valid_until": _FUTURE,
        "symbol": symbol,
        "price": price,
        "quantity": quantity,
    }
    defaults.update(kwargs)
    return GatewaySubmitOrder(**defaults)  # type: ignore[arg-type]


class TestSubmitAsk:
    def test_ask_rests_open(self) -> None:
        svc = _service()
        result = svc.submit_order(_ask())
        assert result.status == GatewayOrderStatus.OPEN
        assert result.side == Side.SELL
        assert result.remaining_quantity == 10
        assert result.filled_quantity == 0
        assert result.trades == ()


class TestSubmitBid:
    def test_bid_rests_open(self) -> None:
        svc = _service()
        result = svc.submit_order(_bid())
        assert result.status == GatewayOrderStatus.OPEN
        assert result.side == Side.BUY
        assert result.remaining_quantity == 10
        assert result.filled_quantity == 0


class TestDeterministicIds:
    def test_order_id_assignment(self) -> None:
        svc = _service()
        r1 = svc.submit_order(_ask())
        r2 = svc.submit_order(_bid())
        assert r1.order_id == "AAPL-O-1"
        assert r2.order_id == "AAPL-O-2"

    def test_command_sequence_assignment(self) -> None:
        svc = _service()
        svc.submit_order(_ask())
        svc.submit_order(_bid())
        log = svc.command_log()
        assert log[0].command_sequence == 1
        assert log[1].command_sequence == 2


class TestCommandLog:
    def test_stores_commands_in_order(self) -> None:
        svc = _service()
        svc.submit_order(_ask(symbol="AAPL"))
        svc.submit_order(_bid(symbol="MSFT"))
        log = svc.command_log()
        assert len(log) == 2
        assert all(isinstance(c, SubmitOrderCommand) for c in log)
        assert log[0].symbol == "AAPL"
        assert log[1].symbol == "MSFT"
        assert log[0].command_type == GatewayCommandType.SUBMIT_ORDER


class TestMatching:
    def test_same_price_full_match(self) -> None:
        svc = _service()
        svc.submit_order(_ask(price=100, quantity=10))
        result = svc.submit_order(_bid(price=100, quantity=10))
        assert result.status == GatewayOrderStatus.FILLED
        assert result.filled_quantity == 10
        assert result.remaining_quantity == 0
        assert len(result.trades) == 1
        assert result.trades[0].price == 100
        assert result.trades[0].quantity == 10

    def test_price_gap_executes_at_seller_price(self) -> None:
        svc = _service()
        svc.submit_order(_ask(price=90, quantity=10))
        result = svc.submit_order(_bid(price=100, quantity=10))
        assert result.status == GatewayOrderStatus.FILLED
        assert result.trades[0].price == 90

    def test_partial_fill(self) -> None:
        svc = _service()
        svc.submit_order(_ask(price=100, quantity=5))
        result = svc.submit_order(_bid(price=100, quantity=10))
        assert result.status == GatewayOrderStatus.PARTIALLY_FILLED
        assert result.filled_quantity == 5
        assert result.remaining_quantity == 5
        assert len(result.trades) == 1

    def test_multiple_fills_from_one_order(self) -> None:
        svc = _service()
        svc.submit_order(_ask(price=100, quantity=3, broker_id="s1"))
        svc.submit_order(_ask(price=100, quantity=4, broker_id="s2"))
        result = svc.submit_order(_bid(price=100, quantity=7))
        assert result.status == GatewayOrderStatus.FILLED
        assert result.filled_quantity == 7
        assert len(result.trades) == 2
        assert result.trades[0].quantity == 3
        assert result.trades[1].quantity == 4


class TestStatusMapping:
    def test_open_status(self) -> None:
        svc = _service()
        result = svc.submit_order(_bid())
        assert result.status == GatewayOrderStatus.OPEN

    def test_partially_filled_status(self) -> None:
        svc = _service()
        svc.submit_order(_ask(price=100, quantity=3))
        result = svc.submit_order(_bid(price=100, quantity=10))
        assert result.status == GatewayOrderStatus.PARTIALLY_FILLED

    def test_filled_status(self) -> None:
        svc = _service()
        svc.submit_order(_ask(price=100, quantity=10))
        result = svc.submit_order(_bid(price=100, quantity=10))
        assert result.status == GatewayOrderStatus.FILLED


class TestTradesOnlyForSubmittedOrder:
    def test_response_includes_only_submitted_order_trades(self) -> None:
        svc = _service()
        svc.submit_order(_ask(price=100, quantity=5, broker_id="s1"))
        svc.submit_order(_ask(price=100, quantity=5, broker_id="s2"))
        result = svc.submit_order(_bid(price=100, quantity=5))
        assert len(result.trades) == 1
        assert result.trades[0].buyer_order_id == result.order_id


class TestErrorBubbling:
    def test_invalid_broker_raises(self) -> None:
        svc = _service()
        with pytest.raises(InvalidBrokerError):
            svc.submit_order(_bid(broker_id="bad broker!"))

    def test_expired_order_raises(self) -> None:
        svc = _service()
        req = _bid(valid_until=_NOW - timedelta(seconds=1))
        with pytest.raises(ExpiredOrderError, match="expired"):
            svc.submit_order(req)
