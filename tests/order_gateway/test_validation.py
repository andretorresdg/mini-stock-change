"""Tests for order gateway validation helpers."""

from datetime import UTC, datetime

import pytest

from mini_exchange.order_gateway.errors import InvalidBrokerError
from mini_exchange.order_gateway.models import GatewaySubmitOrder
from mini_exchange.order_gateway.validation import (
    build_submit_fingerprint,
    make_order_id,
    validate_broker_id,
)
from mini_exchange.orderbook.models import Side


class TestValidateBrokerId:
    @pytest.mark.parametrize(
        "broker_id",
        ["broker1", "a", "A.B-C_D", "x" * 64, "123"],
    )
    def test_valid_ids_pass(self, broker_id: str) -> None:
        validate_broker_id(broker_id)

    @pytest.mark.parametrize(
        "broker_id",
        ["", "   ", "\t"],
    )
    def test_empty_or_whitespace_rejected(self, broker_id: str) -> None:
        with pytest.raises(InvalidBrokerError, match="empty or whitespace"):
            validate_broker_id(broker_id)

    def test_too_long_rejected(self) -> None:
        with pytest.raises(InvalidBrokerError, match="at most 64"):
            validate_broker_id("x" * 65)

    @pytest.mark.parametrize(
        "broker_id",
        ["broker id", "bro!ker", "bro@ker", "bro/ker", "bro ker"],
    )
    def test_invalid_characters_rejected(self, broker_id: str) -> None:
        with pytest.raises(InvalidBrokerError, match="invalid characters"):
            validate_broker_id(broker_id)


class TestMakeOrderId:
    def test_basic_format(self) -> None:
        assert make_order_id("AAPL", 1) == "AAPL-O-1"

    def test_symbol_normalized_to_uppercase(self) -> None:
        assert make_order_id("aapl", 42) == "AAPL-O-42"

    def test_symbol_stripped(self) -> None:
        assert make_order_id("  msft  ", 3) == "MSFT-O-3"

    def test_empty_symbol_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            make_order_id("", 1)

    def test_whitespace_symbol_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            make_order_id("   ", 1)

    @pytest.mark.parametrize("seq", [0, -1])
    def test_non_positive_sequence_rejected(self, seq: int) -> None:
        with pytest.raises(ValueError, match="positive integer"):
            make_order_id("X", seq)


class TestBuildSubmitFingerprint:
    def _make_request(self, **overrides: object) -> GatewaySubmitOrder:
        defaults = {
            "broker_id": "broker1",
            "document_number": "DOC-1",
            "client_order_id": "c1",
            "side": Side.BUY,
            "valid_until": datetime(2030, 1, 1, tzinfo=UTC),
            "symbol": "AAPL",
            "price": 100,
            "quantity": 10,
        }
        defaults.update(overrides)
        return GatewaySubmitOrder(**defaults)  # type: ignore[arg-type]

    def test_deterministic(self) -> None:
        req = self._make_request()
        assert build_submit_fingerprint(req) == build_submit_fingerprint(req)

    def test_same_request_same_fingerprint(self) -> None:
        r1 = self._make_request()
        r2 = self._make_request()
        assert build_submit_fingerprint(r1) == build_submit_fingerprint(r2)

    def test_different_price_different_fingerprint(self) -> None:
        r1 = self._make_request(price=100)
        r2 = self._make_request(price=200)
        assert build_submit_fingerprint(r1) != build_submit_fingerprint(r2)

    def test_different_side_different_fingerprint(self) -> None:
        r1 = self._make_request(side=Side.BUY)
        r2 = self._make_request(side=Side.SELL)
        assert build_submit_fingerprint(r1) != build_submit_fingerprint(r2)

    def test_different_quantity_different_fingerprint(self) -> None:
        r1 = self._make_request(quantity=10)
        r2 = self._make_request(quantity=20)
        assert build_submit_fingerprint(r1) != build_submit_fingerprint(r2)

    def test_different_symbol_different_fingerprint(self) -> None:
        r1 = self._make_request(symbol="AAPL")
        r2 = self._make_request(symbol="MSFT")
        assert build_submit_fingerprint(r1) != build_submit_fingerprint(r2)

    def test_different_client_order_id_different_fingerprint(self) -> None:
        r1 = self._make_request(client_order_id="c1")
        r2 = self._make_request(client_order_id="c2")
        assert build_submit_fingerprint(r1) != build_submit_fingerprint(r2)

    def test_fingerprint_includes_all_fields(self) -> None:
        req = self._make_request()
        fp = build_submit_fingerprint(req)
        assert len(fp) == 8
