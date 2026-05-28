"""Tests for the order submission endpoint."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from mini_exchange.api.app import create_app
from mini_exchange.api.services.order_gateway import (
    OrderGatewayError,
    OrderGatewayService,
)


def _fixed_clock() -> datetime:
    return datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)


def _make_app() -> TestClient:
    svc = OrderGatewayService(clock=_fixed_clock)
    app = create_app(order_gateway_service=svc)
    return TestClient(app)


def _valid_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "document_number": "DOC-001",
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
        assert data["order_id"] == "AAPL-1"


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
        assert resp.json()["order_id"] == "AAPL-1"

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
            json=_valid_body(side="ASK", price=1000),
        )
        resp = client.post(
            "/api/v1/brokers/buyer/orders",
            json=_valid_body(side="BID", price=2000),
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
        app = create_app(order_gateway_service=mock_svc)
        client = TestClient(app)
        resp = client.post("/api/v1/brokers/broker1/orders", json=_valid_body())
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == "ORDER_GATEWAY_ERROR"
        assert data["message"] == "something went wrong"
