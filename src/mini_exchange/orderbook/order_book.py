"""Single-symbol deterministic limit order book."""

from __future__ import annotations

from mini_exchange.orderbook.models import ExecutionReport, Order, Side, Trade
from mini_exchange.orderbook.side_book import SideBook


class OrderBook:
    """Deterministic limit order book for a single symbol."""

    __slots__ = (
        "_asks",
        "_bids",
        "_order_seq",
        "_orders",
        "_symbol",
        "_trade_seq",
        "_trades",
    )

    def __init__(self, symbol: str) -> None:
        if not symbol:
            msg = "symbol must be non-empty"
            raise ValueError(msg)
        self._symbol = symbol
        self._bids = SideBook(Side.BUY)
        self._asks = SideBook(Side.SELL)
        self._orders: dict[str, Order] = {}
        self._trades: list[Trade] = []
        self._order_seq = 0
        self._trade_seq = 0

    @property
    def trades(self) -> tuple[Trade, ...]:
        """All trades executed on this book."""
        return tuple(self._trades)

    def get_order(self, order_id: str) -> Order | None:
        """Look up an order by ID."""
        return self._orders.get(order_id)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID. Returns True if successfully canceled."""
        order = self._orders.get(order_id)
        if order is None:
            return False
        return order.cancel()

    def best_bid(self) -> int | None:
        """Best (highest) bid price."""
        return self._bids.best_price()

    def best_ask(self) -> int | None:
        """Best (lowest) ask price."""
        return self._asks.best_price()

    def snapshot(self, depth: int | None = None) -> dict[str, list[dict[str, int]]]:
        """Return aggregated price levels for both sides."""
        bids = self._bids.snapshot_levels()
        asks = self._asks.snapshot_levels()
        if depth is not None:
            bids = bids[:depth]
            asks = asks[:depth]
        return {"bids": bids, "asks": asks}

    def submit_limit_order(
        self,
        broker_id: str,
        side: Side,
        price: int,
        quantity: int,
        order_id: str | None = None,
    ) -> ExecutionReport:
        """Submit a limit order, match it, and return an execution report."""
        self._order_seq += 1
        if order_id is None:
            order_id = f"{self._symbol}-{self._order_seq}"
        if order_id in self._orders:
            msg = f"duplicate order_id: {order_id}"
            raise ValueError(msg)
        order = Order(
            order_id=order_id,
            broker_id=broker_id,
            symbol=self._symbol,
            side=side,
            price=price,
            quantity=quantity,
            sequence=self._order_seq,
        )
        self._orders[order_id] = order
        trades = self._match(order)
        if order.is_active:
            book = self._bids if side == Side.BUY else self._asks
            book.add(order)
        return ExecutionReport(accepted_order=order, trades=tuple(trades))

    def _match(self, order: Order) -> list[Trade]:
        """Match an incoming order against the opposite side."""
        trades: list[Trade] = []
        opposite = self._asks if order.side == Side.BUY else self._bids
        while order.remaining > 0:
            resting = opposite.peek_best_order()
            if resting is None:
                break
            if not self._prices_cross(order, resting):
                break
            fill_qty = min(order.remaining, resting.remaining)
            if order.side == Side.BUY:
                buyer, seller = order, resting
            else:
                buyer, seller = resting, order
            fill_price = seller.price
            order.apply_fill(fill_qty)
            resting.apply_fill(fill_qty)
            opposite.discard_inactive_head(resting.price)
            self._trade_seq += 1
            trade = Trade(
                trade_id=f"{self._symbol}-T{self._trade_seq}",
                sequence=self._trade_seq,
                symbol=self._symbol,
                buyer_order_id=buyer.order_id,
                seller_order_id=seller.order_id,
                buyer_broker_id=buyer.broker_id,
                seller_broker_id=seller.broker_id,
                price=fill_price,
                quantity=fill_qty,
            )
            self._trades.append(trade)
            trades.append(trade)
        return trades

    @staticmethod
    def _prices_cross(incoming: Order, resting: Order) -> bool:
        """Check if the incoming order's price crosses the resting order."""
        if incoming.side == Side.BUY:
            return incoming.price >= resting.price
        return resting.price >= incoming.price
