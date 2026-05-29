"""Acceptance tests for the matching-engine rules.

These tests mirror the written challenge requirements exactly and act
as executable documentation for the exchange's expected behaviour.

All prices are expressed as integer cents:
  $10.00 = 1_000 cents
  $20.00 = 2_000 cents

No floats are used anywhere in this file.
"""

import pytest

from mini_exchange.orderbook import MatchingEngine, OrderStatus, Side

SYMBOL = "AAPL"

# Price constants in integer cents — no floats.
PRICE_10 = 1_000  # $10.00
PRICE_20 = 2_000  # $20.00


@pytest.fixture
def engine() -> MatchingEngine:
    """A fresh matching engine, isolated per test."""
    return MatchingEngine()


# ── Requirement 1: Same price ─────────────────────────────────────────────────


class TestSamePriceFullMatch:
    """ASK 1000 AAPL @ $10, BID 1000 AAPL @ $10.

    One trade executes at $10; both sides are fully filled.
    """

    def test_one_trade_is_generated(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            1_000,
            document_number="11111111100",
        )
        report = engine.submit_limit_order(
            SYMBOL, "buyer-b", Side.BUY, PRICE_10, 1_000, document_number="22222222200"
        )

        assert len(report.trades) == 1

    def test_execution_price_is_ten_dollars(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            1_000,
            document_number="11111111100",
        )
        report = engine.submit_limit_order(
            SYMBOL, "buyer-b", Side.BUY, PRICE_10, 1_000, document_number="22222222200"
        )

        assert report.trades[0].price == PRICE_10  # 1_000 cents = $10.00
        assert report.trades[0].quantity == 1_000

    def test_buyer_is_fully_filled(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            1_000,
            document_number="11111111100",
        )
        report = engine.submit_limit_order(
            SYMBOL, "buyer-b", Side.BUY, PRICE_10, 1_000, document_number="22222222200"
        )

        assert report.accepted_order.status == OrderStatus.FILLED
        assert report.accepted_order.remaining == 0

    def test_seller_is_fully_filled(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            1_000,
            order_id="ask-a",
            document_number="11111111100",
        )
        engine.submit_limit_order(
            SYMBOL, "buyer-b", Side.BUY, PRICE_10, 1_000, document_number="22222222200"
        )

        ask = engine.book(SYMBOL).get_order("ask-a")
        assert ask is not None
        assert ask.status == OrderStatus.FILLED
        assert ask.remaining == 0


# ── Requirement 2: No match ───────────────────────────────────────────────────


class TestNoMatch:
    """ASK 1000 AAPL @ $20, BID 1000 AAPL @ $10 → bid below ask → no trade."""

    def test_no_trades_are_generated(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_20,
            1_000,
            document_number="11111111100",
        )
        report = engine.submit_limit_order(
            SYMBOL, "buyer-b", Side.BUY, PRICE_10, 1_000, document_number="22222222200"
        )

        assert len(report.trades) == 0

    def test_both_orders_remain_open(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_20,
            1_000,
            order_id="ask-a",
            document_number="11111111100",
        )
        bid_report = engine.submit_limit_order(
            SYMBOL, "buyer-b", Side.BUY, PRICE_10, 1_000, document_number="22222222200"
        )

        ask = engine.book(SYMBOL).get_order("ask-a")
        assert ask is not None
        assert ask.status == OrderStatus.OPEN
        assert bid_report.accepted_order.status == OrderStatus.OPEN

    def test_book_snapshot_shows_resting_ask_and_bid(
        self, engine: MatchingEngine
    ) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_20,
            1_000,
            document_number="11111111100",
        )
        engine.submit_limit_order(
            SYMBOL, "buyer-b", Side.BUY, PRICE_10, 1_000, document_number="22222222200"
        )

        snap = engine.snapshot(SYMBOL)
        ask_prices = [level["price"] for level in snap["asks"]]
        bid_prices = [level["price"] for level in snap["bids"]]
        assert PRICE_20 in ask_prices
        assert PRICE_10 in bid_prices


# ── Requirement 3: Price gap — trade executes at the seller's price ───────────


class TestPriceGapSellerPriceWins:
    """ASK 1000 AAPL @ $10, BID 1000 AAPL @ $20.

    Trade executes at the seller's price of $10, not the buyer's $20.
    """

    def test_execution_price_is_seller_price_not_buyer_price(
        self, engine: MatchingEngine
    ) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            1_000,
            document_number="11111111100",
        )
        report = engine.submit_limit_order(
            SYMBOL, "buyer-b", Side.BUY, PRICE_20, 1_000, document_number="22222222200"
        )

        assert report.trades[0].price == PRICE_10  # $10.00, not $20.00

    def test_both_orders_are_fully_executed(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            1_000,
            document_number="11111111100",
        )
        report = engine.submit_limit_order(
            SYMBOL, "buyer-b", Side.BUY, PRICE_20, 1_000, document_number="22222222200"
        )

        assert report.accepted_order.status == OrderStatus.FILLED
        assert report.trades[0].quantity == 1_000


# ── Requirement 4: Partial execution ─────────────────────────────────────────


class TestPartialExecution:
    """ASK 1000 AAPL @ $10, BID 500 AAPL @ $10 → buyer filled, seller 500 remaining."""

    def test_trade_quantity_equals_buyer_quantity(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            1_000,
            document_number="11111111100",
        )
        report = engine.submit_limit_order(
            SYMBOL, "buyer-b", Side.BUY, PRICE_10, 500, document_number="22222222200"
        )

        assert report.trades[0].quantity == 500

    def test_buyer_is_fully_filled(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            1_000,
            document_number="11111111100",
        )
        report = engine.submit_limit_order(
            SYMBOL, "buyer-b", Side.BUY, PRICE_10, 500, document_number="22222222200"
        )

        assert report.accepted_order.status == OrderStatus.FILLED
        assert report.accepted_order.remaining == 0

    def test_seller_is_partially_filled_with_500_remaining(
        self, engine: MatchingEngine
    ) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            1_000,
            order_id="ask-a",
            document_number="11111111100",
        )
        engine.submit_limit_order(
            SYMBOL, "buyer-b", Side.BUY, PRICE_10, 500, document_number="22222222200"
        )

        ask = engine.book(SYMBOL).get_order("ask-a")
        assert ask is not None
        assert ask.status == OrderStatus.PARTIALLY_FILLED
        assert ask.remaining == 500


# ── Requirement 5: Multiple sellers, one larger buyer ─────────────────────────


class TestMultipleSellersOneLargerBuyer:
    """ASK-A 500, ASK-B 500, BID-C 1500.

    A fills first, B fills second; C rests with 500 remaining on the bid side.
    """

    def test_two_trades_are_generated(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL, "seller-a", Side.SELL, PRICE_10, 500, document_number="11111111100"
        )
        engine.submit_limit_order(
            SYMBOL, "seller-b", Side.SELL, PRICE_10, 500, document_number="22222222200"
        )
        report = engine.submit_limit_order(
            SYMBOL, "buyer-c", Side.BUY, PRICE_10, 1_500, document_number="33333333300"
        )

        assert len(report.trades) == 2

    def test_seller_a_fills_first_then_seller_b(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            500,
            order_id="ask-a",
            document_number="11111111100",
        )
        engine.submit_limit_order(
            SYMBOL,
            "seller-b",
            Side.SELL,
            PRICE_10,
            500,
            order_id="ask-b",
            document_number="22222222200",
        )
        report = engine.submit_limit_order(
            SYMBOL, "buyer-c", Side.BUY, PRICE_10, 1_500, document_number="33333333300"
        )

        assert report.trades[0].seller_order_id == "ask-a"
        assert report.trades[1].seller_order_id == "ask-b"

    def test_both_sellers_are_fully_filled(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            500,
            order_id="ask-a",
            document_number="11111111100",
        )
        engine.submit_limit_order(
            SYMBOL,
            "seller-b",
            Side.SELL,
            PRICE_10,
            500,
            order_id="ask-b",
            document_number="22222222200",
        )
        engine.submit_limit_order(
            SYMBOL, "buyer-c", Side.BUY, PRICE_10, 1_500, document_number="33333333300"
        )

        ask_a = engine.book(SYMBOL).get_order("ask-a")
        ask_b = engine.book(SYMBOL).get_order("ask-b")
        assert ask_a is not None and ask_a.status == OrderStatus.FILLED
        assert ask_b is not None and ask_b.status == OrderStatus.FILLED

    def test_buyer_remains_partially_filled_with_500_remaining(
        self, engine: MatchingEngine
    ) -> None:
        engine.submit_limit_order(
            SYMBOL, "seller-a", Side.SELL, PRICE_10, 500, document_number="11111111100"
        )
        engine.submit_limit_order(
            SYMBOL, "seller-b", Side.SELL, PRICE_10, 500, document_number="22222222200"
        )
        report = engine.submit_limit_order(
            SYMBOL, "buyer-c", Side.BUY, PRICE_10, 1_500, document_number="33333333300"
        )

        assert report.accepted_order.status == OrderStatus.PARTIALLY_FILLED
        assert report.accepted_order.remaining == 500


# ── Requirement 6: FIFO at the same price level ───────────────────────────────


class TestFifoAtSamePriceLevel:
    """At equal ask prices, the earliest submitted order matches before later ones."""

    def test_earlier_seller_matches_before_later_seller(
        self, engine: MatchingEngine
    ) -> None:
        # seller-a submits first
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            1_000,
            order_id="ask-a",
            document_number="11111111100",
        )
        # seller-b submits second at the same price
        engine.submit_limit_order(
            SYMBOL,
            "seller-b",
            Side.SELL,
            PRICE_10,
            1_000,
            order_id="ask-b",
            document_number="22222222200",
        )
        # buyer-c buys exactly 1000 — should match seller-a only
        report = engine.submit_limit_order(
            SYMBOL, "buyer-c", Side.BUY, PRICE_10, 1_000, document_number="33333333300"
        )

        assert len(report.trades) == 1
        assert report.trades[0].seller_order_id == "ask-a"

    def test_earlier_seller_is_fully_filled(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            1_000,
            order_id="ask-a",
            document_number="11111111100",
        )
        engine.submit_limit_order(
            SYMBOL,
            "seller-b",
            Side.SELL,
            PRICE_10,
            1_000,
            document_number="22222222200",
        )
        engine.submit_limit_order(
            SYMBOL, "buyer-c", Side.BUY, PRICE_10, 1_000, document_number="33333333300"
        )

        ask_a = engine.book(SYMBOL).get_order("ask-a")
        assert ask_a is not None
        assert ask_a.status == OrderStatus.FILLED

    def test_later_seller_remains_open(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "seller-a",
            Side.SELL,
            PRICE_10,
            1_000,
            document_number="11111111100",
        )
        engine.submit_limit_order(
            SYMBOL,
            "seller-b",
            Side.SELL,
            PRICE_10,
            1_000,
            order_id="ask-b",
            document_number="22222222200",
        )
        engine.submit_limit_order(
            SYMBOL, "buyer-c", Side.BUY, PRICE_10, 1_000, document_number="33333333300"
        )

        ask_b = engine.book(SYMBOL).get_order("ask-b")
        assert ask_b is not None
        assert ask_b.status == OrderStatus.OPEN
