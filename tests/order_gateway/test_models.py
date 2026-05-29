"""Tests for order gateway models."""

from datetime import UTC, datetime

import pytest

from mini_exchange.order_gateway.models import (
    ExpireOrderCommand,
    GatewayCommandType,
    GatewayOrder,
    GatewayOrderStatus,
    GatewaySubmitOrder,
    GatewayTrade,
    OrderMetadata,
    SubmitOrderCommand,
)
from mini_exchange.orderbook.models import Side

_VALID_DT = datetime(2030, 1, 1, tzinfo=UTC)


# --- GatewaySubmitOrder ---


class TestGatewaySubmitOrderValid:
    def test_valid_creation(self) -> None:
        dto = GatewaySubmitOrder(
            broker_id="broker1",
            document_number="DOC-1",
            client_order_id=None,
            side=Side.BUY,
            valid_until=_VALID_DT,
            symbol="aapl",
            price=100,
            quantity=10,
        )
        assert dto.symbol == "AAPL"
        assert dto.valid_until.tzinfo == UTC

    def test_symbol_normalization(self) -> None:
        dto = GatewaySubmitOrder(
            broker_id="b",
            document_number="D",
            client_order_id=None,
            side=Side.SELL,
            valid_until=_VALID_DT,
            symbol="  msft  ",
            price=1,
            quantity=1,
        )
        assert dto.symbol == "MSFT"

    def test_timezone_normalization(self) -> None:
        dt = datetime(2030, 6, 1, 15, 0, 0, tzinfo=UTC)
        dto = GatewaySubmitOrder(
            broker_id="b",
            document_number="D",
            client_order_id=None,
            side=Side.BUY,
            valid_until=dt,
            symbol="X",
            price=1,
            quantity=1,
        )
        assert dto.valid_until.tzinfo == UTC


class TestGatewaySubmitOrderRejections:
    def test_naive_datetime_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            GatewaySubmitOrder(
                broker_id="b",
                document_number="D",
                client_order_id=None,
                side=Side.BUY,
                valid_until=datetime(2030, 1, 1),
                symbol="X",
                price=1,
                quantity=1,
            )

    @pytest.mark.parametrize("field", ["broker_id", "document_number", "symbol"])
    def test_empty_string_rejected(self, field: str) -> None:
        kwargs = {
            "broker_id": "b",
            "document_number": "D",
            "client_order_id": None,
            "side": Side.BUY,
            "valid_until": _VALID_DT,
            "symbol": "X",
            "price": 1,
            "quantity": 1,
        }
        kwargs[field] = "   "
        with pytest.raises(ValueError, match="must not be empty"):
            GatewaySubmitOrder(**kwargs)

    @pytest.mark.parametrize("val", [0, -1])
    def test_non_positive_price_rejected(self, val: int) -> None:
        with pytest.raises(ValueError, match="positive integer"):
            GatewaySubmitOrder(
                broker_id="b",
                document_number="D",
                client_order_id=None,
                side=Side.BUY,
                valid_until=_VALID_DT,
                symbol="X",
                price=val,
                quantity=1,
            )

    def test_float_price_rejected(self) -> None:
        with pytest.raises(TypeError, match="positive integer"):
            GatewaySubmitOrder(
                broker_id="b",
                document_number="D",
                client_order_id=None,
                side=Side.BUY,
                valid_until=_VALID_DT,
                symbol="X",
                price=1.5,  # type: ignore[arg-type]
                quantity=1,
            )

    @pytest.mark.parametrize("val", [0, -1])
    def test_non_positive_quantity_rejected(self, val: int) -> None:
        with pytest.raises(ValueError, match="positive integer"):
            GatewaySubmitOrder(
                broker_id="b",
                document_number="D",
                client_order_id=None,
                side=Side.BUY,
                valid_until=_VALID_DT,
                symbol="X",
                price=1,
                quantity=val,
            )

    def test_float_quantity_rejected(self) -> None:
        with pytest.raises(TypeError, match="positive integer"):
            GatewaySubmitOrder(
                broker_id="b",
                document_number="D",
                client_order_id=None,
                side=Side.BUY,
                valid_until=_VALID_DT,
                symbol="X",
                price=1,
                quantity=2.0,  # type: ignore[arg-type]
            )

    def test_invalid_side_rejected(self) -> None:
        with pytest.raises(TypeError, match="valid Side"):
            GatewaySubmitOrder(
                broker_id="b",
                document_number="D",
                client_order_id=None,
                side="BUY",  # type: ignore[arg-type]
                valid_until=_VALID_DT,
                symbol="X",
                price=1,
                quantity=1,
            )


# --- SubmitOrderCommand ---


class TestSubmitOrderCommand:
    def test_valid_creation(self) -> None:
        cmd = SubmitOrderCommand(
            command_sequence=1,
            received_at=_VALID_DT,
            command_type=GatewayCommandType.SUBMIT_ORDER,
            broker_id="b",
            document_number="D",
            client_order_id=None,
            order_id="ORD-1",
            side=Side.BUY,
            valid_until=_VALID_DT,
            symbol="aapl",
            price=100,
            quantity=10,
        )
        assert cmd.command_type == GatewayCommandType.SUBMIT_ORDER
        assert cmd.symbol == "AAPL"

    def test_wrong_command_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="SUBMIT_ORDER"):
            SubmitOrderCommand(
                command_sequence=1,
                received_at=_VALID_DT,
                command_type=GatewayCommandType.EXPIRE_ORDER,
                broker_id="b",
                document_number="D",
                client_order_id=None,
                order_id="ORD-1",
                side=Side.BUY,
                valid_until=_VALID_DT,
                symbol="X",
                price=1,
                quantity=1,
            )

    def test_invalid_command_sequence(self) -> None:
        with pytest.raises(ValueError, match="positive integer"):
            SubmitOrderCommand(
                command_sequence=0,
                received_at=_VALID_DT,
                command_type=GatewayCommandType.SUBMIT_ORDER,
                broker_id="b",
                document_number="D",
                client_order_id=None,
                order_id="ORD-1",
                side=Side.BUY,
                valid_until=_VALID_DT,
                symbol="X",
                price=1,
                quantity=1,
            )

    def test_empty_order_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            SubmitOrderCommand(
                command_sequence=1,
                received_at=_VALID_DT,
                command_type=GatewayCommandType.SUBMIT_ORDER,
                broker_id="b",
                document_number="D",
                client_order_id=None,
                order_id="",
                side=Side.BUY,
                valid_until=_VALID_DT,
                symbol="X",
                price=1,
                quantity=1,
            )

    def test_naive_received_at_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            SubmitOrderCommand(
                command_sequence=1,
                received_at=datetime(2030, 1, 1),
                command_type=GatewayCommandType.SUBMIT_ORDER,
                broker_id="b",
                document_number="D",
                client_order_id=None,
                order_id="ORD-1",
                side=Side.BUY,
                valid_until=_VALID_DT,
                symbol="X",
                price=1,
                quantity=1,
            )

    def test_invalid_side_rejected(self) -> None:
        with pytest.raises(TypeError, match="valid Side"):
            SubmitOrderCommand(
                command_sequence=1,
                received_at=_VALID_DT,
                command_type=GatewayCommandType.SUBMIT_ORDER,
                broker_id="b",
                document_number="D",
                client_order_id=None,
                order_id="ORD-1",
                side="BUY",  # type: ignore[arg-type]
                valid_until=_VALID_DT,
                symbol="X",
                price=1,
                quantity=1,
            )


# --- ExpireOrderCommand ---


class TestExpireOrderCommand:
    def test_valid_creation(self) -> None:
        cmd = ExpireOrderCommand(
            command_sequence=5,
            received_at=_VALID_DT,
            command_type=GatewayCommandType.EXPIRE_ORDER,
            order_id="ORD-1",
            symbol="aapl",
            reason="validity window elapsed",
        )
        assert cmd.command_type == GatewayCommandType.EXPIRE_ORDER
        assert cmd.symbol == "AAPL"

    def test_wrong_command_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="EXPIRE_ORDER"):
            ExpireOrderCommand(
                command_sequence=1,
                received_at=_VALID_DT,
                command_type=GatewayCommandType.SUBMIT_ORDER,
                order_id="ORD-1",
                symbol="X",
                reason="test",
            )

    def test_invalid_command_sequence(self) -> None:
        with pytest.raises(ValueError, match="positive integer"):
            ExpireOrderCommand(
                command_sequence=-1,
                received_at=_VALID_DT,
                command_type=GatewayCommandType.EXPIRE_ORDER,
                order_id="ORD-1",
                symbol="X",
                reason="test",
            )

    def test_empty_reason_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            ExpireOrderCommand(
                command_sequence=1,
                received_at=_VALID_DT,
                command_type=GatewayCommandType.EXPIRE_ORDER,
                order_id="ORD-1",
                symbol="X",
                reason="",
            )

    def test_naive_received_at_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            ExpireOrderCommand(
                command_sequence=1,
                received_at=datetime(2030, 1, 1),
                command_type=GatewayCommandType.EXPIRE_ORDER,
                order_id="ORD-1",
                symbol="X",
                reason="test",
            )


# --- OrderMetadata ---


class TestOrderMetadata:
    def test_valid_creation(self) -> None:
        meta = OrderMetadata(
            order_id="ORD-1",
            broker_id="b",
            document_number="D",
            client_order_id="c1",
            side=Side.SELL,
            valid_until=_VALID_DT,
            symbol="aapl",
            price=50,
            quantity=100,
        )
        assert meta.symbol == "AAPL"
        assert meta.status_override is None

    def test_status_override_mutable(self) -> None:
        meta = OrderMetadata(
            order_id="ORD-1",
            broker_id="b",
            document_number="D",
            client_order_id=None,
            side=Side.BUY,
            valid_until=_VALID_DT,
            symbol="X",
            price=1,
            quantity=1,
        )
        meta.status_override = GatewayOrderStatus.EXPIRED
        assert meta.status_override == GatewayOrderStatus.EXPIRED

    def test_empty_order_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            OrderMetadata(
                order_id="",
                broker_id="b",
                document_number="D",
                client_order_id=None,
                side=Side.BUY,
                valid_until=_VALID_DT,
                symbol="X",
                price=1,
                quantity=1,
            )

    def test_invalid_side_rejected(self) -> None:
        with pytest.raises(TypeError, match="valid Side"):
            OrderMetadata(
                order_id="ORD-1",
                broker_id="b",
                document_number="D",
                client_order_id=None,
                side="SELL",  # type: ignore[arg-type]
                valid_until=_VALID_DT,
                symbol="X",
                price=1,
                quantity=1,
            )


# --- GatewayTrade ---


class TestGatewayTrade:
    def test_valid_creation(self) -> None:
        trade = GatewayTrade(
            trade_id="T-1",
            sequence=1,
            symbol="AAPL",
            buyer_order_id="B-1",
            seller_order_id="S-1",
            buyer_broker_id="bb",
            seller_broker_id="sb",
            price=100,
            quantity=10,
        )
        assert trade.trade_id == "T-1"

    def test_empty_trade_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            GatewayTrade(
                trade_id="",
                sequence=1,
                symbol="X",
                buyer_order_id="B",
                seller_order_id="S",
                buyer_broker_id="bb",
                seller_broker_id="sb",
                price=1,
                quantity=1,
            )


# --- GatewayOrder ---


class TestGatewayOrder:
    def test_valid_creation(self) -> None:
        order = GatewayOrder(
            order_id="ORD-1",
            broker_id="b",
            document_number="D",
            client_order_id=None,
            side=Side.BUY,
            symbol="AAPL",
            price=100,
            quantity=10,
            remaining_quantity=5,
            filled_quantity=5,
            status=GatewayOrderStatus.PARTIALLY_FILLED,
            valid_until=_VALID_DT,
            trades=(),
        )
        assert order.remaining_quantity + order.filled_quantity == 10

    def test_negative_remaining_rejected(self) -> None:
        with pytest.raises(ValueError, match="remaining_quantity"):
            GatewayOrder(
                order_id="ORD-1",
                broker_id="b",
                document_number="D",
                client_order_id=None,
                side=Side.BUY,
                symbol="X",
                price=1,
                quantity=10,
                remaining_quantity=-1,
                filled_quantity=5,
                status=GatewayOrderStatus.OPEN,
                valid_until=_VALID_DT,
                trades=(),
            )

    def test_negative_filled_rejected(self) -> None:
        with pytest.raises(ValueError, match="filled_quantity"):
            GatewayOrder(
                order_id="ORD-1",
                broker_id="b",
                document_number="D",
                client_order_id=None,
                side=Side.BUY,
                symbol="X",
                price=1,
                quantity=10,
                remaining_quantity=5,
                filled_quantity=-1,
                status=GatewayOrderStatus.OPEN,
                valid_until=_VALID_DT,
                trades=(),
            )

    def test_inconsistent_quantities_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not exceed quantity"):
            GatewayOrder(
                order_id="ORD-1",
                broker_id="b",
                document_number="D",
                client_order_id=None,
                side=Side.BUY,
                symbol="X",
                price=1,
                quantity=10,
                remaining_quantity=8,
                filled_quantity=5,
                status=GatewayOrderStatus.OPEN,
                valid_until=_VALID_DT,
                trades=(),
            )

    def test_naive_valid_until_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            GatewayOrder(
                order_id="ORD-1",
                broker_id="b",
                document_number="D",
                client_order_id=None,
                side=Side.BUY,
                symbol="X",
                price=1,
                quantity=10,
                remaining_quantity=10,
                filled_quantity=0,
                status=GatewayOrderStatus.OPEN,
                valid_until=datetime(2030, 1, 1),
                trades=(),
            )
