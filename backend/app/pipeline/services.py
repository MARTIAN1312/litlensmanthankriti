"""Long-lived objects shared by all requests, built once at startup."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.config import Settings
from app.llm.router import LLMRouter, build_router
from app.pipeline.jobs import JobRegistry
from app.retrieval.embeddings import Embedder, SentenceTransformerEmbedder
from app.services.arxiv_client import ArxivClient
from app.services.cache import Cache


@dataclass
class Services:
    settings: Settings
    cache: Cache
    router: LLMRouter
    arxiv: ArxivClient
    embedder: Embedder
    jobs: JobRegistry
    # One pipeline at a time: protects the free quota and the demo laptop (DESIGN §3.8).
    pipeline_lock: asyncio.Semaphore = field(
        default_factory=lambda: asyncio.Semaphore(1)
    )


def build_services(settings: Settings) -> Services:
    cache = Cache(settings.data_dir / "cache.sqlite")
    return Services(
        settings=settings,
        cache=cache,
        router=build_router(settings, cache),
        arxiv=ArxivClient(
            cache, contact=settings.arxiv_contact, offline=settings.demo_mode
        ),
        embedder=SentenceTransformerEmbedder(allow_download=not settings.demo_mode),
        jobs=JobRegistry(settings.data_dir / "reviews"),
    )
