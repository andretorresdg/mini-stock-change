"""Multi-symbol matching engine router."""

from __future__ import annotations

from mini_exchange.orderbook.models import ExecutionReport, Side
from mini_exchange.orderbook.order_book import OrderBook


class MatchingEngine:
    """Routes orders to per-symbol OrderBook instances."""

    __slots__ = ("_books",)

    def __init__(self) -> None:
        self._books: dict[str, OrderBook] = {}

    def book(self, symbol: str) -> OrderBook:
        """Get or lazily create an OrderBook for the given symbol."""
        if symbol not in self._books:
            self._books[symbol] = OrderBook(symbol)
        return self._books[symbol]

    def submit_limit_order(
        self,
        symbol: str,
        broker_id: str,
        side: Side,
        price: int,
        quantity: int,
        order_id: str | None = None,
        document_number: str | None = None,
    ) -> ExecutionReport:
        """Route a limit order to the appropriate symbol book."""
        return self.book(symbol).submit_limit_order(
            broker_id=broker_id,
            side=side,
            price=price,
            quantity=quantity,
            order_id=order_id,
            document_number=document_number,
        )

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order on the given symbol book."""
        if symbol not in self._books:
            return False
        return self._books[symbol].cancel_order(order_id)

    def snapshot(
        self, symbol: str, depth: int | None = None
    ) -> dict[str, list[dict[str, int]]]:
        """Return the snapshot for a given symbol."""
        return self.book(symbol).snapshot(depth=depth)
