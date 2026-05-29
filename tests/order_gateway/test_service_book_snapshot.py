"""Tests for OrderGatewayService.get_book_snapshot()."""

from datetime import UTC, datetime, timedelta

import pytest

from mini_exchange.order_gateway.models import (
    GatewayBookLevel,
    GatewayBookSnapshot,
    GatewaySubmitOrder,
)
from mini_exchange.order_gateway.service import OrderGatewayService
from mini_exchange.orderbook.models import Side

_NOW = datetime(2030, 6, 15, 12, 0, 0, tzinfo=UTC)
_FUTURE = _NOW + timedelta(hours=1)


class _MutableClock:
    def __init__(self, at: datetime = _NOW) -> None:
        self.now = at

    def __call__(self) -> datetime:
        return self.now


def _svc(clock: _MutableClock | None = None) -> OrderGatewayService:
    c = clock or _MutableClock()
    return OrderGatewayService(clock=c)


def _ask(
    broker: str = "seller",
    price: int = 1_000,
    quantity: int = 100,
    symbol: str = "AAPL",
    valid_until: datetime = _FUTURE,
) -> GatewaySubmitOrder:
    return GatewaySubmitOrder(
        broker_id=broker,
        document_number=f"DOC-{broker}",
        client_order_id=None,
        side=Side.SELL,
        valid_until=valid_until,
        symbol=symbol,
        price=price,
        quantity=quantity,
    )


def _bid(
    broker: str = "buyer",
    price: int = 1_000,
    quantity: int = 100,
    symbol: str = "AAPL",
    valid_until: datetime = _FUTURE,
) -> GatewaySubmitOrder:
    return GatewaySubmitOrder(
        broker_id=broker,
        document_number=f"DOC-{broker}",
        client_order_id=None,
        side=Side.BUY,
        valid_until=valid_until,
        symbol=symbol,
        price=price,
        quantity=quantity,
    )


class TestGatewayBookLevelValidation:
    """GatewayBookLevel rejects invalid arguments."""

    def test_price_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="price"):
            GatewayBookLevel(price=0, quantity=1)

    def test_price_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="price"):
            GatewayBookLevel(price=-1, quantity=1)

    def test_price_non_integer_raises(self) -> None:
        with pytest.raises(TypeError, match="price"):
            GatewayBookLevel(price=1.5, quantity=1)  # type: ignore[arg-type]

    def test_quantity_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="quantity"):
            GatewayBookLevel(price=1, quantity=0)

    def test_valid_level_constructed(self) -> None:
        level = GatewayBookLevel(price=1_000, quantity=100)
        assert level.price == 1_000
        assert level.quantity == 100


class TestGatewayBookSnapshotValidation:
    """GatewayBookSnapshot rejects empty symbol."""

    def test_empty_symbol_raises(self) -> None:
        with pytest.raises(ValueError, match="symbol"):
            GatewayBookSnapshot(symbol="", bids=(), asks=())

    def test_whitespace_symbol_raises(self) -> None:
        with pytest.raises(ValueError, match="symbol"):
            GatewayBookSnapshot(symbol="   ", bids=(), asks=())

    def test_valid_snapshot_constructed(self) -> None:
        snap = GatewayBookSnapshot(symbol="AAPL", bids=(), asks=())
        assert snap.symbol == "AAPL"
        assert snap.bids == ()
        assert snap.asks == ()


class TestEmptyBook:
    def test_unknown_symbol_returns_empty_bids_and_asks(self) -> None:
        svc = _svc()
        snap = svc.get_book_snapshot("AAPL")
        assert snap.symbol == "AAPL"
        assert snap.bids == ()
        assert snap.asks == ()


class TestSymbolNormalization:
    def test_lowercase_symbol_normalized_to_uppercase(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(price=1_000))
        snap = svc.get_book_snapshot("aapl")
        assert snap.symbol == "AAPL"
        assert len(snap.asks) == 1

    def test_symbol_whitespace_trimmed(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(price=1_000))
        snap = svc.get_book_snapshot("  AAPL  ")
        assert snap.symbol == "AAPL"
        assert len(snap.asks) == 1


class TestRestingOrders:
    def test_resting_ask_appears_in_asks(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(price=1_000, quantity=100))
        snap = svc.get_book_snapshot("AAPL")
        assert len(snap.asks) == 1
        assert snap.asks[0].price == 1_000
        assert snap.asks[0].quantity == 100

    def test_resting_bid_appears_in_bids(self) -> None:
        svc = _svc()
        svc.submit_order(_bid(price=900, quantity=50))
        snap = svc.get_book_snapshot("AAPL")
        assert len(snap.bids) == 1
        assert snap.bids[0].price == 900
        assert snap.bids[0].quantity == 50

    def test_no_match_shows_both_sides(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(price=2_000, quantity=100))
        svc.submit_order(_bid(price=1_000, quantity=100))
        snap = svc.get_book_snapshot("AAPL")
        assert len(snap.asks) == 1
        assert len(snap.bids) == 1
        assert snap.asks[0].price == 2_000
        assert snap.bids[0].price == 1_000


class TestSorting:
    def test_bid_levels_sorted_descending(self) -> None:
        svc = _svc()
        for price, broker in [
            (1_000, "b1"),
            (2_000, "b2"),
            (1_500, "b3"),
        ]:
            svc.submit_order(_bid(broker=broker, price=price, quantity=10))
        snap = svc.get_book_snapshot("AAPL")
        prices = [lvl.price for lvl in snap.bids]
        assert prices == sorted(prices, reverse=True)

    def test_ask_levels_sorted_ascending(self) -> None:
        svc = _svc()
        for price, broker in [
            (2_000, "s1"),
            (1_000, "s2"),
            (1_500, "s3"),
        ]:
            svc.submit_order(_ask(broker=broker, price=price, quantity=10))
        snap = svc.get_book_snapshot("AAPL")
        prices = [lvl.price for lvl in snap.asks]
        assert prices == sorted(prices)


class TestAggregation:
    def test_same_price_bid_quantities_aggregated(self) -> None:
        svc = _svc()
        svc.submit_order(_bid(broker="buyer1", price=1_000, quantity=30))
        svc.submit_order(_bid(broker="buyer2", price=1_000, quantity=20))
        snap = svc.get_book_snapshot("AAPL")
        assert len(snap.bids) == 1
        assert snap.bids[0].price == 1_000
        assert snap.bids[0].quantity == 50

    def test_same_price_ask_quantities_aggregated(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(broker="seller1", price=1_000, quantity=40))
        svc.submit_order(_ask(broker="seller2", price=1_000, quantity=60))
        snap = svc.get_book_snapshot("AAPL")
        assert len(snap.asks) == 1
        assert snap.asks[0].price == 1_000
        assert snap.asks[0].quantity == 100


class TestDepthParameter:
    def test_depth_limits_ask_levels(self) -> None:
        svc = _svc()
        brokers = ["s1", "s2", "s3", "s4", "s5"]
        for i, broker in enumerate(brokers):
            svc.submit_order(_ask(broker=broker, price=(i + 1) * 1_000, quantity=10))
        snap = svc.get_book_snapshot("AAPL", depth=3)
        assert len(snap.asks) == 3
        assert snap.asks[0].price == 1_000
        assert snap.asks[1].price == 2_000
        assert snap.asks[2].price == 3_000


class TestFilledOrdersExcluded:
    def test_fully_matched_orders_not_in_snapshot(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(price=1_000, quantity=100))
        svc.submit_order(_bid(price=1_000, quantity=100))
        snap = svc.get_book_snapshot("AAPL")
        assert snap.bids == ()
        assert snap.asks == ()

    def test_partially_filled_ask_shows_remaining_quantity(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(price=1_000, quantity=100))
        svc.submit_order(_bid(price=1_000, quantity=40))
        snap = svc.get_book_snapshot("AAPL")
        assert len(snap.asks) == 1
        assert snap.asks[0].quantity == 60


class TestExpiredOrderExcluded:
    def test_expired_resting_ask_not_in_snapshot(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _svc(clock=clock)
        expires_at = _NOW + timedelta(minutes=30)
        svc.submit_order(_ask(price=1_000, quantity=100, valid_until=expires_at))
        clock.now = _NOW + timedelta(hours=1)
        snap = svc.get_book_snapshot("AAPL")
        assert snap.asks == ()
