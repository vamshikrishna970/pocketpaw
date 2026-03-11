"""Integration test: index files and search them (uses mocked Gemini API)."""

import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from pocketpaw.search.indexer import Indexer
from pocketpaw.search.service import SearchService
from pocketpaw.search.stores.chroma_store import ChromaVectorStore


@pytest.fixture
def mock_embedder():
    """Returns deterministic embeddings based on content hash."""

    def _embed(chunks):
        results = []
        for chunk in chunks:
            content = chunk.content if isinstance(chunk.content, str) else str(chunk.content[:20])
            h = hashlib.md5(content.encode()).hexdigest()
            vec = [int(c, 16) / 15.0 for c in h[:8]]  # 8-dim vector from hash
            results.append(vec)
        return results

    embedder = AsyncMock()
    embedder.embed_chunks.side_effect = _embed
    embedder.embed_query.side_effect = lambda q: _embed([MagicMock(content=q)])[0]
    return embedder


@pytest.fixture
async def stores(tmp_path):
    meta = ChromaVectorStore(str(tmp_path / "meta"))
    content = ChromaVectorStore(str(tmp_path / "content"))
    await meta.initialize("file_metadata", 8)
    await content.initialize("file_contents", 8)
    return meta, content


@pytest.mark.asyncio
async def test_index_and_search(tmp_path, mock_embedder, stores):
    meta_store, content_store = stores

    # Create test files in a dedicated subdirectory
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "auth.py").write_text("def authenticate(user, pwd):\n    return check(user, pwd)\n")
    (src_dir / "readme.md").write_text("# My Project\n\nThis is a web app.\n")
    (src_dir / "data.json").write_text('{"users": [1, 2], "config": {}}')

    manifest_dir = tmp_path / "manifest_data"
    manifest_dir.mkdir()

    indexer = Indexer(
        embedder=mock_embedder,
        metadata_store=meta_store,
        content_store=content_store,
        manifest_dir=str(manifest_dir),
    )

    stats = await indexer.index_directory(str(src_dir))
    assert stats["indexed"] == 3

    service = SearchService(
        embedder=mock_embedder,
        metadata_store=meta_store,
        content_store=content_store,
    )

    results = await service.search("authenticate", top_k=5)
    assert len(results) >= 1
