from unittest.mock import AsyncMock

import pytest

from pocketpaw.search.indexer import Indexer


@pytest.fixture
def mock_embedder():
    embedder = AsyncMock()
    embedder.embed_chunks.return_value = [[0.1] * 8]
    return embedder


@pytest.fixture
def mock_store():
    store = AsyncMock()
    store.count.return_value = 0
    return store


@pytest.fixture
def indexer(tmp_path, mock_embedder, mock_store):
    # Use a separate directory for manifest so it doesn't interfere with indexing
    manifest_dir = tmp_path / "manifest_data"
    manifest_dir.mkdir()
    return Indexer(
        embedder=mock_embedder,
        metadata_store=mock_store,
        content_store=mock_store,
        manifest_dir=str(manifest_dir),
        blocklist=[".git", "node_modules"],
    )


@pytest.mark.asyncio
async def test_index_text_file(indexer, tmp_path):
    f = tmp_path / "hello.py"
    f.write_text("def hello():\n    print('hi')\n")
    await indexer.index_file(str(f))
    assert indexer._manifest.get_file(str(f)) is not None


@pytest.mark.asyncio
async def test_skip_blocklisted(indexer, tmp_path):
    d = tmp_path / "node_modules"
    d.mkdir()
    f = d / "pkg.js"
    f.write_text("module.exports = {}")
    await indexer.index_file(str(f))
    assert indexer._manifest.get_file(str(f)) is None


@pytest.mark.asyncio
async def test_skip_unchanged(indexer, tmp_path, mock_embedder):
    f = tmp_path / "hello.py"
    f.write_text("x = 1")
    await indexer.index_file(str(f))
    mock_embedder.embed_chunks.reset_mock()
    await indexer.index_file(str(f))
    mock_embedder.embed_chunks.assert_not_called()


@pytest.mark.asyncio
async def test_index_directory(tmp_path, mock_embedder, mock_store):
    # Create source files in a dedicated subdirectory
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.py").write_text("a = 1")
    (src_dir / "b.txt").write_text("hello")
    git_dir = src_dir / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("ignore me")

    manifest_dir = tmp_path / "manifest_data"
    manifest_dir.mkdir()

    indexer = Indexer(
        embedder=mock_embedder,
        metadata_store=mock_store,
        content_store=mock_store,
        manifest_dir=str(manifest_dir),
        blocklist=[".git", "node_modules"],
    )

    stats = await indexer.index_directory(str(src_dir))
    assert stats["indexed"] == 2
    assert stats["skipped"] >= 0
