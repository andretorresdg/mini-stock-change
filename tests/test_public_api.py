"""Tests for public API imports from mini_exchange.orderbook."""

from mini_exchange.orderbook import (
    ExecutionReport,
    InvariantViolationError,
    MatchingEngine,
    Order,
    OrderBook,
    OrderStatus,
    Side,
    SideBook,
    Trade,
)


def test_all_public_exports_importable() -> None:
    assert Side.BUY is not None
    assert Side.SELL is not None
    assert OrderStatus.OPEN is not None
    assert OrderStatus.PARTIALLY_FILLED is not None
    assert OrderStatus.FILLED is not None
    assert OrderStatus.CANCELED is not None
    assert Order is not None
    assert Trade is not None
    assert ExecutionReport is not None
    assert OrderBook is not None
    assert MatchingEngine is not None
    assert InvariantViolationError is not None
    assert SideBook is not None


def test_readme_example() -> None:
    """Verify the README example works exactly as documented."""
    book = OrderBook("AAPL")
    book.submit_limit_order(broker_id="seller1", side=Side.SELL, price=1000, quantity=1)
    report = book.submit_limit_order(
        broker_id="buyer1", side=Side.BUY, price=2000, quantity=1
    )
    assert len(report.trades) == 1
    assert report.trades[0].price == 1000
