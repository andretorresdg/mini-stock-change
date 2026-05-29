"""Acceptance tests for the public order API contract.

These tests exercise the full HTTP stack through the FastAPI TestClient,
proving that the order management API satisfies the exchange requirements.
No OrderBook or MatchingEngine is imported directly.

All prices are integer cents:
  $10.00 = 1_000 cents
  $20.00 = 2_000 cents

No floats are used in this file.
"""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from mini_exchange.api.app import create_app
from mini_exchange.order_gateway.service import OrderGatewayService
from tests.customer_documents import doc_for

_CLOCK_AT = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
_VALID_UNTIL = "2099-01-01T00:00:00Z"

# Price constants in integer cents — no floats.
PRICE_10 = 1_000  # $10.00
PRICE_20 = 2_000  # $20.00


def _clock() -> datetime:
    return _CLOCK_AT


def _make_client() -> TestClient:
    """Create a fresh TestClient with an isolated in-memory service."""
    svc = OrderGatewayService(clock=_clock)
    return TestClient(create_app(order_gateway=svc))


def _body(
    *,
    broker: str = "default",
    document_number: str | None = None,
    **overrides: object,
) -> dict[str, object]:
    body: dict[str, object] = {
        "document_number": document_number
        if document_number is not None
        else doc_for(broker),
        "side": "ASK",
        "valid_until": _VALID_UNTIL,
        "symbol": "AAPL",
        "price": PRICE_10,
        "quantity": 1_000,
    }
    body.update(overrides)
    return body


# ── API contract shape ────────────────────────────────────────────────────────


class TestResponseContainsAllRequiredFields:
    """POST response must expose the full set of order fields."""

    def test_submit_response_includes_all_required_fields(self) -> None:
        client = _make_client()
        resp = client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )

        assert resp.status_code == 201
        data = resp.json()
        required = {
            "order_id",
            "broker_id",
            "document_number",
            "side",
            "symbol",
            "price",
            "quantity",
            "remaining_quantity",
            "filled_quantity",
            "status",
            "valid_until",
            "trades",
        }
        assert required.issubset(data.keys())

    def test_order_id_from_post_is_usable_in_get(self) -> None:
        client = _make_client()
        post_resp = client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )

        order_id = post_resp.json()["order_id"]
        get_resp = client.get(f"/api/v1/brokers/broker-a/orders/{order_id}")

        assert get_resp.status_code == 200
        assert get_resp.json()["order_id"] == order_id


# ── Requirement 1: Same price full match ─────────────────────────────────────


class TestSamePriceFullMatchThroughAPI:
    """POST ASK 1000 @ $10 then POST BID 1000 @ $10 → trade at $10."""

    def test_bid_response_includes_trade_at_ask_price(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="BID", price=PRICE_10, quantity=1_000),
        )

        assert bid_resp.status_code == 201
        data = bid_resp.json()
        assert len(data["trades"]) == 1
        assert data["trades"][0]["price"] == PRICE_10
        assert data["trades"][0]["quantity"] == 1_000

    def test_bid_response_status_is_filled(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="BID", price=PRICE_10, quantity=1_000),
        )

        data = bid_resp.json()
        assert data["status"] == "FILLED"
        assert data["filled_quantity"] == 1_000
        assert data["remaining_quantity"] == 0

    def test_seller_order_retrievable_as_filled(self) -> None:
        client = _make_client()
        ask_resp = client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )
        client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="BID", price=PRICE_10, quantity=1_000),
        )

        ask_id = ask_resp.json()["order_id"]
        get_resp = client.get(f"/api/v1/brokers/broker-a/orders/{ask_id}")

        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "FILLED"

    def test_buyer_order_retrievable_as_filled(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="BID", price=PRICE_10, quantity=1_000),
        )

        bid_id = bid_resp.json()["order_id"]
        get_resp = client.get(f"/api/v1/brokers/broker-b/orders/{bid_id}")

        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "FILLED"


# ── Requirement 2: No match ───────────────────────────────────────────────────


class TestNoMatchThroughAPI:
    """POST ASK @ $20 then POST BID @ $10 → bid below ask → no trade."""

    def test_bid_response_has_no_trades_and_status_open(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_20, quantity=1_000),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="BID", price=PRICE_10, quantity=1_000),
        )

        assert bid_resp.status_code == 201
        data = bid_resp.json()
        assert len(data["trades"]) == 0
        assert data["status"] == "OPEN"

    def test_both_orders_retrievable_as_open(self) -> None:
        client = _make_client()
        ask_resp = client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_20, quantity=1_000),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="BID", price=PRICE_10, quantity=1_000),
        )

        ask_id = ask_resp.json()["order_id"]
        bid_id = bid_resp.json()["order_id"]
        seller_get = client.get(f"/api/v1/brokers/broker-a/orders/{ask_id}")
        buyer_get = client.get(f"/api/v1/brokers/broker-b/orders/{bid_id}")

        assert seller_get.json()["status"] == "OPEN"
        assert buyer_get.json()["status"] == "OPEN"


# ── Requirement 3: Price gap — seller price wins ──────────────────────────────


class TestPriceGapThroughAPI:
    """POST ASK @ $10 then POST BID @ $20 → trade at seller's $10."""

    def test_execution_price_is_seller_price_not_buyer_price(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="BID", price=PRICE_20, quantity=1_000),
        )

        assert bid_resp.status_code == 201
        data = bid_resp.json()
        assert len(data["trades"]) == 1
        assert data["trades"][0]["price"] == PRICE_10  # $10.00, not $20.00

    def test_both_orders_retrievable_as_filled(self) -> None:
        client = _make_client()
        ask_resp = client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="BID", price=PRICE_20, quantity=1_000),
        )

        ask_id = ask_resp.json()["order_id"]
        bid_id = bid_resp.json()["order_id"]
        seller_get = client.get(f"/api/v1/brokers/broker-a/orders/{ask_id}")
        buyer_get = client.get(f"/api/v1/brokers/broker-b/orders/{bid_id}")

        assert seller_get.json()["status"] == "FILLED"
        assert buyer_get.json()["status"] == "FILLED"


# ── Requirement 4: Partial fill ───────────────────────────────────────────────


class TestPartialFillThroughAPI:
    """POST ASK 1000 @ $10 then POST BID 500 @ $10 → buyer filled, seller 500 left."""

    def test_buyer_is_fully_filled(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="BID", price=PRICE_10, quantity=500),
        )

        assert bid_resp.status_code == 201
        data = bid_resp.json()
        assert data["status"] == "FILLED"
        assert data["filled_quantity"] == 500
        assert data["remaining_quantity"] == 0

    def test_trade_quantity_equals_buyer_quantity(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="BID", price=PRICE_10, quantity=500),
        )

        assert bid_resp.json()["trades"][0]["quantity"] == 500

    def test_seller_is_partially_filled_with_500_remaining(self) -> None:
        client = _make_client()
        ask_resp = client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )
        client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="BID", price=PRICE_10, quantity=500),
        )

        ask_id = ask_resp.json()["order_id"]
        get_resp = client.get(f"/api/v1/brokers/broker-a/orders/{ask_id}")

        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["status"] == "PARTIALLY_FILLED"
        assert data["remaining_quantity"] == 500
        assert data["filled_quantity"] == 500


# ── Requirement 5: Multiple sellers, one larger buyer ─────────────────────────


class TestMultipleSellersOneLargerBuyerThroughAPI:
    """ASK-A 500 + ASK-B 500 + BID-C 1500 → A fills, B fills, C rests with 500."""

    def test_two_trades_returned_in_bid_response(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=500),
        )
        client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="ASK", price=PRICE_10, quantity=500),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-c/orders",
            json=_body(broker="broker-c", side="BID", price=PRICE_10, quantity=1_500),
        )

        assert bid_resp.status_code == 201
        assert len(bid_resp.json()["trades"]) == 2

    def test_seller_a_fills_first_then_seller_b(self) -> None:
        client = _make_client()
        ask_a_resp = client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=500),
        )
        ask_b_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="ASK", price=PRICE_10, quantity=500),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-c/orders",
            json=_body(broker="broker-c", side="BID", price=PRICE_10, quantity=1_500),
        )

        ask_a_id = ask_a_resp.json()["order_id"]
        ask_b_id = ask_b_resp.json()["order_id"]
        trades = bid_resp.json()["trades"]
        assert trades[0]["seller_order_id"] == ask_a_id
        assert trades[1]["seller_order_id"] == ask_b_id

    def test_buyer_remains_partially_filled_with_500_remaining(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=500),
        )
        client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="ASK", price=PRICE_10, quantity=500),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-c/orders",
            json=_body(broker="broker-c", side="BID", price=PRICE_10, quantity=1_500),
        )

        data = bid_resp.json()
        assert data["status"] == "PARTIALLY_FILLED"
        assert data["remaining_quantity"] == 500


# ── Requirement 6: FIFO at the same price level ───────────────────────────────


class TestFifoAtSamePriceThroughAPI:
    """ASK-A + ASK-B at same price, BID-C for A's quantity → A fills, B stays open."""

    def test_earliest_ask_matches_first(self) -> None:
        client = _make_client()
        ask_a_resp = client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )
        client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="ASK", price=PRICE_10, quantity=1_000),
        )
        bid_resp = client.post(
            "/api/v1/brokers/broker-c/orders",
            json=_body(broker="broker-c", side="BID", price=PRICE_10, quantity=1_000),
        )

        ask_a_id = ask_a_resp.json()["order_id"]
        assert len(bid_resp.json()["trades"]) == 1
        assert bid_resp.json()["trades"][0]["seller_order_id"] == ask_a_id

    def test_earlier_seller_is_filled(self) -> None:
        client = _make_client()
        ask_a_resp = client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )
        client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="ASK", price=PRICE_10, quantity=1_000),
        )
        client.post(
            "/api/v1/brokers/broker-c/orders",
            json=_body(broker="broker-c", side="BID", price=PRICE_10, quantity=1_000),
        )

        ask_a_id = ask_a_resp.json()["order_id"]
        get_resp = client.get(f"/api/v1/brokers/broker-a/orders/{ask_a_id}")

        assert get_resp.json()["status"] == "FILLED"

    def test_later_seller_remains_open(self) -> None:
        client = _make_client()
        client.post(
            "/api/v1/brokers/broker-a/orders",
            json=_body(broker="broker-a", side="ASK", price=PRICE_10, quantity=1_000),
        )
        ask_b_resp = client.post(
            "/api/v1/brokers/broker-b/orders",
            json=_body(broker="broker-b", side="ASK", price=PRICE_10, quantity=1_000),
        )
        client.post(
            "/api/v1/brokers/broker-c/orders",
            json=_body(broker="broker-c", side="BID", price=PRICE_10, quantity=1_000),
        )

        ask_b_id = ask_b_resp.json()["order_id"]
        get_resp = client.get(f"/api/v1/brokers/broker-b/orders/{ask_b_id}")

        assert get_resp.json()["status"] == "OPEN"
