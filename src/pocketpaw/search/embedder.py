from __future__ import annotations

import asyncio
import logging
import re

from pocketpaw.search.chunkers.protocol import Chunk

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]

_CODE_PATTERN = re.compile(r"[{}\[\]();=<>]|def |class |function |import |from ")


class EmbeddingService:
    """Wraps Gemini Embedding API for text and multimodal content."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-embedding-2-preview",
        dimensions: int = 768,
    ) -> None:
        if genai is None:
            raise ImportError("google-genai is required: pip install google-genai")
        self._model = model
        self._dimensions = dimensions
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()

    async def embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        """Embed a list of chunks. Returns one embedding per chunk."""
        results: list[list[float]] = []
        for chunk in chunks:
            emb = await self._embed_single(chunk)
            results.append(emb)
        return results

    async def embed_query(self, query: str) -> list[float]:
        """Embed a search query with appropriate task type."""
        task_type = "CODE_RETRIEVAL_QUERY" if _CODE_PATTERN.search(query) else "RETRIEVAL_QUERY"
        config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=self._dimensions,
        )
        result = await asyncio.to_thread(
            self._client.models.embed_content,
            model=self._model,
            contents=query,
            config=config,
        )
        return result.embeddings[0].values

    async def _embed_single(self, chunk: Chunk) -> list[float]:
        """Embed a single chunk, handling text vs binary content."""
        if isinstance(chunk.content, str):
            return await self._embed_text(chunk.content)
        else:
            return await self._embed_binary(
                chunk.content, chunk.mime_type or "application/octet-stream"
            )

    async def _embed_text(self, text: str) -> list[float]:
        config = types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=self._dimensions,
        )
        result = await asyncio.to_thread(
            self._client.models.embed_content,
            model=self._model,
            contents=text,
            config=config,
        )
        return result.embeddings[0].values

    async def _embed_binary(self, data: bytes, mime_type: str) -> list[float]:
        content = types.Part.from_bytes(data=data, mime_type=mime_type)
        config = types.EmbedContentConfig(
            output_dimensionality=self._dimensions,
        )
        result = await asyncio.to_thread(
            self._client.models.embed_content,
            model=self._model,
            contents=[content],
            config=config,
        )
        return result.embeddings[0].values
