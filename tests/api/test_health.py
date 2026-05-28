"""Tests for the health endpoints, app factory, and CORS configuration."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mini_exchange.api import create_app

_ALLOWED_ORIGIN = "http://localhost:5173"
_DISALLOWED_ORIGIN = "http://evil.example.com"


def test_create_app_returns_fastapi() -> None:
    app = create_app()
    assert isinstance(app, FastAPI)


def test_app_title() -> None:
    app = create_app()
    assert app.title == "Mini Exchange API"


class TestHealthEndpoints:
    def setup_method(self) -> None:
        self.client = TestClient(create_app())

    def test_liveness(self) -> None:
        response = self.client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_readiness(self) -> None:
        response = self.client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestOpenAPI:
    def setup_method(self) -> None:
        self.client = TestClient(create_app())

    def test_openapi_available(self) -> None:
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/health/live" in schema["paths"]
        assert "/health/ready" in schema["paths"]


class TestCORSAllowedOrigin:
    def setup_method(self) -> None:
        self.client = TestClient(create_app())

    def test_cors_header_present_for_allowed_origin(self) -> None:
        response = self.client.get("/health/live", headers={"Origin": _ALLOWED_ORIGIN})
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == _ALLOWED_ORIGIN

    def test_cors_header_absent_for_disallowed_origin(self) -> None:
        response = self.client.get(
            "/health/live", headers={"Origin": _DISALLOWED_ORIGIN}
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers

    def test_127_origin_allowed(self) -> None:
        response = self.client.get(
            "/health/live", headers={"Origin": "http://127.0.0.1:5173"}
        )
        assert response.status_code == 200
        assert (
            response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
        )


class TestCORSPreflight:
    def setup_method(self) -> None:
        self.client = TestClient(create_app())

    def test_preflight_submit_order(self) -> None:
        response = self.client.options(
            "/api/v1/brokers/broker1/orders",
            headers={
                "Origin": _ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == _ALLOWED_ORIGIN
        assert "POST" in response.headers["access-control-allow-methods"]

    def test_preflight_disallowed_origin_no_cors_header(self) -> None:
        response = self.client.options(
            "/api/v1/brokers/broker1/orders",
            headers={
                "Origin": _DISALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
            },
        )
        assert "access-control-allow-origin" not in response.headers
