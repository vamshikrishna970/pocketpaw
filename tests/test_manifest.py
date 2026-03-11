import pytest

from pocketpaw.search.manifest import IndexManifest


@pytest.fixture
def manifest(tmp_path):
    return IndexManifest(tmp_path / "manifest.json")


def test_empty_manifest(manifest):
    assert manifest.get_file("/a.py") is None
    assert manifest.stats()["total_files"] == 0


def test_set_and_get(manifest):
    manifest.set_file("/a.py", content_hash="abc123", chunk_count=3)
    entry = manifest.get_file("/a.py")
    assert entry is not None
    assert entry["content_hash"] == "abc123"
    assert entry["chunk_count"] == 3


def test_needs_reindex(manifest):
    assert manifest.needs_reindex("/a.py", "abc123") is True
    manifest.set_file("/a.py", content_hash="abc123", chunk_count=1)
    assert manifest.needs_reindex("/a.py", "abc123") is False
    assert manifest.needs_reindex("/a.py", "def456") is True


def test_remove_file(manifest):
    manifest.set_file("/a.py", content_hash="abc", chunk_count=1)
    manifest.remove_file("/a.py")
    assert manifest.get_file("/a.py") is None


def test_persistence(tmp_path):
    path = tmp_path / "manifest.json"
    m1 = IndexManifest(path)
    m1.set_file("/a.py", content_hash="abc", chunk_count=2)
    m1.save()

    m2 = IndexManifest(path)
    assert m2.get_file("/a.py")["content_hash"] == "abc"
