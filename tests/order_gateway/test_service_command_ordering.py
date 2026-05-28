"""Tests for command ordering invariants in the Order Gateway."""

from datetime import UTC, datetime, timedelta

from mini_exchange.order_gateway.models import (
    ExpireOrderCommand,
    GatewaySubmitOrder,
    SubmitOrderCommand,
)
from mini_exchange.order_gateway.service import OrderGatewayService
from mini_exchange.orderbook.models import Side

_NOW = datetime(2030, 6, 15, 12, 0, 0, tzinfo=UTC)
_FUTURE = _NOW + timedelta(hours=1)
_SHORT = _NOW + timedelta(minutes=5)


class _MutableClock:
    def __init__(self, at: datetime = _NOW) -> None:
        self.now = at

    def __call__(self) -> datetime:
        return self.now


def _service(clock: _MutableClock | None = None) -> OrderGatewayService:
    return OrderGatewayService(clock=clock or _MutableClock())


def _ask(**kwargs: object) -> GatewaySubmitOrder:
    defaults: dict[str, object] = {
        "broker_id": "seller",
        "document_number": "DS",
        "client_order_id": None,
        "side": Side.SELL,
        "valid_until": _FUTURE,
        "symbol": "AAPL",
        "price": 100,
        "quantity": 10,
    }
    defaults.update(kwargs)
    return GatewaySubmitOrder(**defaults)  # type: ignore[arg-type]


def _bid(**kwargs: object) -> GatewaySubmitOrder:
    defaults: dict[str, object] = {
        "broker_id": "buyer",
        "document_number": "DB",
        "client_order_id": None,
        "side": Side.BUY,
        "valid_until": _FUTURE,
        "symbol": "AAPL",
        "price": 100,
        "quantity": 10,
    }
    defaults.update(kwargs)
    return GatewaySubmitOrder(**defaults)  # type: ignore[arg-type]


class TestStrictlyIncreasingSequences:
    def test_command_sequences_strictly_increase(self) -> None:
        svc = _service()
        svc.submit_order(_ask(broker_id="s1"))
        svc.submit_order(_ask(broker_id="s2"))
        svc.submit_order(_bid(broker_id="b1"))
        svc.submit_order(_bid(broker_id="b2"))
        log = svc.command_log()
        seqs = [cmd.command_sequence for cmd in log]
        for i in range(1, len(seqs)):
            assert seqs[i] > seqs[i - 1]


class TestSubmitCommandsInAcceptanceOrder:
    def test_submits_ordered_by_acceptance(self) -> None:
        svc = _service()
        svc.submit_order(_ask(broker_id="s1", symbol="AAPL"))
        svc.submit_order(_bid(broker_id="b1", symbol="MSFT"))
        svc.submit_order(_ask(broker_id="s2", symbol="TSLA"))
        log = svc.command_log()
        submit_cmds = [c for c in log if isinstance(c, SubmitOrderCommand)]
        assert submit_cmds[0].symbol == "AAPL"
        assert submit_cmds[1].symbol == "MSFT"
        assert submit_cmds[2].symbol == "TSLA"


class TestExpirationBeforeSubmit:
    def test_expiration_commands_precede_triggering_submit(self) -> None:
        clock = _MutableClock(_NOW)
        svc = _service(clock)
        svc.submit_order(_ask(valid_until=_SHORT, broker_id="s1"))
        svc.submit_order(_bid(valid_until=_SHORT, broker_id="b1", price=50))
        clock.now = _NOW + timedelta(minutes=10)
        svc.submit_order(_ask(broker_id="s2", valid_until=_NOW + timedelta(hours=2)))
        log = svc.command_log()
        last_submit_idx = max(
            i for i, c in enumerate(log) if isinstance(c, SubmitOrderCommand)
        )
        expire_indices = [
            i for i, c in enumerate(log) if isinstance(c, ExpireOrderCommand)
        ]
        for idx in expire_indices:
            assert idx < last_submit_idx


class TestIdempotentRetryNoCommand:
    def test_idempotent_retry_does_not_append_command(self) -> None:
        svc = _service()
        req = _bid(client_order_id="c1")
        svc.submit_order(req)
        initial_len = len(svc.command_log())
        svc.submit_order(req)
        assert len(svc.command_log()) == initial_len


class TestNoApiDependencyInGateway:
    def test_no_fastapi_or_pydantic_in_service_module(self) -> None:
        import inspect

        import mini_exchange.order_gateway.service as mod

        source = inspect.getsource(mod)
        assert "fastapi" not in source.lower()
        assert "pydantic" not in source.lower()

    def test_no_api_imports_in_order_gateway_package(self) -> None:
        import inspect

        import mini_exchange.order_gateway as pkg

        source = inspect.getsource(pkg)
        assert "mini_exchange.api" not in source
