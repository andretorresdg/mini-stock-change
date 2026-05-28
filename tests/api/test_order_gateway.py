"""Tests for the OrderGatewayService."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from mini_exchange.api.schemas import ApiOrderSide, ApiOrderStatus, SubmitOrderRequest
from mini_exchange.api.services.order_gateway import (
    ExpiredOrderError,
    IdempotencyConflictError,
    OrderGatewayError,
    OrderGatewayService,
    OrderNotFoundError,
)


def _fake_clock(
    dt: datetime | None = None,
) -> Callable[[], datetime]:
    """Return a deterministic clock callable."""
    fixed = dt or datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)

    def clock() -> datetime:
        return fixed

    return clock


def _make_request(**kwargs: object) -> SubmitOrderRequest:
    defaults: dict[str, object] = {
        "document_number": "DOC-1",
        "side": "BID",
        "valid_until": "2030-01-01T00:00:00Z",
        "symbol": "AAPL",
        "price": 100,
        "quantity": 10,
    }
    defaults.update(kwargs)
    return SubmitOrderRequest.model_validate(defaults)


class TestSubmitBid:
    def test_submit_bid_order(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        req = _make_request(side="BID")
        resp = svc.submit_order("broker1", req)
        assert resp.order_id == "AAPL-1"
        assert resp.broker_id == "broker1"
        assert resp.side == ApiOrderSide.BID
        assert resp.status == ApiOrderStatus.OPEN
        assert resp.remaining_quantity == 10
        assert resp.filled_quantity == 0
        assert resp.trades == ()


class TestSubmitAsk:
    def test_submit_ask_order(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        req = _make_request(side="ASK")
        resp = svc.submit_order("broker1", req)
        assert resp.side == ApiOrderSide.ASK
        assert resp.status == ApiOrderStatus.OPEN


class TestPriceGapMatch:
    def test_execution_price_is_seller_price(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        sell_req = _make_request(side="ASK", price=95)
        svc.submit_order("seller", sell_req)
        buy_req = _make_request(side="BID", price=100)
        resp = svc.submit_order("buyer", buy_req)
        assert len(resp.trades) == 1
        assert resp.trades[0].price == 95
        assert resp.status == ApiOrderStatus.FILLED


class TestPartialFill:
    def test_partial_fill_response(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        sell_req = _make_request(side="ASK", price=100, quantity=20)
        svc.submit_order("seller", sell_req)
        buy_req = _make_request(side="BID", price=100, quantity=5)
        resp = svc.submit_order("buyer", buy_req)
        assert resp.status == ApiOrderStatus.FILLED
        assert resp.filled_quantity == 5
        seller_resp = svc.get_order("seller", "AAPL-1")
        assert seller_resp.status == ApiOrderStatus.PARTIALLY_FILLED
        assert seller_resp.remaining_quantity == 15


class TestGetOrder:
    def test_get_order_after_submission(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        req = _make_request()
        svc.submit_order("broker1", req)
        resp = svc.get_order("broker1", "AAPL-1")
        assert resp.order_id == "AAPL-1"
        assert resp.status == ApiOrderStatus.OPEN

    def test_get_order_after_full_match(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        svc.submit_order("seller", _make_request(side="ASK", price=100))
        svc.submit_order("buyer", _make_request(side="BID", price=100))
        resp = svc.get_order("seller", "AAPL-1")
        assert resp.status == ApiOrderStatus.FILLED

    def test_get_order_includes_trades(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        svc.submit_order("seller", _make_request(side="ASK", price=100))
        svc.submit_order("buyer", _make_request(side="BID", price=100))
        resp = svc.get_order("buyer", "AAPL-2")
        assert len(resp.trades) == 1
        assert resp.trades[0].buyer_order_id == "AAPL-2"


class TestBrokerIsolation:
    def test_wrong_broker_raises_not_found(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        svc.submit_order("broker1", _make_request())
        with pytest.raises(OrderNotFoundError, match="order not found"):
            svc.get_order("broker2", "AAPL-1")


class TestOrderNotFound:
    def test_unknown_order_raises(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        with pytest.raises(OrderNotFoundError, match="order not found"):
            svc.get_order("broker1", "missing")


class TestInvalidBrokerId:
    @pytest.mark.parametrize(
        "broker_id",
        ["", "   ", "a" * 65, "bad broker!", "broker@id"],
    )
    def test_invalid_broker_rejected(self, broker_id: str) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        req = _make_request()
        with pytest.raises(OrderGatewayError):
            svc.submit_order(broker_id, req)


class TestExpiredOrder:
    def test_expired_order_rejected(self) -> None:
        past = datetime(2020, 1, 1, tzinfo=UTC)
        svc = OrderGatewayService(clock=_fake_clock())
        req = _make_request(valid_until=past.isoformat())
        with pytest.raises(ExpiredOrderError, match="expired"):
            svc.submit_order("broker1", req)

    def test_exactly_at_clock_rejected(self) -> None:
        now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
        svc = OrderGatewayService(clock=_fake_clock(now))
        req = _make_request(valid_until=now.isoformat())
        with pytest.raises(ExpiredOrderError, match="expired"):
            svc.submit_order("broker1", req)


class TestDeterministicClock:
    def test_fake_clock_used(self) -> None:
        fixed = datetime(2099, 12, 31, tzinfo=UTC)
        svc = OrderGatewayService(clock=_fake_clock(fixed))
        future = (fixed + timedelta(days=1)).isoformat()
        req = _make_request(valid_until=future)
        resp = svc.submit_order("broker1", req)
        assert resp.order_id == "AAPL-1"


class TestDefaultService:
    def test_default_constructor(self) -> None:
        svc = OrderGatewayService()
        future = (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat()
        req = _make_request(valid_until=future)
        resp = svc.submit_order("broker1", req)
        assert resp.order_id == "AAPL-1"


class TestIdempotencyRetry:
    def test_same_client_order_id_returns_same_order(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        req = _make_request(client_order_id="abc-123")
        resp1 = svc.submit_order("broker1", req)
        resp2 = svc.submit_order("broker1", req)
        assert resp1.order_id == resp2.order_id

    def test_retry_does_not_create_additional_trades(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        sell = _make_request(side="ASK", price=100, client_order_id="s1")
        svc.submit_order("seller", sell)
        buy = _make_request(side="BID", price=100, client_order_id="b1")
        resp1 = svc.submit_order("buyer", buy)
        resp2 = svc.submit_order("buyer", buy)
        assert len(resp1.trades) == 1
        assert len(resp2.trades) == 1
        assert resp1.trades[0].trade_id == resp2.trades[0].trade_id


class TestIdempotencyConflict:
    def test_different_price_returns_conflict(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        req1 = _make_request(client_order_id="dup", price=100)
        svc.submit_order("broker1", req1)
        req2 = _make_request(client_order_id="dup", price=200)
        with pytest.raises(IdempotencyConflictError):
            svc.submit_order("broker1", req2)

    def test_different_quantity_returns_conflict(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        req1 = _make_request(client_order_id="dup", quantity=10)
        svc.submit_order("broker1", req1)
        req2 = _make_request(client_order_id="dup", quantity=20)
        with pytest.raises(IdempotencyConflictError):
            svc.submit_order("broker1", req2)


class TestIdempotencyBrokerIsolation:
    def test_different_broker_same_client_order_id(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        req = _make_request(client_order_id="shared")
        resp1 = svc.submit_order("broker1", req)
        resp2 = svc.submit_order("broker2", req)
        assert resp1.order_id != resp2.order_id


class TestNoClientOrderIdNotIdempotent:
    def test_submissions_without_client_order_id(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        req = _make_request()
        resp1 = svc.submit_order("broker1", req)
        resp2 = svc.submit_order("broker1", req)
        assert resp1.order_id != resp2.order_id


class TestIdempotentOrderGetStatus:
    def test_status_works_for_idempotent_order(self) -> None:
        svc = OrderGatewayService(clock=_fake_clock())
        req = _make_request(client_order_id="id1")
        svc.submit_order("broker1", req)
        resp = svc.get_order("broker1", "AAPL-1")
        assert resp.order_id == "AAPL-1"
        assert resp.status == ApiOrderStatus.OPEN
