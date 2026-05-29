"""Deterministic replay regression tests for the order book."""

from mini_exchange.orderbook import MatchingEngine, OrderBook, OrderStatus, Side
from tests.customer_documents import doc_for

Command = tuple[str, ...]


def build_commands() -> list[Command]:
    """Command sequence exercising core matching scenarios."""
    return [
        # Resting BUY orders
        ("submit", "B1", "BUY", "100", "10", "bid1"),
        ("submit", "B2", "BUY", "99", "5", "bid2"),
        # Resting SELL orders
        ("submit", "B3", "SELL", "105", "8", "ask1"),
        ("submit", "B4", "SELL", "110", "3", "ask2"),
        # Same-price match: SELL at 100 matches bid1
        ("submit", "B5", "SELL", "100", "4", "sell_match"),
        # Price-gap match: BUY at 106 crosses ask1 at 105
        ("submit", "B6", "BUY", "106", "3", "buy_cross"),
        # Partial fill: BUY at 105 takes remaining 5 from ask1
        ("submit", "B7", "BUY", "105", "12", "buy_partial"),
        # Multi-fill and FIFO: add two sells at same price, buy takes both
        ("submit", "B8", "SELL", "95", "4", "fifo1"),
        ("submit", "B9", "SELL", "95", "6", "fifo2"),
        ("submit", "B10", "BUY", "95", "7", "buy_fifo"),
        # Cancellation
        ("cancel", "bid2"),
        # Order after cancel (won't match canceled bid2)
        ("submit", "B11", "SELL", "99", "3", "sell_no_match"),
    ]


def apply_commands(book: OrderBook, commands: list[Command]) -> None:
    """Apply a command sequence to a book."""
    for cmd in commands:
        if cmd[0] == "submit":
            _, broker, side_str, price, qty, oid = cmd
            side = Side.BUY if side_str == "BUY" else Side.SELL
            book.submit_limit_order(
                broker_id=broker,
                side=side,
                price=int(price),
                quantity=int(qty),
                order_id=oid,
                document_number=doc_for(broker),
            )
        elif cmd[0] == "cancel":
            book.cancel_order(cmd[1])


def snapshot_state(book: OrderBook, commands: list[Command]) -> dict[str, object]:
    """Capture full deterministic state of a book after replay."""
    order_ids: list[str] = []
    statuses: list[str] = []
    remainings: list[int] = []
    for cmd in commands:
        if cmd[0] == "submit":
            oid = cmd[5]
            order_ids.append(oid)
            order = book.get_order(oid)
            assert order is not None
            statuses.append(order.status.value)
            remainings.append(order.remaining)
    trades = book.trades
    trade_ids = [t.trade_id for t in trades]
    trade_seqs = [t.sequence for t in trades]
    trade_prices = [t.price for t in trades]
    trade_qtys = [t.quantity for t in trades]
    return {
        "snapshot": book.snapshot(),
        "order_ids": order_ids,
        "statuses": statuses,
        "remainings": remainings,
        "trade_ids": trade_ids,
        "trade_seqs": trade_seqs,
        "trade_prices": trade_prices,
        "trade_qtys": trade_qtys,
    }


class TestDeterministicReplay:
    def test_identical_replay_produces_identical_state(self) -> None:
        commands = build_commands()
        book_a = OrderBook("SYM")
        book_b = OrderBook("SYM")
        apply_commands(book_a, commands)
        apply_commands(book_b, commands)
        state_a = snapshot_state(book_a, commands)
        state_b = snapshot_state(book_b, commands)
        assert state_a == state_b

    def test_replay_state_values(self) -> None:
        """Verify specific expected values to guard against regressions."""
        commands = build_commands()
        book = OrderBook("SYM")
        apply_commands(book, commands)
        state = snapshot_state(book, commands)
        # bid1: filled by sell_match(4) + fifo2(3) + sell_no_match(3) = 10
        assert state["statuses"][0] == "FILLED"
        assert state["remainings"][0] == 0
        # bid2 was canceled
        assert state["statuses"][1] == "CANCELED"
        assert state["remainings"][1] == 5
        # ask1: filled by buy_cross(3) + buy_partial(5) = 8
        assert state["statuses"][2] == "FILLED"
        assert state["remainings"][2] == 0
        # ask2: never matched, still open
        assert state["statuses"][3] == "OPEN"
        assert state["remainings"][3] == 3
        # buy_partial: filled 5(ask1) + 4(fifo1) + 3(fifo2) = 12
        assert state["statuses"][6] == "FILLED"
        assert state["remainings"][6] == 0
        # fifo1 fully filled (4), fifo2 fully filled (3+3=6)
        assert state["statuses"][7] == "FILLED"
        assert state["statuses"][8] == "FILLED"
        # buy_fifo: no match, rests
        assert state["statuses"][9] == "OPEN"
        assert state["remainings"][9] == 7
        # 7 trades total
        assert len(state["trade_ids"]) == 7
        # Trade sequences are strictly monotonic
        seqs = state["trade_seqs"]
        assert seqs == sorted(seqs)
        assert len(set(seqs)) == len(seqs)

    def test_replay_trade_ids_are_deterministic(self) -> None:
        commands = build_commands()
        book = OrderBook("SYM")
        apply_commands(book, commands)
        trades = book.trades
        for i, trade in enumerate(trades, start=1):
            assert trade.trade_id == f"SYM-T{i}"


class TestDeterministicEngineReplay:
    def test_multi_symbol_deterministic_replay(self) -> None:
        commands_aapl: list[Command] = [
            ("submit", "B1", "SELL", "150", "10", "A-S1"),
            ("submit", "B2", "BUY", "150", "5", "A-B1"),
            ("submit", "B3", "BUY", "149", "8", "A-B2"),
            ("cancel", "A-B2"),
        ]
        commands_goog: list[Command] = [
            ("submit", "B1", "BUY", "200", "20", "G-B1"),
            ("submit", "B2", "SELL", "200", "15", "G-S1"),
            ("submit", "B3", "SELL", "199", "5", "G-S2"),
        ]
        engine_a = MatchingEngine()
        engine_b = MatchingEngine()
        for eng in (engine_a, engine_b):
            for cmd in commands_aapl:
                if cmd[0] == "submit":
                    _, broker, side_str, price, qty, oid = cmd
                    side = Side.BUY if side_str == "BUY" else Side.SELL
                    eng.submit_limit_order(
                        "AAPL",
                        broker,
                        side,
                        int(price),
                        int(qty),
                        oid,
                        document_number=doc_for(broker),
                    )
                elif cmd[0] == "cancel":
                    eng.cancel_order("AAPL", cmd[1])
            for cmd in commands_goog:
                if cmd[0] == "submit":
                    _, broker, side_str, price, qty, oid = cmd
                    side = Side.BUY if side_str == "BUY" else Side.SELL
                    eng.submit_limit_order(
                        "GOOG",
                        broker,
                        side,
                        int(price),
                        int(qty),
                        oid,
                        document_number=doc_for(broker),
                    )
                elif cmd[0] == "cancel":
                    eng.cancel_order("GOOG", cmd[1])
        # Compare snapshots
        assert engine_a.snapshot("AAPL") == engine_b.snapshot("AAPL")
        assert engine_a.snapshot("GOOG") == engine_b.snapshot("GOOG")
        # Compare trade histories
        aapl_a = engine_a.book("AAPL").trades
        aapl_b = engine_b.book("AAPL").trades
        assert aapl_a == aapl_b
        goog_a = engine_a.book("GOOG").trades
        goog_b = engine_b.book("GOOG").trades
        assert goog_a == goog_b
        # Symbols are independent
        assert engine_a.snapshot("AAPL") != engine_a.snapshot("GOOG")
        # Verify AAPL state
        aapl_book = engine_a.book("AAPL")
        assert aapl_book.get_order("A-B2") is not None
        assert aapl_book.get_order("A-B2").status == OrderStatus.CANCELED  # type: ignore[union-attr]
        assert aapl_book.best_ask() == 150
        # Verify GOOG state: B1 had 20, matched 15+5=20 => filled
        goog_book = engine_a.book("GOOG")
        assert goog_book.get_order("G-B1") is not None
        assert goog_book.get_order("G-B1").status == OrderStatus.FILLED  # type: ignore[union-attr]
