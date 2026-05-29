"""Tests for OrderGatewayService lazy valid_until expiration."""

from datetime import UTC, datetime, timedelta

import pytest

from mini_exchange.order_gateway.errors import ExpiredOrderError, OrderNotFoundError
from mini_exchange.order_gateway.models import (
    ExpireOrderCommand,
    GatewayCommandType,
    GatewayOrderStatus,
    GatewaySubmitOrder,
    SubmitOrderCommand,
)
from mini_exchange.order_gateway.service import OrderGatewayService
from mini_exchange.orderbook.models import Side

_NOW = datetime(2030, 6, 15, 12, 0, 0, tzinfo=UTC)


class _MutableClock:
    def __init__(self, at: datetime = _NOW) -> None:
        self.now = at

    def __call__(self) -> datetime:
        return self.now


def _service(clock: _MutableClock | None = None) -> OrderGatewayService:
    c = clock or _MutableClock()
    return OrderGatewayService(clock=c)


def _ask(
    valid_until: datetime = _NOW + timedelta(minutes=5),
    broker_id: str = "seller",
    price: int = 100,
    quantity: int = 10,
    **kwargs: object,
) -> GatewaySubmitOrder:
    defaults = {
        "broker_id": broker_id,
        "document_number": "DOC-S",
        "client_order_id": None,
        "side": Side.SELL,
        "valid_until": valid_until,
        "symbol": "AAPL",
        "price": price,
        "quantity": quantity,
    }
    defaults.update(kwargs)
    return GatewaySubmitOrder(**defaults)  # type: ignore[arg-type]


def _bid(
    valid_until: datetime = _NOW + timedelta(hours=1),
    broker_id: str = "buyer",
    price: int = 100,
    quantity: int = 10,
    **kwargs: object,
) -> GatewaySubmitOrder:
    defaults = {
        "broker_id": broker_id,
        "document_number": "DOC-B",
        "client_order_id": None,
        "side": Side.BUY,
        "valid_until": valid_until,
        "symbol": "AAPL",
        "price": price,
        "quantity": quantity,
    }
    defaults.update(kwargs)
    return GatewaySubmitOrder(**defaults)  # type: ignore[arg-type]


class TestExpiredAskNotMatched:
    def test_expired_ask_not_matched_by_later_bid(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        svc.submit_order(_ask(valid_until=_NOW + timedelta(minutes=5)))
        clock.now = _NOW + timedelta(minutes=10)
        result = svc.submit_order(_bid(price=100, quantity=10))
        assert result.status == GatewayOrderStatus.OPEN
        assert result.filled_quantity == 0
        assert result.trades == ()


class TestExpiredBidNotMatched:
    def test_expired_bid_not_matched_by_later_ask(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        svc.submit_order(_bid(valid_until=_NOW + timedelta(minutes=5)))
        clock.now = _NOW + timedelta(minutes=10)
        result = svc.submit_order(
            _ask(price=100, quantity=10, valid_until=_NOW + timedelta(hours=2))
        )
        assert result.status == GatewayOrderStatus.OPEN
        assert result.filled_quantity == 0
        assert result.trades == ()


class TestStatusChangesToExpired:
    def test_status_becomes_expired_after_clock_advances(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        submitted = svc.submit_order(_ask(valid_until=_NOW + timedelta(minutes=5)))
        assert submitted.status == GatewayOrderStatus.OPEN
        clock.now = _NOW + timedelta(minutes=10)
        result = svc.get_order("seller", submitted.order_id)
        assert result.status == GatewayOrderStatus.EXPIRED


class TestFilledRemainsFilledAfterExpiry:
    def test_filled_order_not_expired(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        ask = svc.submit_order(
            _ask(valid_until=_NOW + timedelta(minutes=5), quantity=10)
        )
        svc.submit_order(_bid(price=100, quantity=10))
        clock.now = _NOW + timedelta(minutes=10)
        result = svc.get_order("seller", ask.order_id)
        assert result.status == GatewayOrderStatus.FILLED


class TestPartiallyFilledExpires:
    def test_partially_filled_becomes_expired(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        ask = svc.submit_order(
            _ask(valid_until=_NOW + timedelta(minutes=5), quantity=10)
        )
        svc.submit_order(_bid(price=100, quantity=3))
        clock.now = _NOW + timedelta(minutes=10)
        result = svc.get_order("seller", ask.order_id)
        assert result.status == GatewayOrderStatus.EXPIRED
        assert result.filled_quantity == 3
        assert result.remaining_quantity == 7


class TestExpiredOrderRetrievable:
    def test_expired_order_retrievable_by_broker(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        submitted = svc.submit_order(_ask(valid_until=_NOW + timedelta(minutes=5)))
        clock.now = _NOW + timedelta(minutes=10)
        result = svc.get_order("seller", submitted.order_id)
        assert result.order_id == submitted.order_id
        assert result.status == GatewayOrderStatus.EXPIRED


class TestWrongBrokerStillNotFound:
    def test_wrong_broker_gets_not_found_even_if_expired(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        submitted = svc.submit_order(_ask(valid_until=_NOW + timedelta(minutes=5)))
        clock.now = _NOW + timedelta(minutes=10)
        with pytest.raises(OrderNotFoundError):
            svc.get_order("other-broker", submitted.order_id)


class TestNewOrderRejection:
    def test_valid_until_equal_to_now_rejected(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        with pytest.raises(ExpiredOrderError):
            svc.submit_order(_bid(valid_until=_NOW))

    def test_valid_until_before_now_rejected(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        with pytest.raises(ExpiredOrderError):
            svc.submit_order(_bid(valid_until=_NOW - timedelta(seconds=1)))


class TestExpirationCommandOrdering:
    def test_expiration_commands_before_submit(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        svc.submit_order(_ask(valid_until=_NOW + timedelta(minutes=5)))
        clock.now = _NOW + timedelta(minutes=10)
        svc.submit_order(
            _bid(price=100, quantity=10, valid_until=_NOW + timedelta(hours=2))
        )
        log = svc.command_log()
        assert isinstance(log[0], SubmitOrderCommand)
        assert isinstance(log[1], ExpireOrderCommand)
        assert isinstance(log[2], SubmitOrderCommand)
        assert log[1].command_type == GatewayCommandType.EXPIRE_ORDER


class TestMultipleExpirationsOrdered:
    def test_multiple_expirations_deterministic_order(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        svc.submit_order(
            _ask(
                valid_until=_NOW + timedelta(minutes=5),
                broker_id="s1",
                price=200,
            )
        )
        svc.submit_order(
            _bid(
                valid_until=_NOW + timedelta(minutes=5),
                broker_id="b1",
                price=50,
            )
        )
        clock.now = _NOW + timedelta(minutes=10)
        svc.submit_order(
            _ask(
                valid_until=_NOW + timedelta(hours=2),
                broker_id="s2",
                price=50,
            )
        )
        log = svc.command_log()
        expire_cmds = [c for c in log if isinstance(c, ExpireOrderCommand)]
        assert len(expire_cmds) == 2
        assert expire_cmds[0].order_id < expire_cmds[1].order_id


class TestGtcOrdersDoNotExpire:
    def test_gtc_order_not_expired_after_clock_advances(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        submitted = svc.submit_order(_ask(valid_until=None))
        clock.now = _NOW + timedelta(days=3650)
        result = svc.get_order("seller", submitted.order_id)
        assert result.status == GatewayOrderStatus.OPEN
        assert result.valid_until is None

    def test_gtc_order_can_be_matched_later(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        svc.submit_order(_ask(valid_until=None, price=100, quantity=10))
        clock.now = _NOW + timedelta(days=30)
        result = svc.submit_order(_bid(price=100, quantity=10, valid_until=None))
        assert result.status == GatewayOrderStatus.FILLED
        assert result.filled_quantity == 10
        assert len(result.trades) == 1

    def test_gtc_response_reports_null_valid_until(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        result = svc.submit_order(_ask(valid_until=None))
        assert result.valid_until is None


class TestExpiredOrdersNotInLaterTrades:
    def test_expired_order_not_in_later_trade_response(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        svc.submit_order(
            _ask(valid_until=_NOW + timedelta(minutes=5), price=100, quantity=5)
        )
        svc.submit_order(
            _ask(
                valid_until=_NOW + timedelta(hours=2),
                price=100,
                quantity=5,
                broker_id="s2",
            )
        )
        clock.now = _NOW + timedelta(minutes=10)
        result = svc.submit_order(_bid(price=100, quantity=5))
        assert len(result.trades) == 1
        assert result.trades[0].seller_broker_id == "s2"
