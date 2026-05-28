"""Deterministic command creation for the order gateway."""

from datetime import UTC

from mini_exchange.order_gateway.clock import Clock
from mini_exchange.order_gateway.errors import ExpiredOrderError
from mini_exchange.order_gateway.models import (
    ExpireOrderCommand,
    GatewayCommandType,
    GatewaySubmitOrder,
    SubmitOrderCommand,
)
from mini_exchange.order_gateway.sequencer import MonotonicSequencer
from mini_exchange.order_gateway.validation import make_order_id, validate_broker_id


class OrderCommandFactory:
    """Creates sequenced gateway commands from validated inputs.

    # Command sequence and order ID sequence are separate for the MVP.
    # Production could derive both from a durable command log or an
    # external ID service to guarantee uniqueness across restarts.
    """

    __slots__ = ("_clock", "_command_seq", "_order_id_seq")

    def __init__(
        self,
        command_sequencer: MonotonicSequencer,
        order_id_sequencer: MonotonicSequencer,
        clock: Clock,
    ) -> None:
        self._command_seq = command_sequencer
        self._order_id_seq = order_id_sequencer
        self._clock = clock

    def create_submit_order_command(
        self,
        request: GatewaySubmitOrder,
    ) -> SubmitOrderCommand:
        """Validate, enrich, and return a SubmitOrderCommand."""
        validate_broker_id(request.broker_id)
        received_at = self._clock().astimezone(UTC)

        if request.valid_until <= received_at:
            msg = "order has expired at submission time"
            raise ExpiredOrderError(msg)

        order_sequence = self._order_id_seq.next()
        order_id = make_order_id(request.symbol, order_sequence)

        return SubmitOrderCommand(
            command_sequence=self._command_seq.next(),
            received_at=received_at,
            command_type=GatewayCommandType.SUBMIT_ORDER,
            broker_id=request.broker_id,
            document_number=request.document_number,
            client_order_id=request.client_order_id,
            order_id=order_id,
            side=request.side,
            valid_until=request.valid_until,
            symbol=request.symbol,
            price=request.price,
            quantity=request.quantity,
        )

    def create_expire_order_command(
        self,
        order_id: str,
        symbol: str,
        reason: str,
    ) -> ExpireOrderCommand:
        """Create an ExpireOrderCommand with the next sequence."""
        received_at = self._clock().astimezone(UTC)

        return ExpireOrderCommand(
            command_sequence=self._command_seq.next(),
            received_at=received_at,
            command_type=GatewayCommandType.EXPIRE_ORDER,
            order_id=order_id,
            symbol=symbol,
            reason=reason,
        )
