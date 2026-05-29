"""Tests for the monotonic sequencer."""

import pytest

from mini_exchange.order_gateway import MonotonicSequencer


class TestMonotonicSequencer:
    def test_default_start(self) -> None:
        seq = MonotonicSequencer()
        assert seq.next() == 1
        assert seq.next() == 2
        assert seq.next() == 3

    def test_custom_start(self) -> None:
        seq = MonotonicSequencer(start=100)
        assert seq.next() == 100
        assert seq.next() == 101

    def test_deterministic_sequence(self) -> None:
        seq_a = MonotonicSequencer(start=5)
        seq_b = MonotonicSequencer(start=5)
        for _ in range(10):
            assert seq_a.next() == seq_b.next()

    @pytest.mark.parametrize("start", [0, -1, -100])
    def test_invalid_start_raises(self, start: int) -> None:
        with pytest.raises(ValueError, match="positive integer"):
            MonotonicSequencer(start=start)
