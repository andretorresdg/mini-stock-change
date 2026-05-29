"""Tests for order cancellation in the OrderBook."""

import pytest

from mini_exchange.orderbook import OrderBook, OrderStatus, Side


@pytest.fixture
def book() -> OrderBook:
    return OrderBook("AAPL")


class TestCancelRestingOrders:
    def test_cancel_resting_buy(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100", order_id="Bid1"
        )
        assert book.cancel_order("Bid1") is True
        order = book.get_order("Bid1")
        assert order is not None
        assert order.status == OrderStatus.CANCELED

    def test_cancel_resting_sell(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, document_number="11111111100", order_id="Ask1"
        )
        assert book.cancel_order("Ask1") is True
        order = book.get_order("Ask1")
        assert order is not None
        assert order.status == OrderStatus.CANCELED


class TestCancelFailures:
    def test_cancel_unknown_order(self, book: OrderBook) -> None:
        assert book.cancel_order("missing") is False

    def test_cancel_filled_order(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, document_number="11111111100", order_id="S1"
        )
        book.submit_limit_order("B2", Side.BUY, 100, 10, document_number="22222222200")
        assert book.cancel_order("S1") is False

    def test_cancel_already_canceled(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100", order_id="Bid1"
        )
        book.cancel_order("Bid1")
        assert book.cancel_order("Bid1") is False


class TestCanceledOrderSkippedInMatching:
    def test_canceled_buy_skipped_during_sell_match(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100", order_id="Bid1"
        )
        book.submit_limit_order(
            "B2", Side.BUY, 100, 5, document_number="22222222200", order_id="Bid2"
        )
        book.cancel_order("Bid1")
        report = book.submit_limit_order(
            "B3", Side.SELL, 100, 5, document_number="33333333300"
        )
        assert len(report.trades) == 1
        assert report.trades[0].buyer_order_id == "Bid2"

    def test_canceled_sell_skipped_during_buy_match(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, document_number="11111111100", order_id="Ask1"
        )
        book.submit_limit_order(
            "B2", Side.SELL, 100, 5, document_number="22222222200", order_id="Ask2"
        )
        book.cancel_order("Ask1")
        report = book.submit_limit_order(
            "B3", Side.BUY, 100, 5, document_number="33333333300"
        )
        assert len(report.trades) == 1
        assert report.trades[0].seller_order_id == "Ask2"


class TestBestPriceAfterCancel:
    def test_best_bid_updates_after_cancel(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100", order_id="Bid1"
        )
        book.submit_limit_order(
            "B2", Side.BUY, 90, 5, document_number="22222222200", order_id="Bid2"
        )
        book.cancel_order("Bid1")
        assert book.best_bid() == 90

    def test_best_ask_updates_after_cancel(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, document_number="11111111100", order_id="Ask1"
        )
        book.submit_limit_order(
            "B2", Side.SELL, 110, 5, document_number="22222222200", order_id="Ask2"
        )
        book.cancel_order("Ask1")
        assert book.best_ask() == 110


class TestSnapshotExcludesCanceled:
    def test_snapshot_excludes_canceled(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100", order_id="Bid1"
        )
        book.submit_limit_order(
            "B2", Side.BUY, 90, 5, document_number="22222222200", order_id="Bid2"
        )
        book.cancel_order("Bid1")
        snap = book.snapshot()
        assert snap["bids"] == [{"price": 90, "quantity": 5}]


class TestCanceledOrderInRegistry:
    def test_canceled_order_accessible(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100", order_id="Bid1"
        )
        book.cancel_order("Bid1")
        order = book.get_order("Bid1")
        assert order is not None
        assert order.status == OrderStatus.CANCELED
        assert order.order_id == "Bid1"
