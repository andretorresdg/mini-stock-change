"""Tests for order gateway command factory."""

from datetime import UTC, datetime, timedelta

import pytest

from mini_exchange.order_gateway.command_factory import OrderCommandFactory
from mini_exchange.order_gateway.errors import ExpiredOrderError, InvalidBrokerError
from mini_exchange.order_gateway.models import (
    GatewayCommandType,
    GatewaySubmitOrder,
)
from mini_exchange.order_gateway.sequencer import MonotonicSequencer
from mini_exchange.orderbook.models import Side

_NOW = datetime(2030, 6, 15, 12, 0, 0, tzinfo=UTC)


def _fake_clock(at: datetime = _NOW) -> datetime:
    return at


def _make_factory(
    now: datetime = _NOW,
) -> OrderCommandFactory:
    return OrderCommandFactory(
        command_sequencer=MonotonicSequencer(),
        order_id_sequencer=MonotonicSequencer(),
        clock=lambda: now,
    )


def _valid_request(**overrides: object) -> GatewaySubmitOrder:
    defaults = {
        "broker_id": "broker1",
        "document_number": "DOC-1",
        "client_order_id": "c1",
        "side": Side.BUY,
        "valid_until": _NOW + timedelta(hours=1),
        "symbol": "AAPL",
        "price": 100,
        "quantity": 10,
    }
    defaults.update(overrides)
    return GatewaySubmitOrder(**defaults)  # type: ignore[arg-type]


class TestCreateSubmitOrderCommand:
    def test_valid_creation(self) -> None:
        factory = _make_factory()
        req = _valid_request()
        cmd = factory.create_submit_order_command(req)

        assert cmd.command_type == GatewayCommandType.SUBMIT_ORDER
        assert cmd.broker_id == "broker1"
        assert cmd.order_id == "AAPL-O-1"
        assert cmd.received_at == _NOW
        assert cmd.symbol == "AAPL"
        assert cmd.price == 100
        assert cmd.quantity == 10

    def test_received_at_from_clock(self) -> None:
        custom_time = datetime(2025, 3, 1, 8, 0, 0, tzinfo=UTC)
        factory = _make_factory(now=custom_time)
        req = _valid_request(valid_until=custom_time + timedelta(minutes=5))
        cmd = factory.create_submit_order_command(req)
        assert cmd.received_at == custom_time

    def test_invalid_broker_rejected(self) -> None:
        factory = _make_factory()
        req = _valid_request(broker_id="bad broker!")
        with pytest.raises(InvalidBrokerError):
            factory.create_submit_order_command(req)

    def test_valid_until_in_future_accepted(self) -> None:
        factory = _make_factory()
        req = _valid_request(valid_until=_NOW + timedelta(seconds=1))
        cmd = factory.create_submit_order_command(req)
        assert cmd.valid_until == _NOW + timedelta(seconds=1)

    def test_valid_until_equal_to_now_rejected(self) -> None:
        factory = _make_factory()
        req = _valid_request(valid_until=_NOW)
        with pytest.raises(ExpiredOrderError, match="expired"):
            factory.create_submit_order_command(req)

    def test_valid_until_before_now_rejected(self) -> None:
        factory = _make_factory()
        req = _valid_request(valid_until=_NOW - timedelta(seconds=1))
        with pytest.raises(ExpiredOrderError, match="expired"):
            factory.create_submit_order_command(req)

    def test_command_sequence_increments(self) -> None:
        factory = _make_factory()
        r1 = _valid_request(client_order_id="c1")
        r2 = _valid_request(client_order_id="c2")
        cmd1 = factory.create_submit_order_command(r1)
        cmd2 = factory.create_submit_order_command(r2)
        assert cmd1.command_sequence == 1
        assert cmd2.command_sequence == 2

    def test_order_id_sequence_increments(self) -> None:
        factory = _make_factory()
        r1 = _valid_request(client_order_id="c1")
        r2 = _valid_request(client_order_id="c2")
        cmd1 = factory.create_submit_order_command(r1)
        cmd2 = factory.create_submit_order_command(r2)
        assert cmd1.order_id == "AAPL-O-1"
        assert cmd2.order_id == "AAPL-O-2"


class TestCreateExpireOrderCommand:
    def test_valid_creation(self) -> None:
        factory = _make_factory()
        cmd = factory.create_expire_order_command(
            order_id="AAPL-O-1",
            symbol="AAPL",
            reason="validity window elapsed",
        )
        assert cmd.command_type == GatewayCommandType.EXPIRE_ORDER
        assert cmd.order_id == "AAPL-O-1"
        assert cmd.symbol == "AAPL"
        assert cmd.reason == "validity window elapsed"
        assert cmd.received_at == _NOW

    def test_command_sequence_shared_with_submit(self) -> None:
        factory = _make_factory()
        req = _valid_request()
        submit_cmd = factory.create_submit_order_command(req)
        expire_cmd = factory.create_expire_order_command(
            order_id="AAPL-O-1",
            symbol="AAPL",
            reason="expired",
        )
        assert submit_cmd.command_sequence == 1
        assert expire_cmd.command_sequence == 2
