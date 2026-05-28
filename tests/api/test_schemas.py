"""Tests for API schemas."""

from datetime import UTC, datetime, timezone

import pytest
from pydantic import ValidationError

from mini_exchange.api.schemas import (
    ApiOrderSide,
    ApiOrderStatus,
    ErrorResponse,
    OrderResponse,
    SubmitOrderRequest,
    TradeResponse,
)
from mini_exchange.orderbook.models import Side


def _valid_request(**kwargs: object) -> SubmitOrderRequest:
    """Build a valid SubmitOrderRequest, overriding with kwargs."""
    defaults: dict[str, object] = {
        "document_number": "DOC-123",
        "side": "BID",
        "valid_until": "2030-01-01T00:00:00Z",
        "symbol": "AAPL",
        "price": 100,
        "quantity": 10,
    }
    defaults.update(kwargs)
    return SubmitOrderRequest.model_validate(defaults)


class TestValidSubmitOrderRequest:
    def test_valid_minimal(self) -> None:
        req = _valid_request()
        assert req.document_number == "DOC-123"
        assert req.side == ApiOrderSide.BID
        assert req.symbol == "AAPL"
        assert req.price == 100
        assert req.quantity == 10
        assert req.client_order_id is None

    def test_valid_with_client_order_id(self) -> None:
        req = _valid_request(client_order_id="my-order-1")
        assert req.client_order_id == "my-order-1"


class TestSymbolNormalization:
    def test_uppercase_normalization(self) -> None:
        req = _valid_request(symbol="aapl")
        assert req.symbol == "AAPL"

    def test_strip_whitespace(self) -> None:
        req = _valid_request(symbol="  goog  ")
        assert req.symbol == "GOOG"


class TestValidUntil:
    def test_timezone_aware_normalized_to_utc(self) -> None:
        eastern = timezone(
            offset=datetime.now(tz=UTC).utcoffset()
            or __import__("datetime").timedelta(hours=-5)
        )
        from datetime import timedelta

        eastern = timezone(timedelta(hours=-5))
        dt = datetime(2030, 6, 15, 12, 0, 0, tzinfo=eastern)
        req = _valid_request(valid_until=dt.isoformat())
        assert req.valid_until.tzinfo == UTC
        assert req.valid_until == dt.astimezone(UTC)

    def test_naive_datetime_rejected(self) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            _valid_request(valid_until="2030-01-01T00:00:00")


class TestDocumentNumberValidation:
    def test_empty_rejected(self) -> None:
        with pytest.raises(ValidationError, match="document_number"):
            _valid_request(document_number="")

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValidationError, match="empty or whitespace"):
            _valid_request(document_number="   ")

    def test_invalid_characters_rejected(self) -> None:
        with pytest.raises(ValidationError, match="invalid characters"):
            _valid_request(document_number="DOC@#$")

    def test_valid_characters_accepted(self) -> None:
        req = _valid_request(document_number="A1.B-2/C")
        assert req.document_number == "A1.B-2/C"


class TestClientOrderIdValidation:
    def test_missing_accepted_as_none(self) -> None:
        req = _valid_request()
        assert req.client_order_id is None

    def test_explicit_null_accepted_as_none(self) -> None:
        req = _valid_request(client_order_id=None)
        assert req.client_order_id is None

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(ValidationError, match="empty or whitespace"):
            _valid_request(client_order_id="")

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValidationError, match="empty or whitespace"):
            _valid_request(client_order_id="   ")

    def test_valid_value_trimmed(self) -> None:
        req = _valid_request(client_order_id="  my-order-1  ")
        assert req.client_order_id == "my-order-1"

    def test_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError, match="at most 128"):
            _valid_request(client_order_id="x" * 129)

    def test_too_long_after_trim_rejected(self) -> None:
        with pytest.raises(ValidationError, match="at most 128"):
            _valid_request(client_order_id="  " + "x" * 129 + "  ")


class TestSymbolValidation:
    def test_empty_rejected(self) -> None:
        with pytest.raises(ValidationError, match="symbol"):
            _valid_request(symbol="")

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValidationError, match="empty or whitespace"):
            _valid_request(symbol="   ")

    def test_invalid_characters_rejected(self) -> None:
        with pytest.raises(ValidationError, match="invalid characters"):
            _valid_request(symbol="AA@PL")


class TestPriceValidation:
    @pytest.mark.parametrize("value", [0, -1, -100])
    def test_non_positive_rejected(self, value: int) -> None:
        with pytest.raises(ValidationError, match="price"):
            _valid_request(price=value)

    def test_float_rejected(self) -> None:
        with pytest.raises(ValidationError, match="price"):
            _valid_request(price=10.5)


class TestQuantityValidation:
    @pytest.mark.parametrize("value", [0, -1, -100])
    def test_non_positive_rejected(self, value: int) -> None:
        with pytest.raises(ValidationError, match="quantity"):
            _valid_request(quantity=value)

    def test_float_rejected(self) -> None:
        with pytest.raises(ValidationError, match="quantity"):
            _valid_request(quantity=5.5)


class TestExtraFieldsRejected:
    def test_submit_request_extra_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            _valid_request(unexpected_field="bad")


class TestSideMapping:
    def test_bid_to_core_buy(self) -> None:
        assert ApiOrderSide.BID.to_core_side() == Side.BUY

    def test_ask_to_core_sell(self) -> None:
        assert ApiOrderSide.ASK.to_core_side() == Side.SELL

    def test_from_core_buy(self) -> None:
        assert ApiOrderSide.from_core_side(Side.BUY) == ApiOrderSide.BID

    def test_from_core_sell(self) -> None:
        assert ApiOrderSide.from_core_side(Side.SELL) == ApiOrderSide.ASK


class TestApiOrderStatus:
    def test_values_exist(self) -> None:
        assert ApiOrderStatus.OPEN == "OPEN"
        assert ApiOrderStatus.PARTIALLY_FILLED == "PARTIALLY_FILLED"
        assert ApiOrderStatus.FILLED == "FILLED"
        assert ApiOrderStatus.CANCELED == "CANCELED"
        assert ApiOrderStatus.EXPIRED == "EXPIRED"


class TestTradeResponse:
    def test_creation(self) -> None:
        trade = TradeResponse(
            trade_id="T1",
            sequence=1,
            symbol="AAPL",
            buyer_order_id="B1",
            seller_order_id="S1",
            buyer_broker_id="BR1",
            seller_broker_id="BR2",
            price=100,
            quantity=5,
        )
        assert trade.trade_id == "T1"
        assert trade.price == 100


class TestOrderResponse:
    def test_creation(self) -> None:
        trade = TradeResponse(
            trade_id="T1",
            sequence=1,
            symbol="AAPL",
            buyer_order_id="B1",
            seller_order_id="S1",
            buyer_broker_id="BR1",
            seller_broker_id="BR2",
            price=100,
            quantity=5,
        )
        order = OrderResponse(
            order_id="O1",
            broker_id="BR1",
            client_order_id=None,
            document_number="DOC-1",
            side=ApiOrderSide.BID,
            symbol="AAPL",
            price=100,
            quantity=10,
            remaining_quantity=5,
            filled_quantity=5,
            status=ApiOrderStatus.PARTIALLY_FILLED,
            valid_until=datetime(2030, 1, 1, tzinfo=UTC),
            trades=(trade,),
        )
        assert order.order_id == "O1"
        assert order.filled_quantity == 5
        assert len(order.trades) == 1


class TestErrorResponse:
    def test_creation(self) -> None:
        err = ErrorResponse(code="INVALID_ORDER", message="Price too low")
        assert err.code == "INVALID_ORDER"
        assert err.message == "Price too low"
