"""Tests for order book invariant validation."""

import pytest

from mini_exchange.orderbook import InvariantViolationError, OrderBook, Side
from mini_exchange.orderbook.models import Order, OrderStatus, Trade
from tests.customer_documents import CUST_111, CUST_222, CUST_SHARED


@pytest.fixture
def book() -> OrderBook:
    return OrderBook("AAPL")


@pytest.fixture
def checked_book() -> OrderBook:
    return OrderBook("AAPL", check_invariants=True)


class TestInvariantsPassValidScenarios:
    def test_pass_after_complex_matching(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, document_number="11111111100", order_id="S1"
        )
        book.submit_limit_order(
            "B2", Side.SELL, 101, 5, document_number="22222222200", order_id="S2"
        )
        book.submit_limit_order("B3", Side.BUY, 100, 8, document_number="33333333300")
        book.submit_limit_order("B4", Side.BUY, 99, 5, document_number="44444444400")
        book.validate_invariants()

    def test_pass_after_cancellation(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100", order_id="Bid1"
        )
        book.cancel_order("Bid1")
        book.validate_invariants()


class TestCheckInvariantsFlag:
    def test_auto_check_after_submit(self, checked_book: OrderBook) -> None:
        checked_book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100"
        )
        checked_book.submit_limit_order(
            "B2", Side.SELL, 110, 5, document_number="22222222200"
        )

    def test_auto_check_after_cancel(self, checked_book: OrderBook) -> None:
        checked_book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100", order_id="X"
        )
        checked_book.cancel_order("X")

    def test_cancel_returns_false_no_check(self, checked_book: OrderBook) -> None:
        assert checked_book.cancel_order("missing") is False


class TestOrderInvariantViolations:
    def test_wrong_symbol_detected(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100", order_id="Bid1"
        )
        order = book.get_order("Bid1")
        assert order is not None
        object.__setattr__(order, "symbol", "WRONG")
        with pytest.raises(InvariantViolationError, match="wrong symbol"):
            book.validate_invariants()

    def test_negative_remaining_detected(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100", order_id="Bid1"
        )
        order = book.get_order("Bid1")
        assert order is not None
        object.__setattr__(order, "remaining", -1)
        with pytest.raises(InvariantViolationError, match="negative remaining"):
            book.validate_invariants()

    def test_filled_with_nonzero_remaining(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100", order_id="Bid1"
        )
        order = book.get_order("Bid1")
        assert order is not None
        object.__setattr__(order, "status", OrderStatus.FILLED)
        with pytest.raises(InvariantViolationError, match="FILLED but remaining != 0"):
            book.validate_invariants()

    def test_active_with_zero_remaining(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.BUY, 100, 10, document_number="11111111100", order_id="Bid1"
        )
        order = book.get_order("Bid1")
        assert order is not None
        object.__setattr__(order, "remaining", 0)
        with pytest.raises(InvariantViolationError, match="active but remaining <= 0"):
            book.validate_invariants()


class TestCrossedBookDetection:
    def test_crossed_book_detected(self, book: OrderBook) -> None:
        book.submit_limit_order("B1", Side.BUY, 100, 10, document_number="11111111100")
        book.submit_limit_order("B2", Side.SELL, 110, 5, document_number="22222222200")
        crossed_order = Order(
            order_id="FAKE",
            broker_id="X",
            document_number=CUST_111,
            symbol="AAPL",
            side=Side.SELL,
            price=90,
            quantity=5,
            sequence=99,
        )
        book._orders["FAKE"] = crossed_order
        book._asks.add(crossed_order)
        with pytest.raises(InvariantViolationError, match="book is crossed"):
            book.validate_invariants()


class TestTradeInvariantViolations:
    def test_trade_price_mismatch_detected(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, document_number="11111111100", order_id="S1"
        )
        book.submit_limit_order(
            "B2", Side.BUY, 100, 10, document_number="22222222200", order_id="Buy1"
        )
        bad_trade = Trade(
            trade_id="AAPL-T1",
            sequence=1,
            symbol="AAPL",
            buyer_order_id="Buy1",
            seller_order_id="S1",
            buyer_broker_id="B2",
            seller_broker_id="B1",
            price=999,
            quantity=10,
        )
        book._trades[0] = bad_trade
        with pytest.raises(InvariantViolationError, match="!= seller price"):
            book.validate_invariants()

    def test_trade_nonpositive_price_detected(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, document_number="11111111100", order_id="S1"
        )
        book.submit_limit_order(
            "B2", Side.BUY, 100, 10, document_number="22222222200", order_id="Buy1"
        )
        bad_trade = Trade(
            trade_id="BAD",
            sequence=1,
            symbol="AAPL",
            buyer_order_id="Buy1",
            seller_order_id="S1",
            buyer_broker_id="B2",
            seller_broker_id="B1",
            price=100,
            quantity=10,
        )
        book._trades[0] = bad_trade
        object.__setattr__(book._trades[0], "price", 0)
        with pytest.raises(InvariantViolationError, match="non-positive price"):
            book.validate_invariants()

    def test_trade_nonpositive_quantity_detected(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, document_number="11111111100", order_id="S1"
        )
        book.submit_limit_order(
            "B2", Side.BUY, 100, 10, document_number="22222222200", order_id="Buy1"
        )
        bad_trade = Trade(
            trade_id="BAD",
            sequence=1,
            symbol="AAPL",
            buyer_order_id="Buy1",
            seller_order_id="S1",
            buyer_broker_id="B2",
            seller_broker_id="B1",
            price=100,
            quantity=10,
        )
        book._trades[0] = bad_trade
        object.__setattr__(book._trades[0], "quantity", 0)
        with pytest.raises(InvariantViolationError, match="non-positive quantity"):
            book.validate_invariants()

    def test_trade_unknown_buyer_detected(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, document_number="11111111100", order_id="S1"
        )
        book.submit_limit_order(
            "B2", Side.BUY, 100, 10, document_number="22222222200", order_id="Buy1"
        )
        bad_trade = Trade(
            trade_id="BAD",
            sequence=1,
            symbol="AAPL",
            buyer_order_id="UNKNOWN",
            seller_order_id="S1",
            buyer_broker_id="B2",
            seller_broker_id="B1",
            price=100,
            quantity=10,
        )
        book._trades[0] = bad_trade
        with pytest.raises(InvariantViolationError, match="unknown buyer"):
            book.validate_invariants()

    def test_trade_unknown_seller_detected(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, document_number="11111111100", order_id="S1"
        )
        book.submit_limit_order(
            "B2", Side.BUY, 100, 10, document_number="22222222200", order_id="Buy1"
        )
        bad_trade = Trade(
            trade_id="BAD",
            sequence=1,
            symbol="AAPL",
            buyer_order_id="Buy1",
            seller_order_id="UNKNOWN",
            buyer_broker_id="B2",
            seller_broker_id="B1",
            price=100,
            quantity=10,
        )
        book._trades[0] = bad_trade
        with pytest.raises(InvariantViolationError, match="unknown seller"):
            book.validate_invariants()

    def test_trade_buyer_wrong_side_detected(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, document_number="11111111100", order_id="S1"
        )
        book.submit_limit_order(
            "B2", Side.BUY, 100, 10, document_number="22222222200", order_id="Buy1"
        )
        bad_trade = Trade(
            trade_id="BAD",
            sequence=1,
            symbol="AAPL",
            buyer_order_id="S1",
            seller_order_id="S1",
            buyer_broker_id="B1",
            seller_broker_id="B1",
            price=100,
            quantity=10,
        )
        book._trades[0] = bad_trade
        with pytest.raises(InvariantViolationError, match="buyer has wrong side"):
            book.validate_invariants()

    def test_trade_seller_wrong_side_detected(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, document_number="11111111100", order_id="S1"
        )
        book.submit_limit_order(
            "B2", Side.BUY, 100, 10, document_number="22222222200", order_id="Buy1"
        )
        bad_trade = Trade(
            trade_id="BAD",
            sequence=1,
            symbol="AAPL",
            buyer_order_id="Buy1",
            seller_order_id="Buy1",
            buyer_broker_id="B2",
            seller_broker_id="B2",
            price=100,
            quantity=10,
        )
        book._trades[0] = bad_trade
        with pytest.raises(InvariantViolationError, match="seller has wrong side"):
            book.validate_invariants()

    def test_trade_same_document_number_detected(self, book: OrderBook) -> None:
        book.submit_limit_order(
            "B1", Side.SELL, 100, 10, order_id="S1", document_number=CUST_111
        )
        book.submit_limit_order(
            "B2", Side.BUY, 100, 10, order_id="Buy1", document_number=CUST_222
        )
        bad_trade = Trade(
            trade_id="BAD",
            sequence=1,
            symbol="AAPL",
            buyer_order_id="Buy1",
            seller_order_id="S1",
            buyer_broker_id="B2",
            seller_broker_id="B1",
            price=100,
            quantity=10,
        )
        object.__setattr__(book._orders["Buy1"], "document_number", CUST_SHARED)
        object.__setattr__(book._orders["S1"], "document_number", CUST_SHARED)
        book._trades[0] = bad_trade
        with pytest.raises(InvariantViolationError, match="same document_number"):
            book.validate_invariants()
