"""Tests for app-level OrderGatewayService wiring."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mini_exchange.api.app import create_app
from mini_exchange.api.dependencies import get_order_gateway_service
from mini_exchange.api.routers.orders import router as orders_router
from mini_exchange.order_gateway.service import OrderGatewayService


class TestSharedServiceInstance:
    def test_app_uses_one_shared_gateway_instance(self) -> None:
        svc = OrderGatewayService()
        app = create_app(order_gateway=svc)
        assert app.state.order_gateway is svc

    def test_default_creates_service_if_none(self) -> None:
        app = create_app()
        assert isinstance(app.state.order_gateway, OrderGatewayService)

    def test_requests_share_the_same_instance(self) -> None:
        app = create_app()
        client = TestClient(app)
        resp1 = client.post(
            "/api/v1/brokers/broker1/orders",
            json={
                "document_number": "DOC-001",
                "side": "BID",
                "valid_until": "2040-01-01T00:00:00Z",
                "symbol": "AAPL",
                "price": 100,
                "quantity": 10,
            },
        )
        assert resp1.status_code == 201
        order_id = resp1.json()["order_id"]
        resp2 = client.get(f"/api/v1/brokers/broker1/orders/{order_id}")
        assert resp2.status_code == 200
        assert resp2.json()["order_id"] == order_id


class TestMissingServiceRaises:
    def test_missing_service_raises_runtime_error(self) -> None:
        app = FastAPI()
        app.include_router(orders_router)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/v1/brokers/broker1/orders",
            json={
                "document_number": "DOC-001",
                "side": "BID",
                "valid_until": "2040-01-01T00:00:00Z",
                "symbol": "AAPL",
                "price": 100,
                "quantity": 10,
            },
        )
        assert resp.status_code == 500

    def test_dependency_raises_directly(self) -> None:
        from unittest.mock import MagicMock

        request = MagicMock()
        request.app.state = MagicMock(spec=[])
        with pytest.raises(RuntimeError, match="not configured"):
            get_order_gateway_service(request)
