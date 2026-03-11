import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="zvec not available on Windows")

from pocketpaw.search.stores.zvec_store import ZvecVectorStore  # noqa: E402


@pytest.fixture
async def store(tmp_path):
    s = ZvecVectorStore(persist_dir=str(tmp_path / "zvec"))
    await s.initialize("test_collection", dimensions=8)
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_upsert_and_query(store):
    await store.upsert(
        ["doc1", "doc2"],
        [
            [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ],
        [{"file_path": "/a.py"}, {"file_path": "/b.py"}],
    )
    assert await store.count() == 2
    results = await store.query([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], top_k=1)
    assert len(results) == 1
    assert results[0].id == "doc1"


@pytest.mark.asyncio
async def test_delete(store):
    await store.upsert(["doc1"], [[1.0] * 8], [{"file_path": "/a.py"}])
    await store.delete(["doc1"])
    assert await store.count() == 0
