"""Semantic file search tool for the AI agent."""

from __future__ import annotations

import logging

from pocketpaw.tools.protocol import BaseTool

logger = logging.getLogger(__name__)

_search_service = None


def _get_search_service():
    global _search_service
    if _search_service is None:
        # Lazy import to avoid circular deps
        from pocketpaw.api.v1.search import _search_service as api_svc

        return api_svc
    return _search_service


class SemanticSearchTool(BaseTool):
    """Search files in the workspace by meaning using Gemini embeddings."""

    @property
    def name(self) -> str:
        return "semantic_search"

    @property
    def description(self) -> str:
        return (
            "Search files in the workspace by meaning. Finds code, documents, "
            "images, videos, and other files matching a natural language query. "
            "Use this when you need to find relevant files without knowing exact names."
        )

    @property
    def trust_level(self) -> str:
        return "standard"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 10)",
                    "default": 10,
                },
                "file_types": {
                    "type": "string",
                    "description": (
                        "Comma-separated filter: code,image,video,audio,text,structured,pdf"
                    ),
                },
                "search_mode": {
                    "type": "string",
                    "enum": ["metadata", "content", "hybrid"],
                    "description": "Search mode (default: hybrid)",
                    "default": "hybrid",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        if not query:
            return self._error("query is required")

        svc = _get_search_service()
        if svc is None:
            return self._error("Semantic search is not enabled. Enable it in settings.")

        top_k = kwargs.get("top_k", 10)
        file_types = kwargs.get("file_types")
        search_mode = kwargs.get("search_mode", "hybrid")

        ft = file_types.split(",") if file_types else None

        try:
            results = await svc.search(
                query,
                top_k=top_k,
                file_types=ft,
                search_mode=search_mode,
            )
        except Exception as e:
            logger.exception("Semantic search failed")
            return self._error(f"Search failed: {e}")

        if not results:
            return "No matching files found."

        lines = [f"Found {len(results)} relevant files:\n"]
        for i, r in enumerate(results, 1):
            fp = r.metadata.get("file_path", "unknown")
            name = r.metadata.get("file_name", "")
            preview = r.metadata.get("content_preview", "")
            score = f"{r.score:.2f}"
            lines.append(f"{i}. **{name or fp}** (relevance: {score})")
            lines.append(f"   Path: {fp}")
            if preview:
                lines.append(f"   Preview: {preview[:150]}")
            lines.append("")

        return "\n".join(lines)
