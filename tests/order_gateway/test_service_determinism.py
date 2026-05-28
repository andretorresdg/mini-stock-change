"""Tests proving the Order Gateway produces deterministic results."""

import threading
from datetime import UTC, datetime, timedelta

from mini_exchange.order_gateway.errors import GatewayStateError
from mini_exchange.order_gateway.models import (
    GatewaySubmitOrder,
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


def _build_scenario() -> list[GatewaySubmitOrder]:
    """Build a diverse scenario exercising various matching paths."""
    return [
        GatewaySubmitOrder(
            broker_id="seller1",
            document_number="D1",
            client_order_id=None,
            side=Side.SELL,
            valid_until=_FUTURE,
            symbol="AAPL",
            price=100,
            quantity=10,
        ),
        GatewaySubmitOrder(
            broker_id="buyer1",
            document_number="D2",
            client_order_id=None,
            side=Side.BUY,
            valid_until=_FUTURE,
            symbol="MSFT",
            price=50,
            quantity=20,
        ),
        GatewaySubmitOrder(
            broker_id="buyer2",
            document_number="D3",
            client_order_id=None,
            side=Side.BUY,
            valid_until=_FUTURE,
            symbol="AAPL",
            price=100,
            quantity=10,
        ),
        GatewaySubmitOrder(
            broker_id="buyer3",
            document_number="D4",
            client_order_id=None,
            side=Side.BUY,
            valid_until=_FUTURE,
            symbol="AAPL",
            price=110,
            quantity=5,
        ),
        GatewaySubmitOrder(
            broker_id="seller2",
            document_number="D5",
            client_order_id=None,
            side=Side.SELL,
            valid_until=_FUTURE,
            symbol="AAPL",
            price=105,
            quantity=8,
        ),
        GatewaySubmitOrder(
            broker_id="seller3",
            document_number="D6",
            client_order_id=None,
            side=Side.SELL,
            valid_until=_FUTURE,
            symbol="AAPL",
            price=100,
            quantity=3,
        ),
        GatewaySubmitOrder(
            broker_id="seller3",
            document_number="D6",
            client_order_id=None,
            side=Side.SELL,
            valid_until=_FUTURE,
            symbol="AAPL",
            price=100,
            quantity=3,
        ),
        GatewaySubmitOrder(
            broker_id="idem-broker",
            document_number="D7",
            client_order_id="c1",
            side=Side.BUY,
            valid_until=_FUTURE,
            symbol="AAPL",
            price=100,
            quantity=5,
        ),
        GatewaySubmitOrder(
            broker_id="idem-broker",
            document_number="D7",
            client_order_id="c1",
            side=Side.BUY,
            valid_until=_FUTURE,
            symbol="AAPL",
            price=100,
            quantity=5,
        ),
        GatewaySubmitOrder(
            broker_id="expiring-seller",
            document_number="D8",
            client_order_id=None,
            side=Side.SELL,
            valid_until=_SHORT,
            symbol="TSLA",
            price=200,
            quantity=10,
        ),
    ]


def _run_scenario(
    clock: _MutableClock,
) -> tuple[list[object], tuple[object, ...]]:
    svc = OrderGatewayService(clock=clock)
    results = []
    scenario = _build_scenario()
    for req in scenario:
        result = svc.submit_order(req)
        results.append(
            (
                result.order_id,
                result.status,
                result.remaining_quantity,
                result.filled_quantity,
                tuple((t.trade_id, t.price, t.quantity) for t in result.trades),
            )
        )
    clock.now = _NOW + timedelta(minutes=10)
    svc.get_order("expiring-seller", "TSLA-O-9")
    svc.validate_invariants()
    return results, svc.command_log()


class TestDeterministicReplay:
    def test_two_identical_runs_produce_same_results(self) -> None:
        clock1 = _MutableClock(_NOW)
        clock2 = _MutableClock(_NOW)
        results1, _log1 = _run_scenario(clock1)
        results2, _log2 = _run_scenario(clock2)
        assert results1 == results2

    def test_two_identical_runs_produce_same_command_log(self) -> None:
        clock1 = _MutableClock(_NOW)
        clock2 = _MutableClock(_NOW)
        _, log1 = _run_scenario(clock1)
        _, log2 = _run_scenario(clock2)
        assert log1 == log2

    def test_scenario_includes_expected_behaviors(self) -> None:
        clock = _MutableClock(_NOW)
        results, _log = _run_scenario(clock)
        statuses = [r[1] for r in results]
        from mini_exchange.order_gateway.models import GatewayOrderStatus

        assert GatewayOrderStatus.OPEN in statuses
        assert GatewayOrderStatus.FILLED in statuses
        assert GatewayOrderStatus.PARTIALLY_FILLED in statuses


class TestConcurrencySafety:
    def test_concurrent_submits_no_duplicates(self) -> None:
        svc = OrderGatewayService(clock=lambda: _NOW)
        results: list[str] = []
        errors: list[Exception] = []

        def submit(idx: int) -> None:
            try:
                req = GatewaySubmitOrder(
                    broker_id=f"broker{idx}",
                    document_number=f"D{idx}",
                    client_order_id=None,
                    side=Side.BUY,
                    valid_until=_FUTURE,
                    symbol="AAPL",
                    price=100,
                    quantity=1,
                )
                result = svc.submit_order(req)
                results.append(result.order_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=submit, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 20
        assert len(set(results)) == 20

    def test_concurrent_command_sequences_contiguous(self) -> None:
        svc = OrderGatewayService(clock=lambda: _NOW)

        def submit(idx: int) -> None:
            req = GatewaySubmitOrder(
                broker_id=f"broker{idx}",
                document_number=f"D{idx}",
                client_order_id=None,
                side=Side.BUY,
                valid_until=_FUTURE,
                symbol="AAPL",
                price=100,
                quantity=1,
            )
            svc.submit_order(req)

        threads = [threading.Thread(target=submit, args=(i,)) for i in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        log = svc.command_log()
        seqs = [cmd.command_sequence for cmd in log]
        assert seqs == list(range(1, 16))

    def test_invariants_hold_after_concurrent_submits(self) -> None:
        svc = OrderGatewayService(clock=lambda: _NOW)

        def submit(idx: int) -> None:
            req = GatewaySubmitOrder(
                broker_id=f"broker{idx}",
                document_number=f"D{idx}",
                client_order_id=None,
                side=Side.BUY if idx % 2 == 0 else Side.SELL,
                valid_until=_FUTURE,
                symbol="AAPL",
                price=100,
                quantity=5,
            )
            svc.submit_order(req)

        threads = [threading.Thread(target=submit, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        svc.validate_invariants()


class TestValidateInvariantsCorrupted:
    def test_non_increasing_sequences_detected(self) -> None:
        import pytest

        svc = OrderGatewayService(clock=lambda: _NOW)
        req = GatewaySubmitOrder(
            broker_id="b",
            document_number="D",
            client_order_id=None,
            side=Side.BUY,
            valid_until=_FUTURE,
            symbol="X",
            price=1,
            quantity=1,
        )
        svc.submit_order(req)
        svc._command_log[0] = svc._command_log[0]
        from mini_exchange.order_gateway.models import (
            GatewayCommandType,
            SubmitOrderCommand,
        )

        fake_cmd = SubmitOrderCommand(
            command_sequence=1,
            received_at=_NOW,
            command_type=GatewayCommandType.SUBMIT_ORDER,
            broker_id="b",
            document_number="D",
            client_order_id=None,
            order_id="FAKE-O-1",
            side=Side.BUY,
            valid_until=_FUTURE,
            symbol="X",
            price=1,
            quantity=1,
        )
        svc._command_log.append(fake_cmd)
        with pytest.raises(GatewayStateError, match="strictly increasing"):
            svc.validate_invariants()

    def test_idempotency_index_unknown_order_detected(self) -> None:
        import pytest

        svc = OrderGatewayService(clock=lambda: _NOW)
        svc._idempotency_index[("b", "c1")] = ((), "NONEXISTENT")
        with pytest.raises(GatewayStateError, match="unknown order"):
            svc.validate_invariants()

    def test_metadata_unknown_core_order_detected(self) -> None:
        import pytest

        from mini_exchange.order_gateway.models import OrderMetadata

        svc = OrderGatewayService(clock=lambda: _NOW)
        svc._metadata_by_order_id["GHOST-1"] = OrderMetadata(
            order_id="GHOST-1",
            broker_id="b",
            document_number="D",
            client_order_id=None,
            side=Side.BUY,
            valid_until=_FUTURE,
            symbol="AAPL",
            price=1,
            quantity=1,
        )
        with pytest.raises(GatewayStateError, match="unknown core order"):
            svc.validate_invariants()
