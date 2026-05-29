"""Acceptance tests: expired orders must not be matched.

These tests exercise the full HTTP stack through FastAPI TestClient,
proving that the exchange never executes an order whose validity window
has elapsed.  All prices are integer cents ($10.00 = 1_000).  No floats.
A deterministic mutable clock replaces real sleeps.

MVP uses lazy expiration at the gateway boundary.
The matching core stays clock-free and deterministic.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from mini_exchange.api.app import create_app
from mini_exchange.order_gateway.service import OrderGatewayService

_NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)

# Price constants in integer cents — no floats.
PRICE_10 = 1_000  # $10.00
PRICE_20 = 2_000  # $20.00

_EXPIRE_IN_5M = _NOW + timedelta(minutes=5)
_EXPIRE_IN_2H = _NOW + timedelta(hours=2)


class _MutableClock:
    def __init__(self, at: datetime = _NOW) -> None:
        self.now = at

    def __call__(self) -> datetime:
        return self.now


def _iso(dt: datetime) -> str:
    """Format a UTC datetime as an ISO 8601 string accepted by the API."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_client(clock: _MutableClock) -> TestClient:
    """Create a TestClient backed by an in-memory service with a fake clock."""
    svc = OrderGatewayService(clock=clock)
    return TestClient(create_app(order_gateway=svc))


def _body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "document_number": "DOC-001",
        "side": "ASK",
        "valid_until": _iso(_EXPIRE_IN_2H),
        "symbol": "AAPL",
        "price": PRICE_10,
        "quantity": 1_000,
    }
    body.update(overrides)
    return body


# ── Expired ASK must not be matched ───────────────────────────────────────────


class TestExpiredAskNotExecuted:
    """An ASK past its valid_until must not be matched by any new BID."""

    def test_bid_after_expired_ask_gets_no_fill(self) -> None:
        clock = _MutableClock(_NOW)
        client = _make_client(clock)

        ask = client.post(
            "/api/v1/brokers/brokerA/orders",
            json=_body(side="ASK", valid_until=_iso(_EXPIRE_IN_5M)),
        )
        assert ask.status_code == 201
        ask_id = ask.json()["order_id"]

        # Advance clock past the ASK's validity window.
        clock.now = _NOW + timedelta(minutes=10)

        bid = client.post(
            "/api/v1/brokers/brokerB/orders",
            json=_body(side="BID", price=PRICE_10, valid_until=_iso(_EXPIRE_IN_2H)),
        )
        assert bid.status_code == 201
        bid_data = bid.json()
        assert bid_data["status"] == "OPEN"
        assert bid_data["filled_quantity"] == 0
        assert bid_data["trades"] == []

        # The BID submission triggered lazy expiration; ASK must now be EXPIRED.
        ask_final = client.get(f"/api/v1/brokers/brokerA/orders/{ask_id}")
        assert ask_final.json()["status"] == "EXPIRED"


# ── Expired BID must not be matched ───────────────────────────────────────────


class TestExpiredBidNotExecuted:
    """A BID past its valid_until must not be matched by any new ASK."""

    def test_ask_after_expired_bid_gets_no_fill(self) -> None:
        clock = _MutableClock(_NOW)
        client = _make_client(clock)

        bid = client.post(
            "/api/v1/brokers/brokerA/orders",
            json=_body(side="BID", price=PRICE_20, valid_until=_iso(_EXPIRE_IN_5M)),
        )
        assert bid.status_code == 201
        bid_id = bid.json()["order_id"]

        # Advance clock past the BID's validity window.
        clock.now = _NOW + timedelta(minutes=10)

        ask = client.post(
            "/api/v1/brokers/brokerB/orders",
            json=_body(side="ASK", price=PRICE_10, valid_until=_iso(_EXPIRE_IN_2H)),
        )
        assert ask.status_code == 201
        ask_data = ask.json()
        assert ask_data["status"] == "OPEN"
        assert ask_data["filled_quantity"] == 0
        assert ask_data["trades"] == []

        # The ASK submission triggered lazy expiration; BID must now be EXPIRED.
        bid_final = client.get(f"/api/v1/brokers/brokerA/orders/{bid_id}")
        assert bid_final.json()["status"] == "EXPIRED"


# ── Partially filled order expiration ─────────────────────────────────────────


class TestPartiallyFilledOrderExpiration:
    """Partial fill then clock advance — remainder must not be matched."""

    def test_third_party_bid_does_not_match_expired_remainder(self) -> None:
        clock = _MutableClock(_NOW)
        client = _make_client(clock)

        # Broker A submits ASK 1000 @ PRICE_10.
        ask = client.post(
            "/api/v1/brokers/brokerA/orders",
            json=_body(side="ASK", quantity=1_000, valid_until=_iso(_EXPIRE_IN_5M)),
        )
        assert ask.status_code == 201
        ask_id = ask.json()["order_id"]

        # Broker B takes 500 — partially fills the ASK.
        bid_b = client.post(
            "/api/v1/brokers/brokerB/orders",
            json=_body(side="BID", quantity=500, valid_until=_iso(_EXPIRE_IN_2H)),
        )
        assert bid_b.json()["status"] == "FILLED"

        ask_mid = client.get(f"/api/v1/brokers/brokerA/orders/{ask_id}")
        assert ask_mid.json()["status"] == "PARTIALLY_FILLED"
        assert ask_mid.json()["remaining_quantity"] == 500

        # Advance clock — Broker A's order expires.
        clock.now = _NOW + timedelta(minutes=10)

        # Broker C bids for the remaining 500; must not match the expired ASK.
        bid_c = client.post(
            "/api/v1/brokers/brokerC/orders",
            json=_body(side="BID", quantity=500, valid_until=_iso(_EXPIRE_IN_2H)),
        )
        assert bid_c.status_code == 201
        bid_c_data = bid_c.json()
        assert bid_c_data["status"] == "OPEN"
        assert bid_c_data["filled_quantity"] == 0

        # Broker A's final status is EXPIRED, retaining the partial fill record.
        ask_final = client.get(f"/api/v1/brokers/brokerA/orders/{ask_id}")
        assert ask_final.json()["status"] == "EXPIRED"
        assert ask_final.json()["filled_quantity"] == 500
        assert ask_final.json()["remaining_quantity"] == 500

    def test_partially_filled_order_status_becomes_expired_on_clock_advance(
        self,
    ) -> None:
        clock = _MutableClock(_NOW)
        client = _make_client(clock)

        ask = client.post(
            "/api/v1/brokers/brokerA/orders",
            json=_body(side="ASK", quantity=1_000, valid_until=_iso(_EXPIRE_IN_5M)),
        )
        ask_id = ask.json()["order_id"]

        client.post(
            "/api/v1/brokers/brokerB/orders",
            json=_body(side="BID", quantity=300, valid_until=_iso(_EXPIRE_IN_2H)),
        )

        clock.now = _NOW + timedelta(minutes=10)

        ask_final = client.get(f"/api/v1/brokers/brokerA/orders/{ask_id}")
        data = ask_final.json()
        assert data["status"] == "EXPIRED"
        assert data["filled_quantity"] == 300
        assert data["remaining_quantity"] == 700


# ── Filled order must not become expired ──────────────────────────────────────


class TestFilledOrderDoesNotExpire:
    """A fully matched order remains FILLED regardless of clock advance."""

    def test_filled_status_persists_after_valid_until_passes(self) -> None:
        clock = _MutableClock(_NOW)
        client = _make_client(clock)

        ask = client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(side="ASK", quantity=1_000, valid_until=_iso(_EXPIRE_IN_5M)),
        )
        assert ask.status_code == 201
        ask_id = ask.json()["order_id"]

        bid = client.post(
            "/api/v1/brokers/buyer/orders",
            json=_body(side="BID", quantity=1_000, valid_until=_iso(_EXPIRE_IN_2H)),
        )
        assert bid.json()["status"] == "FILLED"

        # Confirm FILLED before clock advance.
        ask_mid = client.get(f"/api/v1/brokers/seller/orders/{ask_id}")
        assert ask_mid.json()["status"] == "FILLED"

        # Advance clock well past valid_until.
        clock.now = _NOW + timedelta(minutes=10)

        # Status must remain FILLED, never become EXPIRED.
        ask_final = client.get(f"/api/v1/brokers/seller/orders/{ask_id}")
        assert ask_final.json()["status"] == "FILLED"


# ── Expired-at-submission must be rejected ────────────────────────────────────


class TestExpiredAtSubmission:
    """Orders submitted with valid_until <= clock time must be rejected with 400."""

    def test_valid_until_equal_to_now_returns_400(self) -> None:
        clock = _MutableClock(_NOW)
        client = _make_client(clock)

        resp = client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(side="ASK", valid_until=_iso(_NOW)),
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "EXPIRED_ORDER"

    def test_valid_until_before_now_returns_400(self) -> None:
        clock = _MutableClock(_NOW)
        client = _make_client(clock)

        resp = client.post(
            "/api/v1/brokers/seller/orders",
            json=_body(side="ASK", valid_until=_iso(_NOW - timedelta(seconds=1))),
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "EXPIRED_ORDER"
