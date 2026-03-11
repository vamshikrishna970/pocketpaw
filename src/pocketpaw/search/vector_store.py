from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class SearchResult:
    id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class VectorStoreProtocol(Protocol):
    async def initialize(self, collection: str, dimensions: int) -> None: ...

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadata: list[dict[str, Any]],
    ) -> None: ...

    async def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]: ...

    async def delete(self, ids: list[str]) -> None: ...

    async def delete_by_filter(self, filters: dict[str, Any]) -> None: ...

    async def count(self) -> int: ...

    async def close(self) -> None: ...
