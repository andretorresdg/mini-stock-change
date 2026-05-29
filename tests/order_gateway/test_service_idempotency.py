"""Tests for OrderGatewayService idempotency (broker-scoped client_order_id)."""

from datetime import UTC, datetime, timedelta

import pytest

from mini_exchange.order_gateway.errors import IdempotencyConflictError
from mini_exchange.order_gateway.models import GatewaySubmitOrder, SubmitOrderCommand
from mini_exchange.order_gateway.service import OrderGatewayService
from mini_exchange.orderbook.models import Side

_NOW = datetime(2030, 6, 15, 12, 0, 0, tzinfo=UTC)
_FUTURE = _NOW + timedelta(hours=1)


class _MutableClock:
    def __init__(self, at: datetime = _NOW) -> None:
        self.now = at

    def __call__(self) -> datetime:
        return self.now


def _service(clock: _MutableClock | None = None) -> OrderGatewayService:
    c = clock or _MutableClock()
    return OrderGatewayService(clock=c)


def _request(
    client_order_id: str | None = "c1",
    broker_id: str = "broker1",
    price: int = 100,
    quantity: int = 10,
    symbol: str = "AAPL",
    **kwargs: object,
) -> GatewaySubmitOrder:
    defaults = {
        "broker_id": broker_id,
        "document_number": f"DOC-{broker_id}",
        "client_order_id": client_order_id,
        "side": Side.BUY,
        "valid_until": _FUTURE,
        "symbol": symbol,
        "price": price,
        "quantity": quantity,
    }
    defaults.update(kwargs)
    return GatewaySubmitOrder(**defaults)  # type: ignore[arg-type]


class TestIdempotentRetry:
    def test_same_request_returns_same_order_id(self) -> None:
        svc = _service()
        r1 = svc.submit_order(_request())
        r2 = svc.submit_order(_request())
        assert r1.order_id == r2.order_id

    def test_gtc_retry_returns_same_order_id(self) -> None:
        svc = _service()
        r1 = svc.submit_order(_request(valid_until=None))
        r2 = svc.submit_order(_request(valid_until=None))
        assert r1.order_id == r2.order_id
        assert len(svc.command_log()) == 1

    def test_gtc_then_expiring_same_client_id_conflicts(self) -> None:
        svc = _service()
        svc.submit_order(_request(valid_until=None))
        with pytest.raises(IdempotencyConflictError):
            svc.submit_order(_request(valid_until=_FUTURE))

    def test_retry_does_not_append_command(self) -> None:
        svc = _service()
        svc.submit_order(_request())
        svc.submit_order(_request())
        assert len(svc.command_log()) == 1

    def test_retry_does_not_create_extra_trades(self) -> None:
        svc = _service()
        ask = _request(
            client_order_id="ask1",
            broker_id="seller",
            side=Side.SELL,
            price=100,
            quantity=10,
        )
        svc.submit_order(ask)
        bid = _request(
            client_order_id="bid1",
            broker_id="buyer",
            price=100,
            quantity=10,
        )
        r1 = svc.submit_order(bid)
        r2 = svc.submit_order(bid)
        assert len(r1.trades) == 1
        assert len(r2.trades) == 1
        assert r1.trades[0].trade_id == r2.trades[0].trade_id


class TestIdempotencyConflict:
    def test_different_price_raises(self) -> None:
        svc = _service()
        svc.submit_order(_request(price=100))
        with pytest.raises(IdempotencyConflictError):
            svc.submit_order(_request(price=200))

    def test_different_quantity_raises(self) -> None:
        svc = _service()
        svc.submit_order(_request(quantity=10))
        with pytest.raises(IdempotencyConflictError):
            svc.submit_order(_request(quantity=20))

    def test_different_symbol_raises(self) -> None:
        svc = _service()
        svc.submit_order(_request(symbol="AAPL"))
        with pytest.raises(IdempotencyConflictError):
            svc.submit_order(_request(symbol="MSFT"))


class TestBrokerIsolation:
    def test_different_broker_same_client_order_id_independent(self) -> None:
        svc = _service()
        r1 = svc.submit_order(_request(broker_id="broker1"))
        r2 = svc.submit_order(_request(broker_id="broker2"))
        assert r1.order_id != r2.order_id


class TestNoClientOrderId:
    def test_submissions_without_client_order_id_not_idempotent(self) -> None:
        svc = _service()
        r1 = svc.submit_order(_request(client_order_id=None))
        r2 = svc.submit_order(_request(client_order_id=None))
        assert r1.order_id != r2.order_id
        assert len(svc.command_log()) == 2


class TestRetryAfterExpiry:
    def test_exact_retry_after_valid_until_returns_existing(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock=clock)
        valid_until = _NOW + timedelta(minutes=5)
        req = _request(valid_until=valid_until)
        r1 = svc.submit_order(req)

        clock.now = valid_until + timedelta(seconds=1)
        r2 = svc.submit_order(req)
        assert r1.order_id == r2.order_id
        submit_cmds = [
            c for c in svc.command_log() if isinstance(c, SubmitOrderCommand)
        ]
        assert len(submit_cmds) == 1
