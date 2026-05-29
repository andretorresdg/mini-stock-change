"""Acceptance tests: customer document ownership and self-trade prevention."""

from fastapi.testclient import TestClient

from mini_exchange.api.app import create_app
from mini_exchange.order_gateway.service import OrderGatewayService
from tests.customer_documents import CUST_111, CUST_222, CUST_SHARED

PRICE_10 = 1_000
PRICE_20 = 2_000


def _make_client() -> TestClient:
    return TestClient(create_app(order_gateway=OrderGatewayService()))


def _body(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "document_number": CUST_111,
        "side": "ASK",
        "valid_until": None,
        "symbol": "AAPL",
        "price": PRICE_10,
        "quantity": 100,
    }
    payload.update(overrides)
    return payload


class TestSelfTradePreventionThroughAPI:
    def test_orders_with_same_customer_document_do_not_self_trade_across_brokers(
        self,
    ) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/BROKER-ALPHA/orders",
            json=_body(side="ASK", document_number=CUST_SHARED),
        )
        bid_resp = client.post(
            "/api/v1/brokers/BROKER-BETA/orders",
            json=_body(side="BID", document_number=CUST_SHARED),
        )

        assert bid_resp.status_code == 201
        data = bid_resp.json()
        assert data["document_number"] == CUST_SHARED
        assert data["broker_id"] == "BROKER-BETA"
        assert len(data["trades"]) == 0
        assert data["status"] == "OPEN"

    def test_orders_with_different_customer_documents_trade_normally(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/BROKER-ALPHA/orders",
            json=_body(side="ASK", document_number=CUST_111),
        )
        bid_resp = client.post(
            "/api/v1/brokers/BROKER-BETA/orders",
            json=_body(side="BID", document_number=CUST_222),
        )

        assert bid_resp.status_code == 201
        data = bid_resp.json()
        assert data["document_number"] == CUST_222
        assert len(data["trades"]) == 1
        assert data["status"] == "FILLED"

    def test_same_customer_document_does_not_trade_even_with_price_gap(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/BROKER-ALPHA/orders",
            json=_body(side="ASK", document_number=CUST_SHARED, price=PRICE_10),
        )
        bid_resp = client.post(
            "/api/v1/brokers/BROKER-BETA/orders",
            json=_body(side="BID", document_number=CUST_SHARED, price=PRICE_20),
        )

        assert bid_resp.status_code == 201
        data = bid_resp.json()
        assert len(data["trades"]) == 0
        assert data["status"] == "OPEN"

    def test_different_customer_documents_execute_at_seller_price(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/BROKER-ALPHA/orders",
            json=_body(side="ASK", document_number=CUST_111, price=PRICE_10),
        )
        bid_resp = client.post(
            "/api/v1/brokers/BROKER-BETA/orders",
            json=_body(side="BID", document_number=CUST_222, price=PRICE_20),
        )

        assert bid_resp.status_code == 201
        data = bid_resp.json()
        assert len(data["trades"]) == 1
        assert data["trades"][0]["price"] == PRICE_10

    def test_self_trade_skipped_in_favor_of_other_customer(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/BROKER-ALPHA/orders",
            json=_body(side="ASK", document_number=CUST_SHARED, quantity=100),
        )
        client.post(
            "/api/v1/brokers/BROKER-BETA/orders",
            json=_body(side="ASK", document_number=CUST_222, quantity=100),
        )
        bid_resp = client.post(
            "/api/v1/brokers/BROKER-C/orders",
            json=_body(side="BID", document_number=CUST_SHARED, quantity=100),
        )

        assert bid_resp.status_code == 201
        data = bid_resp.json()
        assert len(data["trades"]) == 1
        assert data["trades"][0]["seller_broker_id"] == "BROKER-BETA"
        assert data["status"] == "FILLED"

    def test_both_self_trade_orders_retrievable_as_open(self) -> None:
        client = _make_client()
        ask_resp = client.post(
            "/api/v1/brokers/BROKER-ALPHA/orders",
            json=_body(side="ASK", document_number=CUST_SHARED),
        )
        bid_resp = client.post(
            "/api/v1/brokers/BROKER-BETA/orders",
            json=_body(side="BID", document_number=CUST_SHARED),
        )

        ask_id = ask_resp.json()["order_id"]
        bid_id = bid_resp.json()["order_id"]
        ask_status = client.get(f"/api/v1/brokers/BROKER-ALPHA/orders/{ask_id}").json()
        bid_status = client.get(f"/api/v1/brokers/BROKER-BETA/orders/{bid_id}").json()
        assert ask_status["status"] == "OPEN"
        assert ask_status["document_number"] == CUST_SHARED
        assert bid_status["status"] == "OPEN"
        assert bid_status["document_number"] == CUST_SHARED

    def test_same_broker_different_customer_documents_may_trade(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/BROKER-ALPHA/orders",
            json=_body(side="ASK", document_number=CUST_111),
        )
        bid_resp = client.post(
            "/api/v1/brokers/BROKER-ALPHA/orders",
            json=_body(side="BID", document_number=CUST_222),
        )

        assert bid_resp.status_code == 201
        assert len(bid_resp.json()["trades"]) == 1
