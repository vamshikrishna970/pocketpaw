"""Vector store backends."""

from __future__ import annotations

import sys


def get_default_backend() -> str:
    if sys.platform == "win32":
        return "chroma"
    try:
        import zvec  # noqa: F401

        return "zvec"
    except ImportError:
        return "chroma"


def create_vector_store(backend: str = "auto", persist_dir: str | None = None):
    if backend == "auto":
        backend = get_default_backend()

    if backend == "chroma":
        from pocketpaw.search.stores.chroma_store import ChromaVectorStore

        return ChromaVectorStore(persist_dir=persist_dir)
    elif backend == "zvec":
        from pocketpaw.search.stores.zvec_store import ZvecVectorStore

        return ZvecVectorStore(persist_dir=persist_dir)
    else:
        raise ValueError(f"Unknown vector backend: {backend!r}")
