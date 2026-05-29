"""Deployment configuration tests.

Verify textually that the Docker Compose MVP is not accidentally configured
for multiple workers.  Only the Python standard library is used for parsing
so no extra dependencies are required.
"""

import importlib
import pathlib

_ROOT = pathlib.Path(__file__).parent.parent.parent
_CONTAINERFILE = _ROOT / "deploy" / "backend.Containerfile"
_COMPOSE = _ROOT / "compose.yaml"
_README = _ROOT / "README.md"


class TestContainerfileDoesNotUseMultipleWorkers:
    """The Containerfile must start Uvicorn as a single process."""

    def test_containerfile_exists(self) -> None:
        assert _CONTAINERFILE.exists()

    def test_no_workers_flag(self) -> None:
        text = _CONTAINERFILE.read_text(encoding="utf-8")
        assert "--workers" not in text

    def test_no_gunicorn(self) -> None:
        text = _CONTAINERFILE.read_text(encoding="utf-8")
        assert "gunicorn" not in text.lower()

    def test_uvicorn_is_the_server(self) -> None:
        text = _CONTAINERFILE.read_text(encoding="utf-8")
        assert "uvicorn" in text.lower()


class TestComposeDoesNotScaleApi:
    """Docker Compose must define exactly one API service instance."""

    def test_compose_exists(self) -> None:
        assert _COMPOSE.exists()

    def test_api_service_is_present(self) -> None:
        text = _COMPOSE.read_text(encoding="utf-8")
        assert "api:" in text

    def test_no_replicas_configured(self) -> None:
        text = _COMPOSE.read_text(encoding="utf-8")
        assert "replicas:" not in text

    def test_no_workers_flag_in_compose(self) -> None:
        text = _COMPOSE.read_text(encoding="utf-8")
        assert "--workers" not in text


class TestReadmeContainsSingleWorkerWarning:
    """README must document the single-worker constraint."""

    def test_single_worker_warning_present(self) -> None:
        text = _README.read_text(encoding="utf-8-sig")
        lower = text.lower()
        assert "single" in lower
        assert "worker" in lower

    def test_workers_flag_mentioned_as_forbidden(self) -> None:
        text = _README.read_text(encoding="utf-8-sig")
        assert "--workers" in text

    def test_restart_resets_state_is_documented(self) -> None:
        text = _README.read_text(encoding="utf-8-sig")
        lower = text.lower()
        assert "restart" in lower


class TestAsgiEntrypoint:
    """The ASGI entrypoint module must be importable and expose a single app."""

    def test_main_module_is_importable(self) -> None:
        main_mod = importlib.import_module("mini_exchange.api.main")
        assert main_mod.app is not None

    def test_repeated_import_returns_same_app(self) -> None:
        first = importlib.import_module("mini_exchange.api.main")
        second = importlib.import_module("mini_exchange.api.main")
        assert first.app is second.app
