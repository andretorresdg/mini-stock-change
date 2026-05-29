"""Gateway service tests for customer-document self-trade prevention."""

from datetime import UTC, datetime, timedelta

from mini_exchange.order_gateway.models import GatewaySubmitOrder
from mini_exchange.order_gateway.service import OrderGatewayService
from mini_exchange.orderbook.models import Side
from tests.customer_documents import CUST_111, CUST_222, CUST_SHARED

_NOW = datetime(2030, 6, 15, 12, 0, 0, tzinfo=UTC)
_FUTURE = _NOW + timedelta(hours=1)


def _svc() -> OrderGatewayService:
    return OrderGatewayService(clock=lambda: _NOW)


def _submit(
    svc: OrderGatewayService,
    *,
    broker_id: str,
    side: Side,
    document_number: str,
    price: int = 1_000,
    quantity: int = 100,
) -> None:
    svc.submit_order(
        GatewaySubmitOrder(
            broker_id=broker_id,
            document_number=document_number,
            client_order_id=None,
            side=side,
            valid_until=_FUTURE,
            symbol="AAPL",
            price=price,
            quantity=quantity,
        )
    )


class TestGatewaySelfTradePrevention:
    def test_same_customer_document_across_brokers_does_not_match(self) -> None:
        svc = _svc()
        _submit(
            svc,
            broker_id="BROKER-ALPHA",
            side=Side.SELL,
            document_number=CUST_SHARED,
        )
        resp = svc.submit_order(
            GatewaySubmitOrder(
                broker_id="BROKER-BETA",
                document_number=CUST_SHARED,
                client_order_id=None,
                side=Side.BUY,
                valid_until=_FUTURE,
                symbol="AAPL",
                price=1_000,
                quantity=100,
            )
        )
        assert len(resp.trades) == 0

    def test_different_customer_documents_match_at_seller_price(self) -> None:
        svc = _svc()
        _submit(
            svc,
            broker_id="BROKER-ALPHA",
            side=Side.SELL,
            document_number=CUST_111,
            price=1_000,
        )
        resp = svc.submit_order(
            GatewaySubmitOrder(
                broker_id="BROKER-BETA",
                document_number=CUST_222,
                client_order_id=None,
                side=Side.BUY,
                valid_until=_FUTURE,
                symbol="AAPL",
                price=2_000,
                quantity=100,
            )
        )
        assert len(resp.trades) == 1
        assert resp.trades[0].price == 1_000

    def test_same_broker_different_customer_documents_may_trade(self) -> None:
        svc = _svc()
        _submit(
            svc,
            broker_id="BROKER-ALPHA",
            side=Side.SELL,
            document_number=CUST_111,
        )
        resp = svc.submit_order(
            GatewaySubmitOrder(
                broker_id="BROKER-ALPHA",
                document_number=CUST_222,
                client_order_id=None,
                side=Side.BUY,
                valid_until=_FUTURE,
                symbol="AAPL",
                price=1_000,
                quantity=100,
            )
        )
        assert len(resp.trades) == 1
