"""Monotonic sequence generator for order and trade IDs."""


class MonotonicSequencer:
    """Generates strictly increasing integer sequences.

    # In-memory sequence is sufficient for a single-process MVP.
    # Production would use a durable command log or database sequence
    # to survive restarts and support multi-instance deployments.
    """

    __slots__ = ("_next",)

    def __init__(self, start: int = 1) -> None:
        if not isinstance(start, int) or start < 1:
            msg = "start must be a positive integer"
            raise ValueError(msg)
        self._next = start

    def next(self) -> int:
        """Return the next value and advance the counter."""
        value = self._next
        self._next += 1
        return value
