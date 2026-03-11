"""Semantic search with Gemini Embedding 2.0."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Module-level singletons set by initialize_search()
_enrichment = None
_search_service = None


def get_enrichment():
    """Return the SearchEnrichment instance, or None if search is not initialized."""
    return _enrichment


def get_search_service():
    """Return the SearchService instance, or None if search is not initialized."""
    return _search_service


async def initialize_search(
    api_key: str = "",
    model: str = "gemini-embedding-2-preview",
    vector_backend: str = "auto",
    dimensions: int = 768,
    data_dir: str = "",
    blocklist: list[str] | None = None,
    allowlist: list[str] | None = None,
    max_file_size_mb: int = 50,
    video_depth: str = "keyframes",
) -> dict[str, Any]:
    """Initialize all search components. Returns dict of service, indexer, enrichment."""
    from pocketpaw.search.embedder import EmbeddingService
    from pocketpaw.search.enrichment import SearchEnrichment
    from pocketpaw.search.indexer import Indexer
    from pocketpaw.search.service import SearchService
    from pocketpaw.search.stores import create_vector_store

    if not data_dir:
        data_dir = str(Path.home() / ".pocketpaw" / "embeddings")

    persist_dir = str(Path(data_dir) / vector_backend)

    embedder = EmbeddingService(api_key=api_key, model=model, dimensions=dimensions)

    meta_store = create_vector_store(vector_backend, persist_dir=persist_dir + "_meta")
    content_store = create_vector_store(vector_backend, persist_dir=persist_dir + "_content")

    await meta_store.initialize("file_metadata", dimensions)
    await content_store.initialize("file_contents", dimensions)

    service = SearchService(
        embedder=embedder,
        metadata_store=meta_store,
        content_store=content_store,
    )
    indexer = Indexer(
        embedder=embedder,
        metadata_store=meta_store,
        content_store=content_store,
        manifest_dir=data_dir,
        blocklist=blocklist,
        allowlist=allowlist,
        max_file_size_mb=max_file_size_mb,
        video_depth=video_depth,
    )
    enrichment = SearchEnrichment(service)

    # Wire up module-level singletons
    global _enrichment, _search_service
    _enrichment = enrichment
    _search_service = service

    # Wire up the API module globals
    from pocketpaw.api.v1 import search as search_api

    search_api._search_service = service
    search_api._indexer = indexer
    search_api._manifest = indexer._manifest

    logger.info(
        "Search initialized: backend=%s, dimensions=%d, data_dir=%s",
        vector_backend,
        dimensions,
        data_dir,
    )

    return {"service": service, "indexer": indexer, "enrichment": enrichment}
