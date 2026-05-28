"""Tests for order book domain models."""

import pytest

from mini_exchange.orderbook import ExecutionReport, Order, OrderStatus, Side, Trade

# --- Order creation ---


def make_order(**kwargs: object) -> Order:
    """Create a default valid order, overriding with kwargs."""
    defaults: dict[str, object] = {
        "order_id": "O1",
        "broker_id": "B1",
        "symbol": "AAPL",
        "side": Side.BUY,
        "price": 100,
        "quantity": 10,
        "sequence": 1,
    }
    defaults.update(kwargs)
    return Order(**defaults)  # type: ignore[arg-type]


class TestOrderCreation:
    def test_valid_order(self) -> None:
        order = make_order()
        assert order.order_id == "O1"
        assert order.broker_id == "B1"
        assert order.symbol == "AAPL"
        assert order.side == Side.BUY
        assert order.price == 100
        assert order.quantity == 10
        assert order.sequence == 1
        assert order.remaining == 10
        assert order.status == OrderStatus.OPEN

    @pytest.mark.parametrize(
        ("field", "value", "error"),
        [
            ("order_id", "", "order_id must be non-empty"),
            ("broker_id", "", "broker_id must be non-empty"),
            ("symbol", "", "symbol must be non-empty"),
            ("price", 0, "price must be a positive integer"),
            ("price", -1, "price must be a positive integer"),
            ("quantity", 0, "quantity must be a positive integer"),
            ("quantity", -5, "quantity must be a positive integer"),
            ("sequence", 0, "sequence must be a positive integer"),
            ("sequence", -1, "sequence must be a positive integer"),
        ],
    )
    def test_invalid_order_value_error(
        self, field: str, value: object, error: str
    ) -> None:
        with pytest.raises(ValueError, match=error):
            make_order(**{field: value})

    def test_invalid_side_type(self) -> None:
        with pytest.raises(TypeError, match="side must be a valid Side"):
            make_order(side="BUY")


# --- Order properties ---


class TestOrderProperties:
    def test_filled_quantity_initially_zero(self) -> None:
        order = make_order()
        assert order.filled_quantity == 0

    def test_filled_quantity_after_partial_fill(self) -> None:
        order = make_order(quantity=10)
        order.apply_fill(3)
        assert order.filled_quantity == 3

    def test_is_active_when_open(self) -> None:
        order = make_order()
        assert order.is_active is True

    def test_is_active_when_partially_filled(self) -> None:
        order = make_order(quantity=10)
        order.apply_fill(5)
        assert order.is_active is True

    def test_is_active_when_filled(self) -> None:
        order = make_order(quantity=10)
        order.apply_fill(10)
        assert order.is_active is False

    def test_is_active_when_canceled(self) -> None:
        order = make_order()
        order.cancel()
        assert order.is_active is False


# --- Order.apply_fill ---


class TestApplyFill:
    def test_partial_fill(self) -> None:
        order = make_order(quantity=10)
        order.apply_fill(4)
        assert order.remaining == 6
        assert order.status == OrderStatus.PARTIALLY_FILLED

    def test_full_fill(self) -> None:
        order = make_order(quantity=10)
        order.apply_fill(10)
        assert order.remaining == 0
        assert order.status == OrderStatus.FILLED

    def test_multiple_fills_to_completion(self) -> None:
        order = make_order(quantity=10)
        order.apply_fill(3)
        order.apply_fill(7)
        assert order.remaining == 0
        assert order.status == OrderStatus.FILLED

    @pytest.mark.parametrize("qty", [0, -1])
    def test_non_positive_fill_rejected(self, qty: int) -> None:
        order = make_order(quantity=10)
        with pytest.raises(
            ValueError, match="fill quantity must be a positive integer"
        ):
            order.apply_fill(qty)

    def test_overfill_rejected(self) -> None:
        order = make_order(quantity=10)
        with pytest.raises(
            ValueError, match="fill quantity exceeds remaining quantity"
        ):
            order.apply_fill(11)

    def test_fill_after_filled_rejected(self) -> None:
        order = make_order(quantity=10)
        order.apply_fill(10)
        with pytest.raises(ValueError, match="cannot fill an inactive order"):
            order.apply_fill(1)

    def test_fill_after_canceled_rejected(self) -> None:
        order = make_order(quantity=10)
        order.cancel()
        with pytest.raises(ValueError, match="cannot fill an inactive order"):
            order.apply_fill(1)


# --- Order.cancel ---


class TestCancel:
    def test_cancel_open_order(self) -> None:
        order = make_order()
        result = order.cancel()
        assert result is True
        assert order.status == OrderStatus.CANCELED

    def test_cancel_partially_filled_order(self) -> None:
        order = make_order(quantity=10)
        order.apply_fill(3)
        result = order.cancel()
        assert result is True
        assert order.status == OrderStatus.CANCELED

    def test_cancel_already_canceled(self) -> None:
        order = make_order()
        order.cancel()
        result = order.cancel()
        assert result is False

    def test_cancel_filled_order(self) -> None:
        order = make_order(quantity=10)
        order.apply_fill(10)
        result = order.cancel()
        assert result is False


# --- Trade ---


def make_trade(**kwargs: object) -> Trade:
    """Create a default valid trade, overriding with kwargs."""
    defaults: dict[str, object] = {
        "trade_id": "T1",
        "sequence": 1,
        "symbol": "AAPL",
        "buyer_order_id": "O1",
        "seller_order_id": "O2",
        "buyer_broker_id": "B1",
        "seller_broker_id": "B2",
        "price": 100,
        "quantity": 5,
    }
    defaults.update(kwargs)
    return Trade(**defaults)  # type: ignore[arg-type]


class TestTradeCreation:
    def test_valid_trade(self) -> None:
        trade = make_trade()
        assert trade.trade_id == "T1"
        assert trade.sequence == 1
        assert trade.symbol == "AAPL"
        assert trade.buyer_order_id == "O1"
        assert trade.seller_order_id == "O2"
        assert trade.buyer_broker_id == "B1"
        assert trade.seller_broker_id == "B2"
        assert trade.price == 100
        assert trade.quantity == 5

    @pytest.mark.parametrize(
        ("field", "value", "error"),
        [
            ("trade_id", "", "trade_id must be non-empty"),
            ("sequence", 0, "sequence must be a positive integer"),
            ("sequence", -1, "sequence must be a positive integer"),
            ("symbol", "", "symbol must be non-empty"),
            ("buyer_order_id", "", "buyer_order_id must be non-empty"),
            ("seller_order_id", "", "seller_order_id must be non-empty"),
            ("buyer_broker_id", "", "buyer_broker_id must be non-empty"),
            ("seller_broker_id", "", "seller_broker_id must be non-empty"),
            ("price", 0, "price must be a positive integer"),
            ("price", -1, "price must be a positive integer"),
            ("quantity", 0, "quantity must be a positive integer"),
            ("quantity", -1, "quantity must be a positive integer"),
        ],
    )
    def test_invalid_trade(self, field: str, value: object, error: str) -> None:
        with pytest.raises(ValueError, match=error):
            make_trade(**{field: value})

    def test_trade_is_frozen(self) -> None:
        trade = make_trade()
        with pytest.raises(AttributeError):
            trade.price = 200  # type: ignore[misc]


# --- ExecutionReport ---


class TestExecutionReport:
    def test_creation(self) -> None:
        order = make_order()
        trade = make_trade()
        report = ExecutionReport(accepted_order=order, trades=(trade,))
        assert report.accepted_order is order
        assert report.trades == (trade,)

    def test_empty_trades(self) -> None:
        order = make_order()
        report = ExecutionReport(accepted_order=order, trades=())
        assert report.trades == ()

    def test_report_is_frozen(self) -> None:
        order = make_order()
        report = ExecutionReport(accepted_order=order, trades=())
        with pytest.raises(AttributeError):
            report.trades = ()  # type: ignore[misc]
