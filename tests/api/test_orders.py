"""Tests for the order endpoints."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from mini_exchange.api.app import create_app
from mini_exchange.order_gateway.errors import OrderGatewayError
from mini_exchange.order_gateway.service import OrderGatewayService


def _fixed_clock() -> datetime:
    return datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)


def _make_app() -> TestClient:
    svc = OrderGatewayService(clock=_fixed_clock)
    app = create_app(order_gateway=svc)
    return TestClient(app)


def _valid_body(*, customer: str = "DOC-001", **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "document_number": customer,
        "side": "ASK",
        "valid_until": "2030-01-01T00:00:00Z",
        "symbol": "AAPL",
        "price": 100,
        "quantity": 10,
    }
    body.update(overrides)
    return body


class TestSubmitAsk:
    def test_successful_ask(self) -> None:
        client = _make_app()
        resp = client.post(
            "/api/v1/brokers/broker1/orders", json=_valid_body(side="ASK")
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["side"] == "ASK"
        assert data["status"] == "OPEN"
        assert data["order_id"] == "AAPL-O-1"


class TestSubmitBid:
    def test_successful_bid(self) -> None:
        client = _make_app()
        resp = client.post(
            "/api/v1/brokers/broker1/orders", json=_valid_body(side="BID")
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["side"] == "BID"
        assert data["status"] == "OPEN"


class TestResponseFields:
    def test_includes_order_id(self) -> None:
        client = _make_app()
        resp = client.post("/api/v1/brokers/broker1/orders", json=_valid_body())
        assert resp.json()["order_id"] == "AAPL-O-1"

    def test_includes_broker_id_from_path(self) -> None:
        client = _make_app()
        resp = client.post("/api/v1/brokers/my-broker/orders", json=_valid_body())
        assert resp.json()["broker_id"] == "my-broker"

    def test_includes_document_number(self) -> None:
        client = _make_app()
        resp = client.post("/api/v1/brokers/broker1/orders", json=_valid_body())
        assert resp.json()["document_number"] == "DOC-001"

    def test_includes_valid_until(self) -> None:
        client = _make_app()
        resp = client.post("/api/v1/brokers/broker1/orders", json=_valid_body())
        assert resp.json()["valid_until"] == "2030-01-01T00:00:00Z"

    def test_includes_status(self) -> None:
        client = _make_app()
        resp = client.post("/api/v1/brokers/broker1/orders", json=_valid_body())
        assert resp.json()["status"] == "OPEN"


class TestPriceGapMatch:
    def test_seller_price_execution(self) -> None:
        client = _make_app()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_valid_body(side="ASK", price=1000, customer="DOC-SELLER"),
        )
        resp = client.post(
            "/api/v1/brokers/buyer/orders",
            json=_valid_body(side="BID", price=2000, customer="DOC-BUYER"),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "FILLED"
        assert len(data["trades"]) == 1
        assert data["trades"][0]["price"] == 1000


class TestInvalidRequestBody:
    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"side": "BID"},
            _valid_body(price=-1),
            {
                "document_number": "D",
                "side": "BID",
                "valid_until": "2030-01-01T00:00:00Z",
                "symbol": "X",
                "price": 1.5,
                "quantity": 10,
            },
        ],
        ids=["empty", "missing-fields", "negative-price", "float-price"],
    )
    def test_invalid_body_returns_422(self, body: object) -> None:
        client = _make_app()
        resp = client.post("/api/v1/brokers/broker1/orders", json=body)
        assert resp.status_code == 422


class TestInvalidBrokerPath:
    @pytest.mark.parametrize(
        "broker_id",
        ["a" * 65, "bad broker!"],
        ids=["too-long", "invalid-chars"],
    )
    def test_invalid_broker_returns_422(self, broker_id: str) -> None:
        client = _make_app()
        resp = client.post(f"/api/v1/brokers/{broker_id}/orders", json=_valid_body())
        assert resp.status_code == 422

    def test_empty_broker_returns_404(self) -> None:
        client = _make_app()
        resp = client.post("/api/v1/brokers//orders", json=_valid_body())
        assert resp.status_code == 404


class TestExpiredOrder:
    def test_expired_order_returns_400(self) -> None:
        client = _make_app()
        resp = client.post(
            "/api/v1/brokers/broker1/orders",
            json=_valid_body(valid_until="2020-01-01T00:00:00Z"),
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == "EXPIRED_ORDER"
        assert "expired" in data["message"]


class TestGenericGatewayError:
    def test_unexpected_gateway_error_returns_400(self) -> None:
        mock_svc = MagicMock(spec=OrderGatewayService)
        mock_svc.submit_order.side_effect = OrderGatewayError("something went wrong")
        app = create_app(order_gateway=mock_svc)
        client = TestClient(app)
        resp = client.post("/api/v1/brokers/broker1/orders", json=_valid_body())
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == "ORDER_GATEWAY_ERROR"
        assert data["message"] == "something went wrong"


# --- GET /api/v1/brokers/{broker_id}/orders/{order_id} ---


class TestGetOrderResting:
    def test_retrieve_resting_order(self) -> None:
        client = _make_app()
        client.post(
            "/api/v1/brokers/broker1/orders",
            json=_valid_body(side="BID"),
        )
        resp = client.get("/api/v1/brokers/broker1/orders/AAPL-O-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_id"] == "AAPL-O-1"
        assert data["status"] == "OPEN"
        assert data["remaining_quantity"] == 10
        assert data["trades"] == []


class TestGetOrderFilled:
    def test_retrieve_filled_order(self) -> None:
        client = _make_app()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_valid_body(side="ASK", price=100, customer="DOC-SELLER"),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_valid_body(side="BID", price=100, customer="DOC-BUYER"),
        )
        resp = client.get("/api/v1/brokers/seller/orders/AAPL-O-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "FILLED"
        assert data["filled_quantity"] == 10


class TestGetOrderPartiallyFilled:
    def test_retrieve_partially_filled_order(self) -> None:
        client = _make_app()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_valid_body(side="ASK", price=100, quantity=20, customer="DOC-SELLER"),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_valid_body(side="BID", price=100, quantity=5, customer="DOC-BUYER"),
        )
        resp = client.get("/api/v1/brokers/seller/orders/AAPL-O-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "PARTIALLY_FILLED"
        assert data["remaining_quantity"] == 15
        assert data["filled_quantity"] == 5


class TestGetOrderIncludesTrades:
    def test_response_includes_trades(self) -> None:
        client = _make_app()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_valid_body(side="ASK", price=100, customer="DOC-SELLER"),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_valid_body(side="BID", price=100, customer="DOC-BUYER"),
        )
        resp = client.get("/api/v1/brokers/buyer/orders/AAPL-O-2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["trades"]) == 1
        assert data["trades"][0]["buyer_order_id"] == "AAPL-O-2"
        assert data["trades"][0]["seller_order_id"] == "AAPL-O-1"
        assert data["trades"][0]["price"] == 100


class TestGetOrderNotFound:
    def test_unknown_order_returns_404(self) -> None:
        client = _make_app()
        resp = client.get("/api/v1/brokers/broker1/orders/no-such")
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == "ORDER_NOT_FOUND"


class TestGetOrderWrongBroker:
    def test_wrong_broker_returns_404(self) -> None:
        client = _make_app()
        client.post(
            "/api/v1/brokers/broker1/orders",
            json=_valid_body(side="BID"),
        )
        resp = client.get("/api/v1/brokers/broker2/orders/AAPL-O-1")
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == "ORDER_NOT_FOUND"


class TestGetOrderInvalidBrokerPath:
    @pytest.mark.parametrize(
        "broker_id",
        ["a" * 65, "bad broker!"],
        ids=["too-long", "invalid-chars"],
    )
    def test_invalid_broker_returns_422(self, broker_id: str) -> None:
        client = _make_app()
        resp = client.get(f"/api/v1/brokers/{broker_id}/orders/X-1")
        assert resp.status_code == 422


class TestGetOrderInvalidOrderId:
    def test_empty_order_id_returns_method_not_allowed(self) -> None:
        client = _make_app()
        resp = client.get("/api/v1/brokers/broker1/orders/")
        assert resp.status_code == 405


class TestIdempotencyConflictEndpoint:
    def test_conflict_returns_409(self) -> None:
        client = _make_app()
        body = _valid_body(client_order_id="dup1", price=100)
        resp1 = client.post("/api/v1/brokers/broker1/orders", json=body)
        assert resp1.status_code == 201
        body2 = _valid_body(client_order_id="dup1", price=200)
        resp2 = client.post("/api/v1/brokers/broker1/orders", json=body2)
        assert resp2.status_code == 409
        data = resp2.json()
        assert data["code"] == "IDEMPOTENCY_CONFLICT"
