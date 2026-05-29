"""Tests for GET /api/v1/market/{symbol}/book."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from mini_exchange.api.app import create_app
from mini_exchange.order_gateway.service import OrderGatewayService

_CLOCK_AT = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
_VALID_UNTIL = "2099-01-01T00:00:00Z"
PRICE_10 = 1_000
PRICE_15 = 1_500
PRICE_20 = 2_000


def _clock() -> datetime:
    return _CLOCK_AT


def _make_client() -> TestClient:
    svc = OrderGatewayService(clock=_clock)
    return TestClient(create_app(order_gateway=svc))


def _body(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "document_number": "DOC-001",
        "side": "ASK",
        "valid_until": _VALID_UNTIL,
        "symbol": "AAPL",
        "price": PRICE_10,
        "quantity": 100,
    }
    base.update(overrides)
    return base


class TestEmptyBook:
    def test_unknown_symbol_returns_200_with_empty_sides(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/market/NEWCOIN/book")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "NEWCOIN"
        assert data["bids"] == []
        assert data["asks"] == []


class TestSymbolNormalization:
    def test_lowercase_symbol_in_url_normalized_to_uppercase(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(side="ASK", price=PRICE_10),
        )
        resp = client.get("/api/v1/market/aapl/book")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "AAPL"
        assert len(data["asks"]) == 1


class TestRestingOrders:
    def test_resting_ask_appears_in_asks(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(side="ASK", price=PRICE_10, quantity=100),
        )
        resp = client.get("/api/v1/market/AAPL/book")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["asks"]) == 1
        assert data["asks"][0]["price"] == PRICE_10
        assert data["asks"][0]["quantity"] == 100
        assert data["bids"] == []

    def test_resting_bid_appears_in_bids(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(side="BID", price=900, quantity=50),
        )
        resp = client.get("/api/v1/market/AAPL/book")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["bids"]) == 1
        assert data["bids"][0]["price"] == 900
        assert data["bids"][0]["quantity"] == 50
        assert data["asks"] == []

    def test_no_match_shows_both_sides(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(side="ASK", price=PRICE_20, quantity=100),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(side="BID", price=PRICE_10, quantity=100),
        )
        resp = client.get("/api/v1/market/AAPL/book")
        data = resp.json()
        assert len(data["asks"]) == 1
        assert len(data["bids"]) == 1
        assert data["asks"][0]["price"] == PRICE_20
        assert data["bids"][0]["price"] == PRICE_10


class TestSorting:
    def test_bid_levels_sorted_descending(self) -> None:
        client = _make_client()
        for price, broker in [
            (PRICE_10, "b1"),
            (PRICE_20, "b2"),
            (PRICE_15, "b3"),
        ]:
            client.post(
                f"/api/v1/brokers/{broker}/orders",
                json=_body(side="BID", price=price, quantity=10),
            )
        resp = client.get("/api/v1/market/AAPL/book")
        prices = [lvl["price"] for lvl in resp.json()["bids"]]
        assert prices == sorted(prices, reverse=True)

    def test_ask_levels_sorted_ascending(self) -> None:
        client = _make_client()
        for price, broker in [
            (PRICE_20, "s1"),
            (PRICE_10, "s2"),
            (PRICE_15, "s3"),
        ]:
            client.post(
                f"/api/v1/brokers/{broker}/orders",
                json=_body(side="ASK", price=price, quantity=10),
            )
        resp = client.get("/api/v1/market/AAPL/book")
        prices = [lvl["price"] for lvl in resp.json()["asks"]]
        assert prices == sorted(prices)


class TestAggregation:
    def test_same_price_ask_quantities_aggregated(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/s1/orders",
            json=_body(side="ASK", price=PRICE_10, quantity=40),
        )
        client.post(
            "/api/v1/brokers/s2/orders",
            json=_body(side="ASK", price=PRICE_10, quantity=60),
        )
        resp = client.get("/api/v1/market/AAPL/book")
        data = resp.json()
        assert len(data["asks"]) == 1
        assert data["asks"][0]["quantity"] == 100

    def test_same_price_bid_quantities_aggregated(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/b1/orders",
            json=_body(side="BID", price=PRICE_10, quantity=30),
        )
        client.post(
            "/api/v1/brokers/b2/orders",
            json=_body(side="BID", price=PRICE_10, quantity=20),
        )
        resp = client.get("/api/v1/market/AAPL/book")
        data = resp.json()
        assert len(data["bids"]) == 1
        assert data["bids"][0]["quantity"] == 50


class TestDepthParameter:
    def test_depth_limits_returned_levels(self) -> None:
        client = _make_client()
        brokers = ["s1", "s2", "s3", "s4", "s5"]
        for i, broker in enumerate(brokers):
            client.post(
                f"/api/v1/brokers/{broker}/orders",
                json=_body(side="ASK", price=(i + 1) * 1_000, quantity=10),
            )
        resp = client.get("/api/v1/market/AAPL/book?depth=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["asks"]) == 2
        assert data["asks"][0]["price"] == 1_000
        assert data["asks"][1]["price"] == 2_000

    def test_invalid_depth_zero_returns_422(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/market/AAPL/book?depth=0")
        assert resp.status_code == 422

    def test_invalid_depth_51_returns_422(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/market/AAPL/book?depth=51")
        assert resp.status_code == 422


class TestFilledOrdersExcluded:
    def test_fully_matched_orders_not_in_book(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(side="ASK", price=PRICE_10, quantity=100),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(side="BID", price=PRICE_10, quantity=100),
        )
        resp = client.get("/api/v1/market/AAPL/book")
        data = resp.json()
        assert data["bids"] == []
        assert data["asks"] == []

    def test_partially_filled_ask_shows_remaining_quantity(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(side="ASK", price=PRICE_10, quantity=100),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(side="BID", price=PRICE_10, quantity=40),
        )
        resp = client.get("/api/v1/market/AAPL/book")
        data = resp.json()
        assert len(data["asks"]) == 1
        assert data["asks"][0]["quantity"] == 60
