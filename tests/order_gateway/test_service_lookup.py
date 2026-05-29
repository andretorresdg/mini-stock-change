"""Tests for OrderGatewayService.get_order (broker-scoped lookup)."""

from datetime import UTC, datetime, timedelta

import pytest

from mini_exchange.order_gateway.errors import InvalidBrokerError, OrderNotFoundError
from mini_exchange.order_gateway.models import (
    GatewayOrderStatus,
    GatewaySubmitOrder,
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
        "valid_until": _FUTURE,
        "symbol": "AAPL",
        "price": price,
        "quantity": quantity,
    }
    defaults.update(kwargs)
    return GatewaySubmitOrder(**defaults)  # type: ignore[arg-type]


def _bid(
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
        "valid_until": _FUTURE,
        "symbol": "AAPL",
        "price": price,
        "quantity": quantity,
    }
    defaults.update(kwargs)
    return GatewaySubmitOrder(**defaults)  # type: ignore[arg-type]


class TestGetRestingOrder:
    def test_retrieve_after_submission(self) -> None:
        svc = _service()
        submitted = svc.submit_order(_ask())
        result = svc.get_order("seller", submitted.order_id)
        assert result.order_id == submitted.order_id
        assert result.status == GatewayOrderStatus.OPEN
        assert result.remaining_quantity == 10
        assert result.filled_quantity == 0
        assert result.trades == ()


class TestGetFilledOrder:
    def test_retrieve_filled_order(self) -> None:
        svc = _service()
        ask_result = svc.submit_order(_ask(price=100, quantity=10))
        svc.submit_order(_bid(price=100, quantity=10))
        result = svc.get_order("seller", ask_result.order_id)
        assert result.status == GatewayOrderStatus.FILLED
        assert result.filled_quantity == 10
        assert result.remaining_quantity == 0


class TestGetPartiallyFilledOrder:
    def test_retrieve_partially_filled(self) -> None:
        svc = _service()
        ask_result = svc.submit_order(_ask(price=100, quantity=10))
        svc.submit_order(_bid(price=100, quantity=3))
        result = svc.get_order("seller", ask_result.order_id)
        assert result.status == GatewayOrderStatus.PARTIALLY_FILLED
        assert result.filled_quantity == 3
        assert result.remaining_quantity == 7


class TestGetOrderWithTrades:
    def test_all_related_trades_included(self) -> None:
        svc = _service()
        ask_result = svc.submit_order(_ask(price=100, quantity=10))
        svc.submit_order(_bid(price=100, quantity=4, broker_id="b1"))
        svc.submit_order(_bid(price=100, quantity=3, broker_id="b2"))
        result = svc.get_order("seller", ask_result.order_id)
        assert len(result.trades) == 2
        assert result.trades[0].quantity == 4
        assert result.trades[1].quantity == 3
        assert all(t.seller_order_id == ask_result.order_id for t in result.trades)


class TestOrderNotFound:
    def test_unknown_order_raises(self) -> None:
        svc = _service()
        with pytest.raises(OrderNotFoundError):
            svc.get_order("broker1", "NONEXISTENT")

    def test_wrong_broker_raises(self) -> None:
        svc = _service()
        submitted = svc.submit_order(_ask(broker_id="seller"))
        with pytest.raises(OrderNotFoundError):
            svc.get_order("other-broker", submitted.order_id)


class TestInvalidBrokerId:
    def test_invalid_broker_raises(self) -> None:
        svc = _service()
        with pytest.raises(InvalidBrokerError):
            svc.get_order("bad broker!", "ORD-1")


class TestLiveStatusAfterMatch:
    def test_status_updates_after_another_order_matches(self) -> None:
        svc = _service()
        ask_result = svc.submit_order(_ask(price=100, quantity=10))
        before = svc.get_order("seller", ask_result.order_id)
        assert before.status == GatewayOrderStatus.OPEN

        svc.submit_order(_bid(price=100, quantity=10))
        after = svc.get_order("seller", ask_result.order_id)
        assert after.status == GatewayOrderStatus.FILLED


class TestStatusOverride:
    def test_status_override_takes_precedence(self) -> None:
        svc = _service()
        submitted = svc.submit_order(_ask())
        # Simulate an expiration override (set directly on metadata for now)
        svc._metadata_by_order_id[
            submitted.order_id
        ].status_override = GatewayOrderStatus.EXPIRED
        result = svc.get_order("seller", submitted.order_id)
        assert result.status == GatewayOrderStatus.EXPIRED


class TestNoApiImports:
    def test_service_module_has_no_fastapi_or_pydantic_imports(self) -> None:
        import inspect

        import mini_exchange.order_gateway.service as mod

        source = inspect.getsource(mod)
        assert "fastapi" not in source.lower()
        assert "pydantic" not in source.lower()
