"""Tests for the OrderBook matching engine."""

import pytest

from mini_exchange.orderbook import OrderBook, OrderStatus, Side


@pytest.fixture
def book() -> OrderBook:
    return OrderBook("AAPL")


class TestBasicMatching:
    def test_same_price_full_match(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 100, 10)
        report = book.submit_limit_order("B2", Side.BUY, 100, 10)
        assert len(report.trades) == 1
        t = report.trades[0]
        assert t.price == 100
        assert t.quantity == 10
        assert report.accepted_order.status == OrderStatus.FILLED

    def test_no_match_price_below(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 100, 10)
        report = book.submit_limit_order("B2", Side.BUY, 99, 10)
        assert len(report.trades) == 0
        assert report.accepted_order.status == OrderStatus.OPEN

    def test_price_gap_uses_seller_price(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 95, 10)
        report = book.submit_limit_order("B2", Side.BUY, 100, 10)
        assert report.trades[0].price == 95

    def test_partial_fill_seller_larger(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 100, 20)
        report = book.submit_limit_order("B2", Side.BUY, 100, 5)
        assert report.trades[0].quantity == 5
        assert report.accepted_order.status == OrderStatus.FILLED
        sell = book.get_order("AAPL-1")
        assert sell is not None
        assert sell.remaining == 15
        assert sell.status == OrderStatus.PARTIALLY_FILLED

    def test_multiple_sellers_matched(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 100, 5, order_id="S1")
        book.submit_limit_order("B2", Side.SELL, 100, 5, order_id="S2")
        report = book.submit_limit_order("B3", Side.BUY, 100, 8)
        assert len(report.trades) == 2
        assert report.trades[0].quantity == 5
        assert report.trades[0].seller_order_id == "S1"
        assert report.trades[1].quantity == 3
        assert report.trades[1].seller_order_id == "S2"
        assert report.accepted_order.status == OrderStatus.FILLED


class TestFifoAndPricePriority:
    def test_fifo_at_same_price(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 100, 5, order_id="S1")
        book.submit_limit_order("B2", Side.SELL, 100, 5, order_id="S2")
        report = book.submit_limit_order("B3", Side.BUY, 100, 5)
        assert report.trades[0].seller_order_id == "S1"

    def test_price_priority_before_time(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 101, 5, order_id="S1")
        book.submit_limit_order("B2", Side.SELL, 99, 5, order_id="S2")
        report = book.submit_limit_order("B3", Side.BUY, 101, 5)
        assert report.trades[0].seller_order_id == "S2"
        assert report.trades[0].price == 99

    def test_sell_matches_highest_bid_first(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.BUY, 99, 5, order_id="Bid1")
        book.submit_limit_order("B2", Side.BUY, 101, 5, order_id="Bid2")
        report = book.submit_limit_order("B3", Side.SELL, 99, 5)
        assert report.trades[0].buyer_order_id == "Bid2"
        assert report.trades[0].price == 99


class TestSellerPriceRule:
    def test_resting_buy_crossed_by_sell(self, book: OrderBook) -> None:
        """When a BUY rests and a SELL arrives, execution uses seller price."""
        book.submit_limit_order("B1", Side.BUY, 105, 10, order_id="Bid1")
        report = book.submit_limit_order("B2", Side.SELL, 100, 10)
        assert report.trades[0].price == 100


class TestRestingOrders:
    def test_buy_rests_when_no_asks(self, book: OrderBook) -> None:
        report = book.submit_limit_order("B1", Side.BUY, 100, 10)
        assert len(report.trades) == 0
        assert report.accepted_order.status == OrderStatus.OPEN
        assert book.best_bid() == 100

    def test_sell_rests_when_no_bids(self, book: OrderBook) -> None:
        report = book.submit_limit_order("B1", Side.SELL, 100, 10)
        assert len(report.trades) == 0
        assert report.accepted_order.status == OrderStatus.OPEN
        assert book.best_ask() == 100


class TestDuplicateOrderId:
    def test_duplicate_rejected(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.BUY, 100, 10, order_id="dup")
        with pytest.raises(ValueError, match="duplicate order_id"):
            book.submit_limit_order("B2", Side.BUY, 100, 10, order_id="dup")


class TestBestBidAsk:
    def test_after_full_match(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 100, 10)
        book.submit_limit_order("B2", Side.BUY, 100, 10)
        assert book.best_bid() is None
        assert book.best_ask() is None

    def test_after_partial_match(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 100, 10)
        book.submit_limit_order("B2", Side.BUY, 100, 5)
        assert book.best_bid() is None
        assert book.best_ask() == 100


class TestSnapshot:
    def test_depth_limiting(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.BUY, 100, 5)
        book.submit_limit_order("B2", Side.BUY, 99, 5)
        book.submit_limit_order("B3", Side.BUY, 98, 5)
        snap = book.snapshot(depth=2)
        assert len(snap["bids"]) == 2
        assert snap["bids"][0]["price"] == 100
        assert snap["bids"][1]["price"] == 99

    def test_full_snapshot(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.BUY, 100, 5)
        book.submit_limit_order("B2", Side.SELL, 110, 3)
        snap = book.snapshot()
        assert snap == {
            "bids": [{"price": 100, "quantity": 5}],
            "asks": [{"price": 110, "quantity": 3}],
        }


class TestDeterminism:
    def test_trade_id_format(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 100, 10)
        report = book.submit_limit_order("B2", Side.BUY, 100, 10)
        assert report.trades[0].trade_id == "AAPL-T1"

    def test_trade_sequence_increments(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 100, 5, order_id="S1")
        book.submit_limit_order("B2", Side.SELL, 100, 5, order_id="S2")
        report = book.submit_limit_order("B3", Side.BUY, 100, 10)
        assert report.trades[0].sequence == 1
        assert report.trades[1].sequence == 2

    def test_auto_generated_order_id(self, book: OrderBook) -> None:
        report = book.submit_limit_order("B1", Side.BUY, 100, 10)
        assert report.accepted_order.order_id == "AAPL-1"

    def test_trades_property(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 100, 10)
        book.submit_limit_order("B2", Side.BUY, 100, 10)
        assert len(book.trades) == 1
        assert book.trades[0].trade_id == "AAPL-T1"


class TestOrderStatuses:
    def test_full_fill_status(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 100, 10)
        report = book.submit_limit_order("B2", Side.BUY, 100, 10)
        assert report.accepted_order.status == OrderStatus.FILLED

    def test_partial_fill_status(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.SELL, 100, 10)
        report = book.submit_limit_order("B2", Side.BUY, 100, 5)
        sell = book.get_order("AAPL-1")
        assert sell is not None
        assert sell.status == OrderStatus.PARTIALLY_FILLED
        assert report.accepted_order.status == OrderStatus.FILLED


class TestGetOrder:
    def test_nonexistent_returns_none(self, book: OrderBook) -> None:
        assert book.get_order("missing") is None


class TestEmptySymbol:
    def test_empty_symbol_rejected(self) -> None:
        with pytest.raises(ValueError, match="symbol must be non-empty"):
            OrderBook("")
