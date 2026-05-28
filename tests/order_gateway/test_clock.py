"""Tests for the clock module."""

from datetime import UTC, datetime

from mini_exchange.order_gateway import utc_now


def test_utc_now_returns_datetime() -> None:
    result = utc_now()
    assert isinstance(result, datetime)


def test_utc_now_is_timezone_aware() -> None:
    result = utc_now()
    assert result.tzinfo is not None


def test_utc_now_is_utc() -> None:
    result = utc_now()
    assert result.tzinfo == UTC
