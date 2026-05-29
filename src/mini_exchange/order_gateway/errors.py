"""Order gateway domain errors."""


class OrderGatewayError(Exception):
    """Base error for the order gateway."""


class InvalidBrokerError(OrderGatewayError):
    """Raised when the broker identifier is invalid."""


class ExpiredOrderError(OrderGatewayError):
    """Raised when an order has expired at submission time."""


class OrderNotFoundError(OrderGatewayError):
    """Raised when an order is not found or inaccessible."""


class IdempotencyConflictError(OrderGatewayError):
    """Raised when client_order_id is reused with different parameters."""


class GatewayStateError(OrderGatewayError):
    """Raised when the gateway is in an inconsistent internal state."""
