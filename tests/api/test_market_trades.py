"""Tests for GET /api/v1/market/{symbol}/trades."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from mini_exchange.api.app import create_app
from mini_exchange.order_gateway.service import OrderGatewayService
from tests.customer_documents import doc_for

_CLOCK_AT = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
_VALID_UNTIL = "2099-01-01T00:00:00Z"
PRICE_10 = 1_000
PRICE_20 = 2_000


def _clock() -> datetime:
    return _CLOCK_AT


def _make_client() -> TestClient:
    svc = OrderGatewayService(clock=_clock)
    return TestClient(create_app(order_gateway=svc))


def _body(
    *,
    broker: str = "default",
    document_number: str | None = None,
    **overrides: object,
) -> dict[str, object]:
    base: dict[str, object] = {
        "document_number": document_number
        if document_number is not None
        else doc_for(broker),
        "side": "ASK",
        "valid_until": _VALID_UNTIL,
        "symbol": "AAPL",
        "price": PRICE_10,
        "quantity": 100,
    }
    base.update(overrides)
    return base


class TestNoTrades:
    def test_unknown_symbol_returns_200_with_empty_trades(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/market/NEWCOIN/trades")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "NEWCOIN"
        assert data["trades"] == []


class TestSymbolNormalization:
    def test_lowercase_symbol_in_url_normalized_to_uppercase(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(broker="seller", side="ASK", price=PRICE_10),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(broker="buyer", side="BID", price=PRICE_10),
        )
        resp = client.get("/api/v1/market/aapl/trades")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "AAPL"
        assert len(data["trades"]) == 1


class TestSamePriceMatch:
    def test_matched_trade_appears_in_response(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(broker="seller", side="ASK", price=PRICE_10, quantity=50),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(broker="buyer", side="BID", price=PRICE_10, quantity=50),
        )
        resp = client.get("/api/v1/market/AAPL/trades")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["trades"]) == 1
        trade = data["trades"][0]
        assert trade["price"] == PRICE_10
        assert trade["quantity"] == 50
        assert trade["symbol"] == "AAPL"
        assert trade["trade_id"] != ""
        assert trade["sequence"] >= 1

    def test_price_gap_trade_uses_ask_price(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(broker="seller", side="ASK", price=PRICE_10, quantity=100),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(broker="buyer", side="BID", price=PRICE_20, quantity=100),
        )
        resp = client.get("/api/v1/market/AAPL/trades")
        data = resp.json()
        assert data["trades"][0]["price"] == PRICE_10


class TestPartialFill:
    def test_partial_fill_trade_has_matched_quantity(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(broker="seller", side="ASK", price=PRICE_10, quantity=100),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(broker="buyer", side="BID", price=PRICE_10, quantity=40),
        )
        resp = client.get("/api/v1/market/AAPL/trades")
        data = resp.json()
        assert len(data["trades"]) == 1
        assert data["trades"][0]["quantity"] == 40


class TestMultipleTrades:
    def test_all_trades_returned_within_default_limit(self) -> None:
        client = _make_client()
        for s, b in [("s1", "b1"), ("s2", "b2"), ("s3", "b3")]:
            client.post(
                f"/api/v1/brokers/{s}/orders",
                json=_body(broker=s, side="ASK", price=PRICE_10, quantity=10),
            )
            client.post(
                f"/api/v1/brokers/{b}/orders",
                json=_body(broker=b, side="BID", price=PRICE_10, quantity=10),
            )
        resp = client.get("/api/v1/market/AAPL/trades")
        assert len(resp.json()["trades"]) == 3

    def test_trades_returned_newest_first(self) -> None:
        client = _make_client()
        for s, b in [("s1", "b1"), ("s2", "b2"), ("s3", "b3")]:
            client.post(
                f"/api/v1/brokers/{s}/orders",
                json=_body(broker=s, side="ASK", price=PRICE_10, quantity=10),
            )
            client.post(
                f"/api/v1/brokers/{b}/orders",
                json=_body(broker=b, side="BID", price=PRICE_10, quantity=10),
            )
        resp = client.get("/api/v1/market/AAPL/trades")
        seqs = [t["sequence"] for t in resp.json()["trades"]]
        assert seqs == sorted(seqs, reverse=True)


class TestSymbolFilter:
    def test_trades_filtered_by_symbol(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(broker="seller", side="ASK", symbol="AAPL", price=PRICE_10),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(broker="buyer", side="BID", symbol="AAPL", price=PRICE_10),
        )
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(broker="seller", side="ASK", symbol="GOOG", price=PRICE_10),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(broker="buyer", side="BID", symbol="GOOG", price=PRICE_10),
        )
        aapl = client.get("/api/v1/market/AAPL/trades").json()
        goog = client.get("/api/v1/market/GOOG/trades").json()
        assert len(aapl["trades"]) == 1
        assert aapl["trades"][0]["symbol"] == "AAPL"
        assert len(goog["trades"]) == 1
        assert goog["trades"][0]["symbol"] == "GOOG"


class TestLimitParameter:
    def test_limit_restricts_returned_trades(self) -> None:
        client = _make_client()
        for s, b in [("s1", "b1"), ("s2", "b2"), ("s3", "b3")]:
            client.post(
                f"/api/v1/brokers/{s}/orders",
                json=_body(broker=s, side="ASK", price=PRICE_10, quantity=10),
            )
            client.post(
                f"/api/v1/brokers/{b}/orders",
                json=_body(broker=b, side="BID", price=PRICE_10, quantity=10),
            )
        resp = client.get("/api/v1/market/AAPL/trades?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()["trades"]) == 2

    def test_limit_zero_returns_422(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/market/AAPL/trades?limit=0")
        assert resp.status_code == 422

    def test_limit_201_returns_422(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/market/AAPL/trades?limit=201")
        assert resp.status_code == 422


class TestPrivacy:
    def test_response_does_not_expose_document_number(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(
                broker="seller", side="ASK", price=PRICE_10, document_number="PRIV-DOC"
            ),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(broker="buyer", side="BID", price=PRICE_10),
        )
        resp = client.get("/api/v1/market/AAPL/trades")
        trade = resp.json()["trades"][0]
        assert "document_number" not in trade
        assert "PRIV-DOC" not in str(trade)

    def test_response_does_not_expose_broker_ids(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/secret-seller/orders",
            json=_body(broker="secret-seller", side="ASK", price=PRICE_10),
        )
        client.post(
            "/api/v1/brokers/secret-buyer/orders",
            json=_body(broker="secret-buyer", side="BID", price=PRICE_10),
        )
        resp = client.get("/api/v1/market/AAPL/trades")
        trade = resp.json()["trades"][0]
        assert "broker_id" not in trade
        assert "secret-seller" not in str(trade)
        assert "secret-buyer" not in str(trade)

    def test_response_contains_only_expected_fields(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(broker="seller", side="ASK", price=PRICE_10),
        )
        client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(broker="buyer", side="BID", price=PRICE_10),
        )
        resp = client.get("/api/v1/market/AAPL/trades")
        trade = resp.json()["trades"][0]
        assert set(trade.keys()) == {
            "trade_id",
            "sequence",
            "symbol",
            "price",
            "quantity",
        }
