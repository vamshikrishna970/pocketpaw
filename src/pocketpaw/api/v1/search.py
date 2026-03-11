"""Semantic search API endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Search"])

_search_service = None
_indexer = None
_manifest = None


def _get_search_service():
    global _search_service
    if _search_service is None:
        raise HTTPException(503, "Search service not initialized. Enable search in settings.")
    return _search_service


def _get_indexer():
    global _indexer
    if _indexer is None:
        raise HTTPException(503, "Indexer not initialized.")
    return _indexer


def _get_manifest():
    global _manifest
    if _manifest is None:
        raise HTTPException(503, "Search not initialized.")
    return _manifest


class SearchResultItem(BaseModel):
    id: str
    score: float
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    took_ms: float = 0.0


class IndexRequest(BaseModel):
    path: str
    recursive: bool = True


class IndexStatusResponse(BaseModel):
    indexing: bool = False
    progress: dict[str, int] = {}


class StatsResponse(BaseModel):
    total_files: int = 0
    total_chunks: int = 0


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(10, ge=1, le=100),
    mode: str = Query("hybrid", pattern="^(metadata|content|hybrid)$"),
    file_types: str | None = Query(
        None, description="Comma-separated: code,image,video,audio,text"
    ),
    extensions: str | None = Query(None, description="Comma-separated: .py,.js,.ts"),
    directories: str | None = Query(None, description="Comma-separated directory paths"),
):
    import time

    start = time.monotonic()
    svc = _get_search_service()
    ft = file_types.split(",") if file_types else None
    ext = extensions.split(",") if extensions else None
    dirs = directories.split(",") if directories else None

    results = await svc.search(
        q,
        top_k=top_k,
        file_types=ft,
        extensions=ext,
        directories=dirs,
        search_mode=mode,
    )
    took = (time.monotonic() - start) * 1000
    return SearchResponse(
        results=[SearchResultItem(id=r.id, score=r.score, metadata=r.metadata) for r in results],
        took_ms=round(took, 1),
    )


@router.post("/search/index")
async def trigger_index(req: IndexRequest):
    indexer = _get_indexer()
    import asyncio

    asyncio.create_task(indexer.index_directory(req.path, recursive=req.recursive))
    return {"status": "indexing_started", "path": req.path}


@router.delete("/search/index")
async def remove_from_index(path: str = Query(...)):
    indexer = _get_indexer()
    removed = await indexer.remove_directory(path)
    return {"status": "removed", "path": path, "files_removed": removed}


@router.get("/search/stats", response_model=StatsResponse)
async def get_stats():
    manifest = _get_manifest()
    stats = manifest.stats()
    return StatsResponse(**stats)
