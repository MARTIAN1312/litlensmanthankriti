from __future__ import annotations

from pathlib import Path

import pytest

from app.config import REPO_ROOT, Settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("GROQ_API_KEY", "GEMINI_API_KEY", "GEMINI_MODEL", "CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)


def test_placeholder_and_blank_keys_count_as_missing() -> None:
    s = Settings(_env_file=None, groq_api_key="your-groq-key-here", gemini_api_key="")
    assert s.groq_api_key is None
    assert s.gemini_api_key is None
    assert not s.groq_configured


def test_key_is_secret_in_repr() -> None:
    s = Settings(_env_file=None, groq_api_key="gsk_supersecret")
    assert "gsk_supersecret" not in repr(s)
    assert s.groq_configured


def test_gemini_needs_key_and_model() -> None:
    assert not Settings(_env_file=None, gemini_api_key="k").gemini_configured
    s = Settings(_env_file=None, gemini_api_key="k", gemini_model="some-flash-model")
    assert s.gemini_configured


def test_cors_never_allows_wildcard() -> None:
    s = Settings(_env_file=None, cors_origins="*, http://localhost:5173")
    assert s.cors_origin_list == ["http://localhost:5173"]


def test_relative_data_dir_is_under_repo_root() -> None:
    s = Settings(_env_file=None, data_dir=Path("data"))
    assert s.data_dir == (REPO_ROOT / "data").resolve()


def test_host_loopback_detection() -> None:
    assert Settings(_env_file=None).host_is_loopback
    assert not Settings(_env_file=None, host="0.0.0.0").host_is_loopback
