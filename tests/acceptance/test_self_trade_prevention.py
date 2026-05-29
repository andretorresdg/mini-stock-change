"""Acceptance tests: same document_number must not self-trade through the API."""

from fastapi.testclient import TestClient

from mini_exchange.api.app import create_app
from mini_exchange.order_gateway.service import OrderGatewayService

PRICE_10 = 1_000
DOC_SAME = "CUST-123"
DOC_OTHER = "CUST-456"


def _make_client() -> TestClient:
    return TestClient(create_app(order_gateway=OrderGatewayService()))


def _body(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "document_number": DOC_SAME,
        "side": "ASK",
        "valid_until": None,
        "symbol": "AAPL",
        "price": PRICE_10,
        "quantity": 100,
    }
    payload.update(overrides)
    return payload


class TestSelfTradePreventionThroughAPI:
    """Brokers must not execute against the same customer document number."""

    def test_same_document_ask_and_bid_do_not_trade(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(side="ASK", document_number=DOC_SAME),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(side="BID", document_number=DOC_SAME),
        )

        assert bid_resp.status_code == 201
        data = bid_resp.json()
        assert len(data["trades"]) == 0
        assert data["status"] == "OPEN"

    def test_different_documents_trade_normally(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(side="ASK", document_number=DOC_SAME),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(side="BID", document_number=DOC_OTHER),
        )

        assert bid_resp.status_code == 201
        data = bid_resp.json()
        assert len(data["trades"]) == 1
        assert data["status"] == "FILLED"

    def test_self_trade_skipped_in_favor_of_other_customer(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(side="ASK", document_number=DOC_SAME, quantity=100),
        )
        client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(side="ASK", document_number=DOC_OTHER, quantity=100),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-c/orders",
            json=_body(side="BID", document_number=DOC_SAME, quantity=100),
        )

        assert bid_resp.status_code == 201
        data = bid_resp.json()
        assert len(data["trades"]) == 1
        assert data["trades"][0]["seller_broker_id"] == "broker-b"
        assert data["status"] == "FILLED"

    def test_both_self_trade_orders_retrievable_as_open(self) -> None:
        client = _make_client()
        ask_resp = client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(side="ASK", document_number=DOC_SAME),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(side="BID", document_number=DOC_SAME),
        )

        ask_id = ask_resp.json()["order_id"]
        bid_id = bid_resp.json()["order_id"]
        assert (
            client.get(f"/api/v1/brokers/broker-a/orders/{ask_id}").json()["status"]
            == "OPEN"
        )
        assert (
            client.get(f"/api/v1/brokers/broker-b/orders/{bid_id}").json()["status"]
            == "OPEN"
        )
