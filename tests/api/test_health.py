"""Tests for the health endpoints and app factory."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mini_exchange.api import create_app


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
