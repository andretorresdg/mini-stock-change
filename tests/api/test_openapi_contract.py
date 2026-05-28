"""OpenAPI contract regression tests."""

from fastapi.testclient import TestClient

from mini_exchange.api import create_app

_SUBMIT_PATH = "/api/v1/brokers/{broker_id}/orders"
_STATUS_PATH = "/api/v1/brokers/{broker_id}/orders/{order_id}"


def _get_schema() -> dict:  # type: ignore[type-arg]
    client = TestClient(create_app())
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    return resp.json()


class TestPathsExist:
    def test_submit_path_exists(self) -> None:
        schema = _get_schema()
        assert _SUBMIT_PATH in schema["paths"]

    def test_status_path_exists(self) -> None:
        schema = _get_schema()
        assert _STATUS_PATH in schema["paths"]


class TestMethods:
    def test_post_method_on_submit(self) -> None:
        schema = _get_schema()
        assert "post" in schema["paths"][_SUBMIT_PATH]

    def test_get_method_on_status(self) -> None:
        schema = _get_schema()
        assert "get" in schema["paths"][_STATUS_PATH]


class TestSchemas:
    def test_submit_order_request_schema(self) -> None:
        schema = _get_schema()
        schemas = schema["components"]["schemas"]
        assert "SubmitOrderRequest" in schemas

    def test_order_response_schema(self) -> None:
        schema = _get_schema()
        schemas = schema["components"]["schemas"]
        assert "OrderResponse" in schemas

    def test_trade_response_schema(self) -> None:
        schema = _get_schema()
        schemas = schema["components"]["schemas"]
        assert "TradeResponse" in schemas

    def test_error_response_schema(self) -> None:
        schema = _get_schema()
        schemas = schema["components"]["schemas"]
        assert "ErrorResponse" in schemas


class TestResponseCodes:
    def test_post_declares_201(self) -> None:
        schema = _get_schema()
        post = schema["paths"][_SUBMIT_PATH]["post"]
        assert "201" in post["responses"]

    def test_get_declares_200(self) -> None:
        schema = _get_schema()
        get = schema["paths"][_STATUS_PATH]["get"]
        assert "200" in get["responses"]

    def test_post_declares_422(self) -> None:
        schema = _get_schema()
        post = schema["paths"][_SUBMIT_PATH]["post"]
        assert "422" in post["responses"]

    def test_get_declares_422(self) -> None:
        schema = _get_schema()
        get = schema["paths"][_STATUS_PATH]["get"]
        assert "422" in get["responses"]
