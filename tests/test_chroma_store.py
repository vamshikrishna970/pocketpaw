import pytest

from pocketpaw.search.stores.chroma_store import ChromaVectorStore


@pytest.fixture
async def store(tmp_path):
    s = ChromaVectorStore(persist_dir=str(tmp_path / "chroma"))
    await s.initialize("test_collection", dimensions=8)
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_upsert_and_query(store):
    ids = ["doc1", "doc2"]
    embeddings = [
        [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ]
    metadata = [{"file_path": "/a.py"}, {"file_path": "/b.py"}]
    await store.upsert(ids, embeddings, metadata)
    assert await store.count() == 2

    results = await store.query([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], top_k=1)
    assert len(results) == 1
    assert results[0].id == "doc1"


@pytest.mark.asyncio
async def test_delete(store):
    await store.upsert(["doc1"], [[1.0] * 8], [{"file_path": "/a.py"}])
    assert await store.count() == 1
    await store.delete(["doc1"])
    assert await store.count() == 0


@pytest.mark.asyncio
async def test_delete_by_filter(store):
    await store.upsert(
        ["doc1", "doc2"],
        [[1.0] * 8, [0.0] + [1.0] * 7],
        [{"file_path": "/a.py"}, {"file_path": "/b.py"}],
    )
    await store.delete_by_filter({"file_path": "/a.py"})
    assert await store.count() == 1
