"""Tests for the mini_exchange package."""

import mini_exchange


def test_version_is_string() -> None:
    assert isinstance(mini_exchange.__version__, str)


def test_version_value() -> None:
    assert mini_exchange.__version__ == "0.1.0"
