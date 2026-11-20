"""Shared fixtures. Tests never read the real `.env` and never call real APIs."""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Run every `async def test_...` on asyncio via anyio's bundled pytest plugin."""
    for item in items:
        fn = getattr(item, "function", None)
        if fn is not None and inspect.iscoroutinefunction(fn):
            item.add_marker(pytest.mark.anyio)


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
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
