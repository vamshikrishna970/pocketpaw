from unittest.mock import AsyncMock

import pytest

from pocketpaw.search.service import SearchService
from pocketpaw.search.vector_store import SearchResult


@pytest.fixture
def mock_embedder():
    e = AsyncMock()
    e.embed_query.return_value = [0.1] * 8
    return e


@pytest.fixture
def mock_meta_store():
    s = AsyncMock()
    s.query.return_value = [
        SearchResult(
            id="meta:abc",
            score=0.9,
            metadata={"file_path": "/a.py", "file_name": "a.py"},
        ),
    ]
    return s


@pytest.fixture
def mock_content_store():
    s = AsyncMock()
    s.query.return_value = [
        SearchResult(
            id="chunk:abc:0",
            score=0.85,
            metadata={"file_path": "/a.py", "content_preview": "def hello():"},
        ),
    ]
    return s


@pytest.fixture
def service(mock_embedder, mock_meta_store, mock_content_store):
    return SearchService(
        embedder=mock_embedder,
        metadata_store=mock_meta_store,
        content_store=mock_content_store,
    )


@pytest.mark.asyncio
async def test_search_hybrid(service):
    results = await service.search("hello function", search_mode="hybrid")
    assert len(results) >= 1
    assert results[0].metadata["file_path"] == "/a.py"


@pytest.mark.asyncio
async def test_search_metadata_only(service):
    results = await service.search("a.py", search_mode="metadata")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_search_content_only(service):
    results = await service.search("def hello", search_mode="content")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_search_with_file_type_filter(service, mock_content_store):
    mock_content_store.query.return_value = [
        SearchResult(
            id="chunk:1",
            score=0.9,
            metadata={"file_path": "/img.png", "chunk_type": "image"},
        ),
        SearchResult(
            id="chunk:2",
            score=0.8,
            metadata={"file_path": "/a.py", "chunk_type": "code"},
        ),
    ]
    results = await service.search("hello", file_types=["code"])
    code_results = [r for r in results if r.metadata.get("chunk_type") == "code"]
    assert len(code_results) >= 1
