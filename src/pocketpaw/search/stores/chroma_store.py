from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb

from pocketpaw.search.vector_store import SearchResult

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    def __init__(self, persist_dir: str | None = None) -> None:
        self._persist_dir = persist_dir
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    async def initialize(self, collection: str, dimensions: int) -> None:
        if self._persist_dir:
            Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self._persist_dir)
        else:
            self._client = chromadb.Client()
        self._collection = self._client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )
        self._dimensions = dimensions

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadata: list[dict[str, Any]],
    ) -> None:
        assert self._collection is not None
        # ChromaDB does not accept None values in metadata
        clean_meta = [{k: v for k, v in m.items() if v is not None} for m in metadata]
        self._collection.upsert(ids=ids, embeddings=embeddings, metadatas=clean_meta)

    async def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        assert self._collection is not None
        where = filters if filters else None
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self._collection.count() or 1),
            where=where,
        )
        out: list[SearchResult] = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                score = 1.0 - (results["distances"][0][i] if results["distances"] else 0.0)
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                out.append(SearchResult(id=doc_id, score=score, metadata=meta))
        return out

    async def delete(self, ids: list[str]) -> None:
        assert self._collection is not None
        self._collection.delete(ids=ids)

    async def delete_by_filter(self, filters: dict[str, Any]) -> None:
        assert self._collection is not None
        self._collection.delete(where=filters)

    async def count(self) -> int:
        assert self._collection is not None
        return self._collection.count()

    async def close(self) -> None:
        self._client = None
        self._collection = None
