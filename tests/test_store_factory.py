import sys

import pytest

from pocketpaw.search.stores import create_vector_store, get_default_backend


def test_default_backend_windows():
    if sys.platform == "win32":
        assert get_default_backend() == "chroma"


def test_create_chroma(tmp_path):
    store = create_vector_store("chroma", persist_dir=str(tmp_path))
    from pocketpaw.search.stores.chroma_store import ChromaVectorStore

    assert isinstance(store, ChromaVectorStore)


def test_create_auto(tmp_path):
    store = create_vector_store("auto", persist_dir=str(tmp_path))
    assert store is not None


def test_create_invalid():
    with pytest.raises(ValueError, match="Unknown"):
        create_vector_store("invalid_backend")
