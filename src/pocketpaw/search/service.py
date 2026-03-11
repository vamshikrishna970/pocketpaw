from __future__ import annotations

import logging
import time
from typing import Any

from pocketpaw.search.embedder import EmbeddingService
from pocketpaw.search.vector_store import SearchResult

logger = logging.getLogger(__name__)


class SearchService:
    """Unified semantic search interface."""

    def __init__(
        self,
        embedder: EmbeddingService,
        metadata_store: Any,
        content_store: Any,
    ) -> None:
        self._embedder = embedder
        self._meta_store = metadata_store
        self._content_store = content_store

    async def search(
        self,
        query: str,
        top_k: int = 10,
        file_types: list[str] | None = None,
        extensions: list[str] | None = None,
        directories: list[str] | None = None,
        search_mode: str = "hybrid",
    ) -> list[SearchResult]:
        """Search the index. Modes: metadata, content, hybrid."""
        start = time.monotonic()
        query_embedding = await self._embedder.embed_query(query)

        results: list[SearchResult] = []

        if search_mode in ("metadata", "hybrid"):
            meta_results = await self._meta_store.query(
                query_embedding,
                top_k=top_k,
            )
            results.extend(meta_results)

        if search_mode in ("content", "hybrid"):
            content_results = await self._content_store.query(
                query_embedding,
                top_k=top_k,
            )
            results.extend(content_results)

        # Filter by file type
        if file_types:
            results = [
                r
                for r in results
                if r.metadata.get("chunk_type", "") in file_types
                or r.metadata.get("file_type", "") in file_types
            ]

        # Filter by extension
        if extensions:
            results = [
                r
                for r in results
                if r.metadata.get("extension", "") in extensions
                or any(r.metadata.get("file_path", "").endswith(e) for e in extensions)
            ]

        # Filter by directory scope
        if directories:
            results = [
                r
                for r in results
                if any(r.metadata.get("file_path", "").startswith(d) for d in directories)
            ]

        # Deduplicate by file_path, keep highest score
        seen: dict[str, SearchResult] = {}
        for r in results:
            fp = r.metadata.get("file_path", r.id)
            if fp not in seen or r.score > seen[fp].score:
                seen[fp] = r
        results = sorted(seen.values(), key=lambda r: r.score, reverse=True)[:top_k]

        elapsed = (time.monotonic() - start) * 1000
        logger.debug("Search for %r took %.1fms, %d results", query, elapsed, len(results))
        return results
