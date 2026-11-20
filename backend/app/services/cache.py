"""SQLite cache for arXiv and LLM responses (DESIGN §7, SRS FR-50).

Keys are content hashes, so an identical request never spends quota twice.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS http_cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS llm_cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    tokens_in INTEGER NOT NULL,
    tokens_out INTEGER NOT NULL,
    created_at REAL NOT NULL
);
"""


def make_key(*parts: Any) -> str:
    """Stable sha256 over JSON-encoded parts (sorted keys, so dict order never matters)."""
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CachedLLM:
    text: str
    tokens_in: int
    tokens_out: int


class Cache:
    """Small thread-safe wrapper. Calls are fast enough to run inline from async code."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._lock = threading.Lock()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- arXiv / HTTP ---
    def get_http(self, key: str) -> Any | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM http_cache WHERE key = ?", (key,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def set_http(self, key: str, value: Any) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO http_cache (key, value, created_at) "
                "VALUES (?, ?, ?)",
                (key, json.dumps(value, ensure_ascii=False), time.time()),
            )

    # --- LLM ---
    def get_llm(self, key: str) -> CachedLLM | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value, tokens_in, tokens_out FROM llm_cache WHERE key = ?",
                (key,),
            ).fetchone()
        return CachedLLM(row[0], row[1], row[2]) if row else None

    def set_llm(self, key: str, text: str, tokens_in: int, tokens_out: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO llm_cache "
                "(key, value, tokens_in, tokens_out, created_at) VALUES (?, ?, ?, ?, ?)",
                (key, text, tokens_in, tokens_out, time.time()),
            )
