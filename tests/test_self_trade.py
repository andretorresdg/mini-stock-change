"""Tests for self-trade prevention by customer document number."""

import pytest

from mini_exchange.orderbook import MatchingEngine, OrderStatus, Side
from tests.customer_documents import CUST_111, CUST_222, CUST_SHARED

SYMBOL = "AAPL"
PRICE_10 = 1_000


@pytest.fixture
def engine() -> MatchingEngine:
    return MatchingEngine()


class TestSelfTradeBlockedSameDocument:
    """Orders with the same document_number must not match, even across brokers."""

    def test_ask_then_bid_same_document_no_trade(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "BROKER-ALPHA",
            Side.SELL,
            PRICE_10,
            100,
            document_number=CUST_SHARED,
        )
        report = engine.submit_limit_order(
            SYMBOL,
            "BROKER-BETA",
            Side.BUY,
            PRICE_10,
            100,
            document_number=CUST_SHARED,
        )

        assert len(report.trades) == 0
        assert report.accepted_order.status == OrderStatus.OPEN

    def test_bid_then_ask_same_document_no_trade(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "BROKER-ALPHA",
            Side.BUY,
            PRICE_10,
            100,
            document_number=CUST_SHARED,
        )
        report = engine.submit_limit_order(
            SYMBOL,
            "BROKER-BETA",
            Side.SELL,
            PRICE_10,
            100,
            document_number=CUST_SHARED,
        )

        assert len(report.trades) == 0
        assert report.accepted_order.status == OrderStatus.OPEN

    def test_both_orders_remain_on_book(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "BROKER-ALPHA",
            Side.SELL,
            PRICE_10,
            100,
            order_id="ask-1",
            document_number=CUST_SHARED,
        )
        engine.submit_limit_order(
            SYMBOL,
            "BROKER-BETA",
            Side.BUY,
            PRICE_10,
            100,
            order_id="bid-1",
            document_number=CUST_SHARED,
        )

        snap = engine.snapshot(SYMBOL)
        assert len(snap["asks"]) == 1
        assert len(snap["bids"]) == 1


class TestDifferentDocumentsMatchNormally:
    """Different document numbers may trade when prices cross."""

    def test_different_documents_execute(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "BROKER-ALPHA",
            Side.SELL,
            PRICE_10,
            100,
            document_number=CUST_111,
        )
        report = engine.submit_limit_order(
            SYMBOL,
            "BROKER-BETA",
            Side.BUY,
            PRICE_10,
            100,
            document_number=CUST_222,
        )

        assert len(report.trades) == 1
        assert report.accepted_order.status == OrderStatus.FILLED

    def test_same_broker_different_documents_may_trade(
        self, engine: MatchingEngine
    ) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "BROKER-ALPHA",
            Side.SELL,
            PRICE_10,
            100,
            document_number=CUST_111,
        )
        report = engine.submit_limit_order(
            SYMBOL,
            "BROKER-ALPHA",
            Side.BUY,
            PRICE_10,
            100,
            document_number=CUST_222,
        )

        assert len(report.trades) == 1


class TestSelfTradeSkippedForNextEligibleCounterparty:
    """Skipping a self-trade candidate must not block unrelated orders."""

    def test_bid_matches_second_ask_when_first_is_self_trade(
        self, engine: MatchingEngine
    ) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "BROKER-ALPHA",
            Side.SELL,
            PRICE_10,
            100,
            order_id="ask-self",
            document_number=CUST_SHARED,
        )
        engine.submit_limit_order(
            SYMBOL,
            "BROKER-BETA",
            Side.SELL,
            PRICE_10,
            100,
            order_id="ask-other",
            document_number=CUST_222,
        )
        report = engine.submit_limit_order(
            SYMBOL,
            "BROKER-C",
            Side.BUY,
            PRICE_10,
            100,
            document_number=CUST_SHARED,
        )

        assert len(report.trades) == 1
        assert report.trades[0].seller_order_id == "ask-other"
        assert report.accepted_order.status == OrderStatus.FILLED

        ask_self = engine.book(SYMBOL).get_order("ask-self")
        assert ask_self is not None
        assert ask_self.status == OrderStatus.OPEN

    def test_partial_fill_skips_self_trade_then_matches_other(
        self, engine: MatchingEngine
    ) -> None:
        engine.submit_limit_order(
            SYMBOL,
            "BROKER-ALPHA",
            Side.SELL,
            PRICE_10,
            50,
            order_id="ask-self",
            document_number=CUST_SHARED,
        )
        engine.submit_limit_order(
            SYMBOL,
            "BROKER-BETA",
            Side.SELL,
            PRICE_10,
            50,
            order_id="ask-other",
            document_number=CUST_222,
        )
        report = engine.submit_limit_order(
            SYMBOL,
            "BROKER-C",
            Side.BUY,
            PRICE_10,
            80,
            document_number=CUST_SHARED,
        )

        assert len(report.trades) == 1
        assert report.trades[0].quantity == 50
        assert report.trades[0].seller_order_id == "ask-other"
        assert report.accepted_order.status == OrderStatus.PARTIALLY_FILLED
        assert report.accepted_order.remaining == 30
