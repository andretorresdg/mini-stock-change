"""Tests for order routes wired to the new OrderGatewayService."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from mini_exchange.api.app import create_app
from mini_exchange.order_gateway.service import OrderGatewayService

_NOW = datetime(2030, 6, 15, 12, 0, 0, tzinfo=UTC)
_FUTURE = _NOW + timedelta(hours=1)


class _MutableClock:
    def __init__(self, at: datetime = _NOW) -> None:
        self.now = at

    def __call__(self) -> datetime:
        return self.now


def _make_client(clock: _MutableClock | None = None) -> TestClient:
    c = clock or _MutableClock()
    svc = OrderGatewayService(clock=c)
    app = create_app(order_gateway=svc)
    return TestClient(app)


def _valid_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "document_number": "DOC-001",
        "side": "ASK",
        "valid_until": "2031-01-01T00:00:00Z",
        "symbol": "AAPL",
        "price": 100,
        "quantity": 10,
    }
    body.update(overrides)
    return body


class TestSubmitAskHTTP:
    def test_successful_ask(self) -> None:
        client = _make_client()
        resp = client.post(
            "/api/v1/brokers/broker1/orders", json=_valid_body(side="ASK")
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["side"] == "ASK"
        assert data["status"] == "OPEN"
        assert data["order_id"] == "AAPL-O-1"


class TestSubmitBidHTTP:
    def test_successful_bid(self) -> None:
        client = _make_client()
        resp = client.post(
            "/api/v1/brokers/broker1/orders", json=_valid_body(side="BID")
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["side"] == "BID"
        assert data["status"] == "OPEN"


class TestPriceGapMatchHTTP:
    def test_seller_price_is_execution_price(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_valid_body(side="ASK", price=90),
        )
        resp = client.post(
            "/api/v1/brokers/buyer/orders",
            json=_valid_body(side="BID", price=100),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "FILLED"
        assert data["trades"][0]["price"] == 90


class TestGetRestingHTTP:
    def test_get_resting_order(self) -> None:
        client = _make_client()
        client.post("/api/v1/brokers/broker1/orders", json=_valid_body(side="BID"))
        resp = client.get("/api/v1/brokers/broker1/orders/AAPL-O-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "OPEN"
        assert data["remaining_quantity"] == 10


class TestGetFilledHTTP:
    def test_get_filled_order(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_valid_body(side="ASK", price=100),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_valid_body(side="BID", price=100),
        )
        resp = client.get("/api/v1/brokers/seller/orders/AAPL-O-1")
        assert resp.status_code == 200
        assert resp.json()["status"] == "FILLED"


class TestGetPartiallyFilledHTTP:
    def test_get_partially_filled_order(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_valid_body(side="ASK", price=100, quantity=20),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_valid_body(side="BID", price=100, quantity=5),
        )
        resp = client.get("/api/v1/brokers/seller/orders/AAPL-O-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "PARTIALLY_FILLED"
        assert data["filled_quantity"] == 5


class TestNotFoundHTTP:
    def test_unknown_order_404(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/brokers/broker1/orders/NOPE")
        assert resp.status_code == 404
        assert resp.json()["code"] == "ORDER_NOT_FOUND"

    def test_wrong_broker_404(self) -> None:
        client = _make_client()
        client.post("/api/v1/brokers/broker1/orders", json=_valid_body(side="BID"))
        resp = client.get("/api/v1/brokers/other/orders/AAPL-O-1")
        assert resp.status_code == 404
        assert resp.json()["code"] == "ORDER_NOT_FOUND"


class TestIdempotentRetryHTTP:
    def test_retry_returns_same_order_id(self) -> None:
        client = _make_client()
        body = _valid_body(client_order_id="c1", side="BID")
        r1 = client.post("/api/v1/brokers/broker1/orders", json=body)
        r2 = client.post("/api/v1/brokers/broker1/orders", json=body)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["order_id"] == r2.json()["order_id"]


class TestIdempotencyConflictHTTP:
    def test_conflict_returns_409(self) -> None:
        client = _make_client()
        body1 = _valid_body(client_order_id="c1", price=100)
        body2 = _valid_body(client_order_id="c1", price=200)
        client.post("/api/v1/brokers/broker1/orders", json=body1)
        resp = client.post("/api/v1/brokers/broker1/orders", json=body2)
        assert resp.status_code == 409
        assert resp.json()["code"] == "IDEMPOTENCY_CONFLICT"


class TestExpiredAtSubmissionHTTP:
    def test_expired_returns_400(self) -> None:
        client = _make_client()
        resp = client.post(
            "/api/v1/brokers/broker1/orders",
            json=_valid_body(valid_until="2020-01-01T00:00:00Z"),
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "EXPIRED_ORDER"


class TestExpirationThroughHTTP:
    def test_expired_order_not_matched_via_http(self) -> None:
        clock = _MutableClock(_NOW)
        client = _make_client(clock)
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_valid_body(
                side="ASK",
                price=100,
                valid_until=(_NOW + timedelta(minutes=5)).isoformat(),
            ),
        )
        clock.now = _NOW + timedelta(minutes=10)
        resp = client.post(
            "/api/v1/brokers/buyer/orders",
            json=_valid_body(
                side="BID",
                price=100,
                valid_until=(_NOW + timedelta(hours=2)).isoformat(),
            ),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "OPEN"
        assert data["filled_quantity"] == 0
