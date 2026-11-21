"""Vector store: ChromaDB (persistent), with a NumPy fallback behind the same interface.

One collection per job (`job_<uuid-hex>`). Vectors are L2-normalised, so
cosine similarity = dot product (Chroma reports distance = 1 - cosine).
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Protocol
from uuid import UUID

import numpy as np

from app.retrieval.chunker import Chunk

log = logging.getLogger("litlens.vectors")


class VectorStore(Protocol):
    name: str

    def add(self, job_id: UUID, chunks: list[Chunk], vectors: np.ndarray) -> None: ...

    def query(
        self, job_id: UUID, vector: np.ndarray, *, k: int, max_per_paper: int
    ) -> list[tuple[Chunk, float]]: ...

    def count(self, job_id: UUID) -> int: ...

    def delete(self, job_id: UUID) -> None: ...


def _collection_name(job_id: UUID) -> str:
    return f"job_{job_id.hex}"


def _diverse(
    hits: list[tuple[Chunk, float]], k: int, max_per_paper: int
) -> list[tuple[Chunk, float]]:
    """Best-first, at most `max_per_paper` chunks from any one paper."""
    out: list[tuple[Chunk, float]] = []
    per: dict[int, int] = {}
    for chunk, score in sorted(hits, key=lambda h: h[1], reverse=True):
        if per.get(chunk.ref, 0) >= max_per_paper:
            continue
        per[chunk.ref] = per.get(chunk.ref, 0) + 1
        out.append((chunk, score))
        if len(out) >= k:
            break
    return out


class ChromaStore:
    name = "chroma"

    def __init__(self, path: Path) -> None:
        import chromadb
        from chromadb.config import Settings

        path.mkdir(parents=True, exist_ok=True)
        # Telemetry off: it would contact a host outside our allowlist (SECURITY D-1).
        self._client = chromadb.PersistentClient(
            path=str(path), settings=Settings(anonymized_telemetry=False)
        )
        self._lock = threading.Lock()

    def _col(self, job_id: UUID):
        return self._client.get_or_create_collection(
            _collection_name(job_id),
            embedding_function=None,  # we always pass our own vectors
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, job_id: UUID, chunks: list[Chunk], vectors: np.ndarray) -> None:
        if not chunks:
            return
        with self._lock:
            self._col(job_id).add(
                ids=[f"{i}-{c.id}" for i, c in enumerate(chunks)],
                embeddings=[v.tolist() for v in vectors],
                documents=[c.text for c in chunks],
                metadatas=[
                    {"ref": c.ref, "arxiv_id": c.arxiv_id, "page": c.page}
                    for c in chunks
                ],
            )

    def query(
        self, job_id: UUID, vector: np.ndarray, *, k: int, max_per_paper: int
    ) -> list[tuple[Chunk, float]]:
        with self._lock:
            col = self._col(job_id)
            n = col.count()
            if n == 0:
                return []
            res = col.query(
                query_embeddings=[vector.tolist()],
                n_results=min(n, k * 4),  # over-fetch, then diversify
                include=["documents", "metadatas", "distances"],
            )
        hits = [
            (
                Chunk(int(m["ref"]), str(m["arxiv_id"]), int(m["page"]), str(doc)),
                round(1.0 - float(dist), 4),
            )
            for doc, m, dist in zip(
                res["documents"][0],
                res["metadatas"][0],
                res["distances"][0],
                strict=True,
            )
        ]
        return _diverse(hits, k, max_per_paper)

    def count(self, job_id: UUID) -> int:
        with self._lock:
            return self._col(job_id).count()

    def delete(self, job_id: UUID) -> None:
        with self._lock:
            try:
                self._client.delete_collection(_collection_name(job_id))
            except Exception:  # noqa: S110 - missing collection is fine
                pass


class NumpyStore:
    """Fallback if ChromaDB can't be installed/imported. Persists to .npz + .json."""

    name = "numpy"

    def __init__(self, path: Path) -> None:
        self._dir = path.resolve()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._mem: dict[UUID, tuple[list[Chunk], np.ndarray]] = {}
        self._lock = threading.Lock()

    def _paths(self, job_id: UUID) -> tuple[Path, Path]:
        base = self._dir / _collection_name(job_id)
        return base.with_suffix(".npz"), base.with_suffix(".json")

    def _load(self, job_id: UUID) -> tuple[list[Chunk], np.ndarray]:
        if job_id in self._mem:
            return self._mem[job_id]
        vec_path, meta_path = self._paths(job_id)
        if vec_path.is_file() and meta_path.is_file():
            vecs = np.load(vec_path)["v"]
            chunks = [Chunk(**c) for c in json.loads(meta_path.read_text("utf-8"))]
            self._mem[job_id] = (chunks, vecs)
        else:
            self._mem[job_id] = ([], np.zeros((0, 384), dtype=np.float32))
        return self._mem[job_id]

    def add(self, job_id: UUID, chunks: list[Chunk], vectors: np.ndarray) -> None:
        if not chunks:
            return
        with self._lock:
            old_chunks, old_vecs = self._load(job_id)
            all_chunks = old_chunks + chunks
            all_vecs = (
                np.vstack([old_vecs, vectors])
                if len(old_chunks)
                else vectors.astype(np.float32)
            )
            self._mem[job_id] = (all_chunks, all_vecs)
            vec_path, meta_path = self._paths(job_id)
            np.savez(vec_path, v=all_vecs)
            meta_path.write_text(json.dumps([asdict(c) for c in all_chunks]), "utf-8")

    def query(
        self, job_id: UUID, vector: np.ndarray, *, k: int, max_per_paper: int
    ) -> list[tuple[Chunk, float]]:
        with self._lock:
            chunks, vecs = self._load(job_id)
        if not chunks:
            return []
        scores = vecs @ vector
        top = np.argsort(-scores)[: k * 4]
        hits = [(chunks[i], round(float(scores[i]), 4)) for i in top]
        return _diverse(hits, k, max_per_paper)

    def count(self, job_id: UUID) -> int:
        with self._lock:
            return len(self._load(job_id)[0])

    def delete(self, job_id: UUID) -> None:
        with self._lock:
            self._mem.pop(job_id, None)
            for p in self._paths(job_id):
                p.unlink(missing_ok=True)


def make_vector_store(data_dir: Path) -> VectorStore:
    try:
        return ChromaStore(data_dir / "chroma")
    except Exception as e:  # import or init failure
        log.warning(
            "ChromaDB unavailable (%s); using NumPy vector store", type(e).__name__
        )
        return NumpyStore(data_dir / "vectors")
