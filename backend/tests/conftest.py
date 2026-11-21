"""Shared fixtures. Tests never read the real `.env` and never call real APIs."""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.fakes import make_services


def pytest_pycollect_makeitem(collector, name, obj):  # noqa: ANN001, ANN201, ARG001
    """Run every `async def test_...` on asyncio via anyio's bundled pytest plugin.

    The mark is applied to the function itself *before* pytest parametrizes it,
    so it also works for @pytest.mark.parametrize'd async tests.
    """
    if name.startswith("test") and inspect.iscoroutinefunction(obj):
        pytest.mark.anyio(obj)
    return None  # let pytest collect it normally


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        groq_api_key="test-groq-key",
        gemini_api_key=None,
        env="dev",
        data_dir=tmp_path / "data",
    )


@pytest.fixture
def client(settings: Settings, tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(settings, make_services(tmp_path, settings=settings))
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
