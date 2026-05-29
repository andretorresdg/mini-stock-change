"""Tests for OrderGatewayService.get_market_trades()."""

from datetime import UTC, datetime, timedelta

import pytest

from mini_exchange.order_gateway.models import (
    GatewayMarketTrade,
    GatewayMarketTrades,
    GatewaySubmitOrder,
)
from mini_exchange.order_gateway.service import OrderGatewayService
from mini_exchange.orderbook.models import Side

_NOW = datetime(2030, 6, 15, 12, 0, 0, tzinfo=UTC)
_FUTURE = _NOW + timedelta(hours=1)


def _fixed_clock() -> datetime:
    return _NOW


def _svc() -> OrderGatewayService:
    return OrderGatewayService(clock=_fixed_clock)


def _ask(
    broker: str = "seller",
    price: int = 1_000,
    quantity: int = 100,
    symbol: str = "AAPL",
) -> GatewaySubmitOrder:
    return GatewaySubmitOrder(
        broker_id=broker,
        document_number=f"DOC-{broker}",
        client_order_id=None,
        side=Side.SELL,
        valid_until=_FUTURE,
        symbol=symbol,
        price=price,
        quantity=quantity,
    )


def _bid(
    broker: str = "buyer",
    price: int = 1_000,
    quantity: int = 100,
    symbol: str = "AAPL",
) -> GatewaySubmitOrder:
    return GatewaySubmitOrder(
        broker_id=broker,
        document_number=f"DOC-{broker}",
        client_order_id=None,
        side=Side.BUY,
        valid_until=_FUTURE,
        symbol=symbol,
        price=price,
        quantity=quantity,
    )


class TestGatewayMarketTradeValidation:
    """GatewayMarketTrade rejects invalid arguments."""

    def test_empty_trade_id_raises(self) -> None:
        with pytest.raises(ValueError, match="trade_id"):
            GatewayMarketTrade(
                trade_id="", sequence=1, symbol="AAPL", price=1_000, quantity=10
            )

    def test_sequence_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="sequence"):
            GatewayMarketTrade(
                trade_id="T1", sequence=0, symbol="AAPL", price=1_000, quantity=10
            )

    def test_empty_symbol_raises(self) -> None:
        with pytest.raises(ValueError, match="symbol"):
            GatewayMarketTrade(
                trade_id="T1", sequence=1, symbol="", price=1_000, quantity=10
            )

    def test_price_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="price"):
            GatewayMarketTrade(
                trade_id="T1", sequence=1, symbol="AAPL", price=0, quantity=10
            )

    def test_quantity_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="quantity"):
            GatewayMarketTrade(
                trade_id="T1", sequence=1, symbol="AAPL", price=1_000, quantity=0
            )

    def test_valid_trade_constructed(self) -> None:
        t = GatewayMarketTrade(
            trade_id="T1", sequence=1, symbol="AAPL", price=1_000, quantity=10
        )
        assert t.trade_id == "T1"
        assert t.sequence == 1


class TestGatewayMarketTradesValidation:
    """GatewayMarketTrades rejects empty symbol."""

    def test_empty_symbol_raises(self) -> None:
        with pytest.raises(ValueError, match="symbol"):
            GatewayMarketTrades(symbol="", trades=())

    def test_valid_container_constructed(self) -> None:
        result = GatewayMarketTrades(symbol="AAPL", trades=())
        assert result.symbol == "AAPL"
        assert result.trades == ()


class TestNoTrades:
    def test_unknown_symbol_returns_empty_trades(self) -> None:
        svc = _svc()
        result = svc.get_market_trades("AAPL")
        assert result.symbol == "AAPL"
        assert result.trades == ()


class TestSymbolNormalization:
    def test_lowercase_symbol_normalized_to_uppercase(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(price=1_000))
        svc.submit_order(_bid(price=1_000))
        result = svc.get_market_trades("aapl")
        assert result.symbol == "AAPL"
        assert len(result.trades) == 1

    def test_whitespace_in_symbol_trimmed(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(price=1_000))
        svc.submit_order(_bid(price=1_000))
        result = svc.get_market_trades("  AAPL  ")
        assert result.symbol == "AAPL"
        assert len(result.trades) == 1


class TestSamePriceMatch:
    def test_trade_has_correct_price_and_quantity(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(price=1_000, quantity=50))
        svc.submit_order(_bid(price=1_000, quantity=50))
        result = svc.get_market_trades("AAPL")
        assert len(result.trades) == 1
        trade = result.trades[0]
        assert trade.price == 1_000
        assert trade.quantity == 50
        assert trade.symbol == "AAPL"
        assert trade.trade_id != ""
        assert trade.sequence >= 1

    def test_trade_does_not_expose_broker_ids(self) -> None:
        svc = _svc()
        svc.submit_order(_ask())
        svc.submit_order(_bid())
        result = svc.get_market_trades("AAPL")
        trade = result.trades[0]
        assert not hasattr(trade, "buyer_broker_id")
        assert not hasattr(trade, "seller_broker_id")
        assert not hasattr(trade, "document_number")


class TestPriceGapMatch:
    def test_trade_price_is_resting_ask_price(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(price=1_000, quantity=100))
        svc.submit_order(_bid(price=2_000, quantity=100))
        result = svc.get_market_trades("AAPL")
        assert len(result.trades) == 1
        assert result.trades[0].price == 1_000


class TestPartialFill:
    def test_partial_fill_trade_quantity_is_matched_quantity(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(price=1_000, quantity=100))
        svc.submit_order(_bid(price=1_000, quantity=40))
        result = svc.get_market_trades("AAPL")
        assert len(result.trades) == 1
        assert result.trades[0].quantity == 40


class TestMultipleTrades:
    def test_all_trades_returned_when_within_limit(self) -> None:
        svc = _svc()
        for s, b in [("s1", "b1"), ("s2", "b2"), ("s3", "b3")]:
            svc.submit_order(_ask(broker=s, price=1_000, quantity=10))
            svc.submit_order(_bid(broker=b, price=1_000, quantity=10))
        result = svc.get_market_trades("AAPL")
        assert len(result.trades) == 3


class TestSymbolFilter:
    def test_only_matching_symbol_trades_returned(self) -> None:
        svc = _svc()
        svc.submit_order(_ask(price=1_000, symbol="AAPL"))
        svc.submit_order(_bid(price=1_000, symbol="AAPL"))
        svc.submit_order(_ask(price=1_000, symbol="GOOG"))
        svc.submit_order(_bid(price=1_000, symbol="GOOG"))
        aapl = svc.get_market_trades("AAPL")
        goog = svc.get_market_trades("GOOG")
        assert len(aapl.trades) == 1
        assert aapl.trades[0].symbol == "AAPL"
        assert len(goog.trades) == 1
        assert goog.trades[0].symbol == "GOOG"


class TestLimitParameter:
    def test_limit_restricts_number_of_returned_trades(self) -> None:
        svc = _svc()
        brokers = [("s1", "b1"), ("s2", "b2"), ("s3", "b3")]
        for s, b in brokers:
            svc.submit_order(_ask(broker=s, price=1_000, quantity=10))
            svc.submit_order(_bid(broker=b, price=1_000, quantity=10))
        result = svc.get_market_trades("AAPL", limit=2)
        assert len(result.trades) == 2

    def test_limit_returns_newest_trades_first(self) -> None:
        svc = _svc()
        brokers = [("s1", "b1"), ("s2", "b2"), ("s3", "b3")]
        for s, b in brokers:
            svc.submit_order(_ask(broker=s, price=1_000, quantity=10))
            svc.submit_order(_bid(broker=b, price=1_000, quantity=10))
        result = svc.get_market_trades("AAPL", limit=2)
        seqs = [t.sequence for t in result.trades]
        assert seqs == sorted(seqs, reverse=True)


class TestTradesOrder:
    """Trades are returned newest-to-oldest (descending sequence)."""

    def test_all_trades_ordered_newest_first(self) -> None:
        svc = _svc()
        brokers = [("s1", "b1"), ("s2", "b2"), ("s3", "b3")]
        for s, b in brokers:
            svc.submit_order(_ask(broker=s, price=1_000, quantity=10))
            svc.submit_order(_bid(broker=b, price=1_000, quantity=10))
        result = svc.get_market_trades("AAPL")
        seqs = [t.sequence for t in result.trades]
        assert seqs == sorted(seqs, reverse=True)
