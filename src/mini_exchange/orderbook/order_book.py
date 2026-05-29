"""Single-symbol deterministic limit order book."""

from __future__ import annotations

from mini_exchange.orderbook.models import (
    ExecutionReport,
    Order,
    OrderStatus,
    Side,
    Trade,
)
from mini_exchange.orderbook.side_book import SideBook


class InvariantViolationError(Exception):
    """Raised when an order book invariant is violated."""


class OrderBook:
    """Deterministic limit order book for a single symbol."""

    __slots__ = (
        "_asks",
        "_bids",
        "_check_invariants",
        "_order_seq",
        "_orders",
        "_symbol",
        "_trade_seq",
        "_trades",
    )

    def __init__(self, symbol: str, *, check_invariants: bool = False) -> None:
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
        self._check_invariants = check_invariants

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
        result = order.cancel()
        if result and self._check_invariants:
            self.validate_invariants()
        return result

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
        document_number: str | None = None,
    ) -> ExecutionReport:
        """Submit a limit order, match it, and return an execution report."""
        self._order_seq += 1
        if order_id is None:
            order_id = f"{self._symbol}-{self._order_seq}"
        if order_id in self._orders:
            msg = f"duplicate order_id: {order_id}"
            raise ValueError(msg)
        if document_number is None:
            document_number = f"DOC-{broker_id}"
        order = Order(
            order_id=order_id,
            broker_id=broker_id,
            document_number=document_number,
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
        report = ExecutionReport(accepted_order=order, trades=tuple(trades))
        if self._check_invariants:
            self.validate_invariants()
        return report

    def validate_invariants(self) -> None:
        """Check all order book invariants. Raises InvariantViolation on failure."""
        self._check_order_invariants()
        self._check_not_crossed()
        self._check_trade_invariants()

    def _check_order_invariants(self) -> None:
        for order in self._orders.values():
            if order.symbol != self._symbol:
                msg = f"order {order.order_id} has wrong symbol {order.symbol}"
                raise InvariantViolationError(msg)
            if order.remaining < 0:
                msg = f"order {order.order_id} has negative remaining"
                raise InvariantViolationError(msg)
            if order.status == OrderStatus.FILLED and order.remaining != 0:
                msg = f"order {order.order_id} is FILLED but remaining != 0"
                raise InvariantViolationError(msg)
            if order.is_active and order.remaining <= 0:
                msg = f"order {order.order_id} is active but remaining <= 0"
                raise InvariantViolationError(msg)

    def _check_not_crossed(self) -> None:
        bid = self.best_bid()
        ask = self.best_ask()
        if bid is not None and ask is not None and bid >= ask:
            msg = f"book is crossed: best_bid={bid} >= best_ask={ask}"
            raise InvariantViolationError(msg)

    def _check_trade_invariants(self) -> None:
        for trade in self._trades:
            if trade.price <= 0:
                msg = f"trade {trade.trade_id} has non-positive price"
                raise InvariantViolationError(msg)
            if trade.quantity <= 0:
                msg = f"trade {trade.trade_id} has non-positive quantity"
                raise InvariantViolationError(msg)
            buyer = self._orders.get(trade.buyer_order_id)
            if buyer is None:
                msg = f"trade {trade.trade_id} refers to unknown buyer"
                raise InvariantViolationError(msg)
            seller = self._orders.get(trade.seller_order_id)
            if seller is None:
                msg = f"trade {trade.trade_id} refers to unknown seller"
                raise InvariantViolationError(msg)
            if buyer.side != Side.BUY:
                msg = f"trade {trade.trade_id} buyer has wrong side"
                raise InvariantViolationError(msg)
            if seller.side != Side.SELL:
                msg = f"trade {trade.trade_id} seller has wrong side"
                raise InvariantViolationError(msg)
            if trade.price != seller.price:
                msg = (
                    f"trade {trade.trade_id} price {trade.price} "
                    f"!= seller price {seller.price}"
                )
                raise InvariantViolationError(msg)
            if buyer.document_number == seller.document_number:
                msg = (
                    f"trade {trade.trade_id} matches same document_number "
                    f"{buyer.document_number}"
                )
                raise InvariantViolationError(msg)

    def _match(self, order: Order) -> list[Trade]:
        """Match an incoming order against the opposite side."""
        trades: list[Trade] = []
        opposite = self._asks if order.side == Side.BUY else self._bids
        while order.remaining > 0:
            resting = opposite.find_matchable_order(order)
            if resting is None:
                break
            fill_qty = min(order.remaining, resting.remaining)
            if order.side == Side.BUY:
                buyer, seller = order, resting
            else:
                buyer, seller = resting, order
            fill_price = seller.price
            order.apply_fill(fill_qty)
            resting.apply_fill(fill_qty)
            opposite.purge_inactive(resting.price)
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
