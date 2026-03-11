from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pocketpaw.search.vector_store import SearchResult

logger = logging.getLogger(__name__)


class ZvecVectorStore:
    """Vector store backed by zvec (Linux/macOS only)."""

    def __init__(self, persist_dir: str | None = None) -> None:
        self._persist_dir = persist_dir
        self._collection_name: str = ""
        self._dimensions: int = 0
        self._db = None
        self._metadata_path: Path | None = None
        self._metadata: dict[str, dict[str, Any]] = {}

    async def initialize(self, collection: str, dimensions: int) -> None:
        import zvec

        self._collection_name = collection
        self._dimensions = dimensions

        if self._persist_dir:
            Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
            db_path = str(Path(self._persist_dir) / f"{collection}.zvec")
            self._metadata_path = Path(self._persist_dir) / f"{collection}_meta.json"
        else:
            db_path = f"/tmp/{collection}.zvec"
            self._metadata_path = Path(f"/tmp/{collection}_meta.json")

        schema = zvec.VectorSchema(
            name="embedding",
            data_type=zvec.DataType.VECTOR_FP32,
            dimension=dimensions,
        )
        self._db = zvec.Collection.create_and_open(db_path, schema=schema)

        # Load metadata sidecar
        if self._metadata_path.exists():
            self._metadata = json.loads(self._metadata_path.read_text())

    def _save_metadata(self) -> None:
        if self._metadata_path:
            self._metadata_path.write_text(json.dumps(self._metadata))

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadata: list[dict[str, Any]],
    ) -> None:
        assert self._db is not None
        for doc_id, emb, meta in zip(ids, embeddings, metadata):
            self._db.insert({"id": doc_id, "embedding": emb})
            self._metadata[doc_id] = meta
        self._save_metadata()

    async def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        assert self._db is not None
        import zvec

        q = zvec.VectorQuery(vector=embedding, topk=top_k)
        raw_results = self._db.query(q)

        out: list[SearchResult] = []
        for item in raw_results:
            doc_id = item["id"]
            meta = self._metadata.get(doc_id, {})
            if filters:
                if not all(meta.get(k) == v for k, v in filters.items()):
                    continue
            out.append(SearchResult(id=doc_id, score=item["score"], metadata=meta))
        return out

    async def delete(self, ids: list[str]) -> None:
        # zvec doesn't have native delete; track in metadata
        for doc_id in ids:
            self._metadata.pop(doc_id, None)
        self._save_metadata()

    async def delete_by_filter(self, filters: dict[str, Any]) -> None:
        to_remove = [
            k
            for k, v in self._metadata.items()
            if all(v.get(fk) == fv for fk, fv in filters.items())
        ]
        for doc_id in to_remove:
            self._metadata.pop(doc_id, None)
        self._save_metadata()

    async def count(self) -> int:
        return len(self._metadata)

    async def close(self) -> None:
        self._db = None
        self._metadata = {}
