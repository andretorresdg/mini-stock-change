"""Tests for the SideBook class."""

import pytest

from mini_exchange.orderbook import Order, OrderStatus, Side, SideBook


def make_order(
    side: Side = Side.BUY,
    price: int = 100,
    quantity: int = 10,
    sequence: int = 1,
    order_id: str = "O1",
) -> Order:
    """Create a default valid order."""
    return Order(
        order_id=order_id,
        broker_id="B1",
        symbol="AAPL",
        side=side,
        price=price,
        quantity=quantity,
        sequence=sequence,
    )


class TestBuyBestPrice:
    def test_highest_price_is_best(self) -> None:
        book = SideBook(Side.BUY)
        book.add(make_order(price=90, sequence=1, order_id="O1"))
        book.add(make_order(price=110, sequence=2, order_id="O2"))
        book.add(make_order(price=100, sequence=3, order_id="O3"))
        assert book.best_price() == 110

    def test_empty_book_returns_none(self) -> None:
        book = SideBook(Side.BUY)
        assert book.best_price() is None

    def test_peek_best_order_empty(self) -> None:
        book = SideBook(Side.BUY)
        assert book.peek_best_order() is None


class TestSellBestPrice:
    def test_lowest_price_is_best(self) -> None:
        book = SideBook(Side.SELL)
        book.add(make_order(side=Side.SELL, price=110, sequence=1, order_id="O1"))
        book.add(make_order(side=Side.SELL, price=90, sequence=2, order_id="O2"))
        book.add(make_order(side=Side.SELL, price=100, sequence=3, order_id="O3"))
        assert book.best_price() == 90


class TestFifoOrdering:
    def test_fifo_within_same_price(self) -> None:
        book = SideBook(Side.BUY)
        o1 = make_order(price=100, sequence=1, order_id="O1")
        o2 = make_order(price=100, sequence=2, order_id="O2")
        o3 = make_order(price=100, sequence=3, order_id="O3")
        book.add(o1)
        book.add(o2)
        book.add(o3)
        assert book.peek_best_order() is o1

    def test_fifo_after_front_filled(self) -> None:
        book = SideBook(Side.BUY)
        o1 = make_order(price=100, sequence=1, order_id="O1")
        o2 = make_order(price=100, sequence=2, order_id="O2")
        book.add(o1)
        book.add(o2)
        o1.apply_fill(10)
        assert book.peek_best_order() is o2


class TestSnapshotBuy:
    def test_aggregates_by_price_descending(self) -> None:
        book = SideBook(Side.BUY)
        book.add(make_order(price=100, quantity=5, sequence=1, order_id="O1"))
        book.add(make_order(price=100, quantity=3, sequence=2, order_id="O2"))
        book.add(make_order(price=90, quantity=7, sequence=3, order_id="O3"))
        levels = book.snapshot_levels()
        assert levels == [
            {"price": 100, "quantity": 8},
            {"price": 90, "quantity": 7},
        ]

    def test_skips_inactive_orders(self) -> None:
        book = SideBook(Side.BUY)
        o1 = make_order(price=100, quantity=10, sequence=1, order_id="O1")
        o2 = make_order(price=100, quantity=5, sequence=2, order_id="O2")
        book.add(o1)
        book.add(o2)
        o1.cancel()
        levels = book.snapshot_levels()
        assert levels == [{"price": 100, "quantity": 5}]


class TestSnapshotSell:
    def test_aggregates_by_price_ascending(self) -> None:
        book = SideBook(Side.SELL)
        book.add(
            make_order(side=Side.SELL, price=110, quantity=4, sequence=1, order_id="O1")
        )
        book.add(
            make_order(side=Side.SELL, price=90, quantity=6, sequence=2, order_id="O2")
        )
        levels = book.snapshot_levels()
        assert levels == [
            {"price": 90, "quantity": 6},
            {"price": 110, "quantity": 4},
        ]


class TestLazyCleanup:
    def test_filled_orders_skipped_lazily(self) -> None:
        book = SideBook(Side.BUY)
        o1 = make_order(price=100, quantity=10, sequence=1, order_id="O1")
        o2 = make_order(price=100, quantity=5, sequence=2, order_id="O2")
        book.add(o1)
        book.add(o2)
        o1.apply_fill(10)
        assert o1.status == OrderStatus.FILLED
        assert book.peek_best_order() is o2

    def test_canceled_orders_skipped_lazily(self) -> None:
        book = SideBook(Side.BUY)
        o1 = make_order(price=100, quantity=10, sequence=1, order_id="O1")
        o2 = make_order(price=100, quantity=5, sequence=2, order_id="O2")
        book.add(o1)
        book.add(o2)
        o1.cancel()
        assert book.peek_best_order() is o2

    def test_all_orders_inactive_returns_none(self) -> None:
        book = SideBook(Side.BUY)
        o1 = make_order(price=100, quantity=10, sequence=1, order_id="O1")
        book.add(o1)
        o1.apply_fill(10)
        assert book.best_price() is None
        assert book.peek_best_order() is None

    def test_discard_inactive_head_cleans_level(self) -> None:
        book = SideBook(Side.BUY)
        o1 = make_order(price=100, quantity=10, sequence=1, order_id="O1")
        o2 = make_order(price=100, quantity=5, sequence=2, order_id="O2")
        book.add(o1)
        book.add(o2)
        o1.cancel()
        book.discard_inactive_head(100)
        assert book.peek_best_order() is o2

    def test_discard_inactive_head_removes_empty_level(self) -> None:
        book = SideBook(Side.BUY)
        o1 = make_order(price=100, quantity=10, sequence=1, order_id="O1")
        book.add(o1)
        o1.cancel()
        book.discard_inactive_head(100)
        assert book.snapshot_levels() == []

    def test_discard_inactive_head_nonexistent_price(self) -> None:
        book = SideBook(Side.BUY)
        book.discard_inactive_head(999)


class TestRejection:
    def test_side_mismatch_rejected(self) -> None:
        book = SideBook(Side.BUY)
        sell_order = make_order(side=Side.SELL)
        with pytest.raises(ValueError, match="expected BUY order, got SELL"):
            book.add(sell_order)

    def test_inactive_order_rejected(self) -> None:
        book = SideBook(Side.BUY)
        order = make_order()
        order.cancel()
        with pytest.raises(ValueError, match="cannot add an inactive order"):
            book.add(order)

    def test_stale_heap_entry_cleaned(self) -> None:
        """Cover lines 43-44: heap entry with no matching level."""
        book = SideBook(Side.BUY)
        o1 = make_order(price=100, quantity=10, sequence=1, order_id="O1")
        o2 = make_order(price=90, quantity=5, sequence=2, order_id="O2")
        book.add(o1)
        book.add(o2)
        # Cancel o1 and use discard_inactive_head to remove level from _levels
        # but the heap entry for price=100 remains
        o1.cancel()
        book.discard_inactive_head(100)
        # Now best_price() finds heap entry -100, but _levels[100] is gone
        assert book.best_price() == 90

    def test_snapshot_skips_level_with_all_inactive(self) -> None:
        """Cover branch 74->72: level exists but total is 0."""
        book = SideBook(Side.BUY)
        o1 = make_order(price=100, quantity=10, sequence=1, order_id="O1")
        o2 = make_order(price=90, quantity=5, sequence=2, order_id="O2")
        book.add(o1)
        book.add(o2)
        # Cancel o1 but don't trigger lazy cleanup via best_price
        o1.cancel()
        # snapshot_levels iterates _levels directly; price 100 still in dict
        levels = book.snapshot_levels()
        assert levels == [{"price": 90, "quantity": 5}]
