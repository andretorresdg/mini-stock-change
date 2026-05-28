"""Tests for order gateway errors."""

import pytest

from mini_exchange.order_gateway import (
    ExpiredOrderError,
    GatewayStateError,
    IdempotencyConflictError,
    InvalidBrokerError,
    OrderGatewayError,
    OrderNotFoundError,
)


@pytest.mark.parametrize(
    "exc_class",
    [
        InvalidBrokerError,
        ExpiredOrderError,
        OrderNotFoundError,
        IdempotencyConflictError,
        GatewayStateError,
    ],
)
def test_subclass_of_gateway_error(exc_class: type) -> None:
    assert issubclass(exc_class, OrderGatewayError)


def test_gateway_error_is_exception() -> None:
    assert issubclass(OrderGatewayError, Exception)


def test_errors_carry_message() -> None:
    err = ExpiredOrderError("order expired")
    assert str(err) == "order expired"
