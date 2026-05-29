"""Side book: one side (BUY or SELL) of an order book."""

from __future__ import annotations

import heapq
from collections import deque

from mini_exchange.orderbook.models import Order, Side


class SideBook:
    """Manages price levels and FIFO ordering for one side of the book."""

    __slots__ = ("_heap", "_levels", "_side")

    def __init__(self, side: Side) -> None:
        self._side = side
        self._levels: dict[int, deque[Order]] = {}
        self._heap: list[int] = []

    def add(self, order: Order) -> None:
        """Add an active order to the book."""
        if order.side != self._side:
            msg = f"expected {self._side.value} order, got {order.side.value}"
            raise ValueError(msg)
        if not order.is_active:
            msg = "cannot add an inactive order"
            raise ValueError(msg)
        price = order.price
        if price not in self._levels:
            self._levels[price] = deque()
            heap_key = -price if self._side == Side.BUY else price
            heapq.heappush(self._heap, heap_key)
        self._levels[price].append(order)

    def best_price(self) -> int | None:
        """Return the best price, lazily discarding stale levels."""
        while self._heap:
            raw = self._heap[0]
            price = -raw if self._side == Side.BUY else raw
            level = self._levels.get(price)
            if level is None:
                heapq.heappop(self._heap)
                continue
            self._clean_inactive_head(level)
            if level:
                return price
            del self._levels[price]
            heapq.heappop(self._heap)
        return None

    def peek_best_order(self) -> Order | None:
        """Return the best-priority order without removing it."""
        price = self.best_price()
        if price is None:
            return None
        level = self._levels[price]
        return level[0]

    def discard_inactive_head(self, price: int) -> None:
        """Remove inactive orders from the front of a price level."""
        level = self._levels.get(price)
        if level is None:
            return
        self._clean_inactive_head(level)
        if not level:
            del self._levels[price]

    def find_matchable_order(self, incoming: Order) -> Order | None:
        """Return the best-priority resting order that crosses and is not self-trade."""
        # Self-trade prevention uses customer document_number, not broker_id.
        # The same customer may route orders through different brokers.
        for price in self._active_prices_best_first():
            level = self._levels[price]
            first_active = next((o for o in level if o.is_active), None)
            if first_active is None:
                continue
            if not _prices_cross(incoming, first_active):
                break
            for order in level:
                if not order.is_active:
                    continue
                if order.document_number == incoming.document_number:
                    continue
                if _prices_cross(incoming, order):
                    return order
        return None

    def purge_inactive(self, price: int) -> None:
        """Remove all inactive orders from a price level."""
        level = self._levels.get(price)
        if level is None:
            return
        while level and not level[0].is_active:
            level.popleft()
        if not level:
            del self._levels[price]

    def snapshot_levels(self) -> list[dict[str, int]]:
        """Aggregate remaining active quantity by price level."""
        result: list[dict[str, int]] = []
        for price, level in self._levels.items():
            total = sum(o.remaining for o in level if o.is_active)
            if total > 0:
                result.append({"price": price, "quantity": total})
        if self._side == Side.BUY:
            result.sort(key=lambda x: x["price"], reverse=True)
        else:
            result.sort(key=lambda x: x["price"])
        return result

    def _active_prices_best_first(self) -> list[int]:
        """Return price levels with active orders, best price first."""
        prices: list[int] = []
        for price, level in self._levels.items():
            self._clean_inactive_head(level)
            if level:
                prices.append(price)
        if self._side == Side.BUY:
            prices.sort(reverse=True)
        else:
            prices.sort()
        return prices

    @staticmethod
    def _clean_inactive_head(level: deque[Order]) -> None:
        """Remove inactive orders from the front of a deque."""
        while level and not level[0].is_active:
            level.popleft()


def _prices_cross(incoming: Order, resting: Order) -> bool:
    """Check whether incoming and resting orders have compatible prices."""
    if incoming.side == Side.BUY:
        return incoming.price >= resting.price
    return resting.price >= incoming.price
