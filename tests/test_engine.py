"""Tests for the MatchingEngine multi-symbol router."""

import pytest

from mini_exchange.orderbook import MatchingEngine, OrderStatus, Side


@pytest.fixture
def engine() -> MatchingEngine:
    return MatchingEngine()


class TestLazyBookCreation:
    def test_book_created_on_first_access(self, engine: MatchingEngine) -> None:
        book = engine.book("AAPL")
        assert book is engine.book("AAPL")

    def test_different_symbols_different_books(self, engine: MatchingEngine) -> None:
        assert engine.book("AAPL") is not engine.book("GOOG")


class TestSubmitThroughEngine:
    def test_submit_and_match(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            "AAPL", "B1", Side.SELL, 100, 10, document_number="11111111100"
        )
        report = engine.submit_limit_order(
            "AAPL", "B2", Side.BUY, 100, 10, document_number="22222222200"
        )
        assert len(report.trades) == 1
        assert report.accepted_order.status == OrderStatus.FILLED

    def test_no_cross_symbol_matching(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            "AAPL", "B1", Side.SELL, 100, 10, document_number="11111111100"
        )
        report = engine.submit_limit_order(
            "GOOG", "B2", Side.BUY, 100, 10, document_number="22222222200"
        )
        assert len(report.trades) == 0
        assert report.accepted_order.status == OrderStatus.OPEN


class TestIndependentSnapshots:
    def test_snapshots_are_independent(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            "AAPL", "B1", Side.BUY, 100, 5, document_number="11111111100"
        )
        engine.submit_limit_order(
            "GOOG", "B1", Side.SELL, 200, 3, document_number="11111111100"
        )
        aapl_snap = engine.snapshot("AAPL")
        goog_snap = engine.snapshot("GOOG")
        assert aapl_snap == {
            "bids": [{"price": 100, "quantity": 5}],
            "asks": [],
        }
        assert goog_snap == {
            "bids": [],
            "asks": [{"price": 200, "quantity": 3}],
        }


class TestIndependentOrderIds:
    def test_auto_ids_per_symbol(self, engine: MatchingEngine) -> None:
        r1 = engine.submit_limit_order(
            "AAPL", "B1", Side.BUY, 100, 5, document_number="11111111100"
        )
        r2 = engine.submit_limit_order(
            "GOOG", "B1", Side.BUY, 100, 5, document_number="11111111100"
        )
        assert r1.accepted_order.order_id == "AAPL-1"
        assert r2.accepted_order.order_id == "GOOG-1"


class TestCancelThroughEngine:
    def test_cancel_existing_order(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            "AAPL",
            "B1",
            Side.BUY,
            100,
            10,
            order_id="X1",
            document_number="11111111100",
        )
        assert engine.cancel_order("AAPL", "X1") is True

    def test_cancel_unknown_order(self, engine: MatchingEngine) -> None:
        engine.submit_limit_order(
            "AAPL", "B1", Side.BUY, 100, 10, document_number="11111111100"
        )
        assert engine.cancel_order("AAPL", "nope") is False

    def test_cancel_unknown_symbol(self, engine: MatchingEngine) -> None:
        assert engine.cancel_order("NOPE", "X1") is False
