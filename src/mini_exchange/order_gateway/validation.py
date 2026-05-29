"""Validation helpers for the order gateway."""

import re

from mini_exchange.order_gateway.errors import InvalidBrokerError
from mini_exchange.order_gateway.models import GatewaySubmitOrder

_BROKER_ID_PATTERN = re.compile(r"^[A-Za-z0-9._\-]+$")
_BROKER_ID_MAX_LENGTH = 64


def validate_broker_id(broker_id: str) -> None:
    """Validate broker_id format and length."""
    if not broker_id or not broker_id.strip():
        msg = "broker_id must not be empty or whitespace"
        raise InvalidBrokerError(msg)
    if len(broker_id) > _BROKER_ID_MAX_LENGTH:
        msg = f"broker_id must be at most {_BROKER_ID_MAX_LENGTH} characters"
        raise InvalidBrokerError(msg)
    if not _BROKER_ID_PATTERN.match(broker_id):
        msg = "broker_id contains invalid characters"
        raise InvalidBrokerError(msg)


def make_order_id(symbol: str, order_sequence: int) -> str:
    """Generate a deterministic order ID from symbol and sequence."""
    if not symbol or not symbol.strip():
        msg = "symbol must not be empty"
        raise ValueError(msg)
    if not isinstance(order_sequence, int) or order_sequence < 1:
        msg = "order_sequence must be a positive integer"
        raise ValueError(msg)
    return f"{symbol.strip().upper()}-O-{order_sequence}"


def build_submit_fingerprint(
    request: GatewaySubmitOrder,
) -> tuple[object, ...]:
    """Build a deterministic fingerprint tuple for idempotency checks."""
    # GTC orders (valid_until is None) use a stable marker so retries match.
    valid_until = (
        request.valid_until.isoformat() if request.valid_until is not None else "GTC"
    )
    return (
        request.broker_id,
        request.client_order_id,
        request.document_number,
        request.side.value,
        valid_until,
        request.symbol,
        request.price,
        request.quantity,
    )
