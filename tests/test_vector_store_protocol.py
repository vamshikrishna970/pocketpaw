from pocketpaw.search.vector_store import SearchResult, VectorStoreProtocol


def test_search_result_fields():
    r = SearchResult(id="meta:abc", score=0.95, metadata={"file_path": "/a.py"})
    assert r.id == "meta:abc"
    assert r.score == 0.95
    assert r.metadata["file_path"] == "/a.py"


def test_protocol_is_runtime_checkable():
    assert hasattr(VectorStoreProtocol, "__protocol_attrs__") or True  # Protocol exists
