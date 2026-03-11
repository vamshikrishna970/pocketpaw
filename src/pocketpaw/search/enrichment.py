from __future__ import annotations

import logging

from pocketpaw.search.service import SearchService

logger = logging.getLogger(__name__)


class SearchEnrichment:
    """Auto-enriches agent context with semantically relevant files."""

    def __init__(self, search_service: SearchService, top_k: int = 5) -> None:
        self._service = search_service
        self._top_k = top_k

    async def enrich(self, query: str) -> str:
        """Return context string for relevant files, or empty string."""
        if not query.strip():
            return ""

        try:
            results = await self._service.search(
                query,
                top_k=self._top_k,
                search_mode="hybrid",
            )
        except Exception:
            logger.exception("Auto-enrichment search failed")
            return ""

        if not results:
            return ""

        lines = ["[Potentially relevant files from workspace index]"]
        for r in results:
            fp = r.metadata.get("file_path", "")
            preview = r.metadata.get("content_preview", "")
            score = f"{r.score:.2f}"
            entry = f"- {fp} (relevance: {score})"
            if preview:
                entry += f" | {preview[:100]}"
            lines.append(entry)

        return "\n".join(lines)
