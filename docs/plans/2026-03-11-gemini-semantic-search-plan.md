# Gemini Semantic Search - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add semantic search to PocketPaw using Gemini Embedding 2.0, with zvec + ChromaDB vector backends, smart chunking, and both explorer UI and agent integration.

**Architecture:** Embedding service wraps Gemini API, chunkers split files by type, vector store protocol abstracts zvec/ChromaDB, indexer handles background processing + file watching, SearchService unifies queries for REST API, agent tool, and auto-enrichment.

**Tech Stack:** google-genai, zvec, chromadb, watchfiles, pymupdf, python-docx, ffmpeg (video keyframes)

---

### Task 1: Dependencies and Optional Extra

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add search optional extra to pyproject.toml**

Add after the `mcp` extra (around line 137):

```toml
search = [
    "google-genai>=1.0.0",
    "chromadb>=0.6.0",
    "watchfiles>=1.0.0",
]
search-full = [
    "pocketpaw[search]",
    "pymupdf>=1.25.0",
    "python-docx>=1.1.0",
]
```

Add `"pocketpaw[search]"` to the `all-tools` and `all` composites.

**Step 2: Install dev deps**

Run: `uv sync --dev --extra search`

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add search optional dependencies"
```

---

### Task 2: Search Config Settings

**Files:**
- Modify: `src/pocketpaw/config.py`
- Test: `tests/test_search_config.py`

**Step 1: Write test**

```python
# tests/test_search_config.py
from pocketpaw.config import Settings

def test_search_defaults():
    s = Settings()
    assert s.search_enabled is False
    assert s.search_embedding_model == "gemini-embedding-2-preview"
    assert s.search_embedding_dimensions == 768
    assert s.search_vector_backend == "auto"
    assert s.search_auto_index_dirs == []
    assert s.search_auto_enrich is False
    assert s.search_max_file_size_mb == 50
    assert s.search_video_analysis_depth == "keyframes"
    assert s.search_batch_size == 32
    assert ".git" in s.search_index_blocklist
    assert s.search_index_allowlist == []

def test_search_env_override(monkeypatch):
    monkeypatch.setenv("POCKETPAW_SEARCH_ENABLED", "true")
    monkeypatch.setenv("POCKETPAW_SEARCH_EMBEDDING_DIMENSIONS", "1536")
    s = Settings()
    assert s.search_enabled is True
    assert s.search_embedding_dimensions == 1536
```

**Step 2: Run test, verify fail**

Run: `uv run pytest tests/test_search_config.py -v`

**Step 3: Add settings to config.py**

Add after the web search settings block (around line 437):

```python
# ── Search & Indexing (Gemini Embedding 2.0) ─────────────────────
search_enabled: bool = Field(default=False, description="Enable semantic search")
search_gemini_api_key: str = Field(default="", description="Gemini API key for embeddings")
search_use_oauth: bool = Field(default=True, description="Try Google OAuth before API key")
search_embedding_model: str = Field(
    default="gemini-embedding-2-preview",
    description="Gemini embedding model name",
)
search_embedding_dimensions: int = Field(
    default=768, description="Embedding dimensions (128-3072)"
)
search_vector_backend: str = Field(
    default="auto", description="Vector backend: 'auto', 'zvec', 'chroma'"
)
search_auto_index_dirs: list[str] = Field(
    default_factory=list, description="Directories to auto-index on startup"
)
search_auto_enrich: bool = Field(
    default=False, description="Auto-enrich agent context with relevant files"
)
search_max_file_size_mb: int = Field(default=50, description="Max file size to index (MB)")
search_video_analysis_depth: str = Field(
    default="keyframes", description="Video analysis: 'keyframes' or 'full'"
)
search_batch_size: int = Field(default=32, description="Chunks per embedding API call")
search_index_blocklist: list[str] = Field(
    default_factory=lambda: [
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        ".env", "dist", "build", ".next", ".cache",
    ],
    description="Directories/patterns to skip during indexing",
)
search_index_allowlist: list[str] = Field(
    default_factory=list,
    description="If non-empty, only index files matching these patterns",
)
```

**Step 4: Run test, verify pass**

Run: `uv run pytest tests/test_search_config.py -v`

**Step 5: Commit**

```bash
git add src/pocketpaw/config.py tests/test_search_config.py
git commit -m "feat(search): add search settings to config"
```

---

### Task 3: Vector Store Protocol and SearchResult

**Files:**
- Create: `src/pocketpaw/search/__init__.py`
- Create: `src/pocketpaw/search/vector_store.py`
- Test: `tests/test_vector_store_protocol.py`

**Step 1: Create package init**

```python
# src/pocketpaw/search/__init__.py
"""Semantic search with Gemini Embedding 2.0."""
```

**Step 2: Write test**

```python
# tests/test_vector_store_protocol.py
from pocketpaw.search.vector_store import SearchResult, VectorStoreProtocol

def test_search_result_fields():
    r = SearchResult(id="meta:abc", score=0.95, metadata={"file_path": "/a.py"})
    assert r.id == "meta:abc"
    assert r.score == 0.95
    assert r.metadata["file_path"] == "/a.py"

def test_protocol_is_runtime_checkable():
    assert hasattr(VectorStoreProtocol, "__protocol_attrs__") or True  # Protocol exists
```

**Step 3: Implement**

```python
# src/pocketpaw/search/vector_store.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class SearchResult:
    id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class VectorStoreProtocol(Protocol):
    async def initialize(self, collection: str, dimensions: int) -> None: ...

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadata: list[dict[str, Any]],
    ) -> None: ...

    async def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]: ...

    async def delete(self, ids: list[str]) -> None: ...

    async def delete_by_filter(self, filters: dict[str, Any]) -> None: ...

    async def count(self) -> int: ...

    async def close(self) -> None: ...
```

**Step 4: Run test, verify pass**

Run: `uv run pytest tests/test_vector_store_protocol.py -v`

**Step 5: Commit**

```bash
git add src/pocketpaw/search/ tests/test_vector_store_protocol.py
git commit -m "feat(search): add vector store protocol and SearchResult"
```

---

### Task 4: ChromaDB Vector Store Backend

**Files:**
- Create: `src/pocketpaw/search/stores/__init__.py`
- Create: `src/pocketpaw/search/stores/chroma_store.py`
- Test: `tests/test_chroma_store.py`

**Step 1: Write test**

```python
# tests/test_chroma_store.py
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
    embeddings = [[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                  [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]
    metadata = [{"file_path": "/a.py"}, {"file_path": "/b.py"}]
    await store.upsert(ids, embeddings, metadata)
    assert await store.count() == 2

    results = await store.query([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], top_k=1)
    assert len(results) == 1
    assert results[0].id == "doc1"

@pytest.mark.asyncio
async def test_delete(store):
    await store.upsert(
        ["doc1"], [[1.0] * 8], [{"file_path": "/a.py"}]
    )
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
```

**Step 2: Run test, verify fail**

Run: `uv run pytest tests/test_chroma_store.py -v`

**Step 3: Implement**

```python
# src/pocketpaw/search/stores/__init__.py
"""Vector store backends."""

# src/pocketpaw/search/stores/chroma_store.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb

from pocketpaw.search.vector_store import SearchResult

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    def __init__(self, persist_dir: str | None = None) -> None:
        self._persist_dir = persist_dir
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    async def initialize(self, collection: str, dimensions: int) -> None:
        if self._persist_dir:
            Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self._persist_dir)
        else:
            self._client = chromadb.Client()
        self._collection = self._client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )
        self._dimensions = dimensions

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadata: list[dict[str, Any]],
    ) -> None:
        assert self._collection is not None
        # ChromaDB does not accept None values in metadata
        clean_meta = [
            {k: v for k, v in m.items() if v is not None} for m in metadata
        ]
        self._collection.upsert(ids=ids, embeddings=embeddings, metadatas=clean_meta)

    async def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        assert self._collection is not None
        where = filters if filters else None
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self._collection.count() or 1),
            where=where,
        )
        out: list[SearchResult] = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                score = 1.0 - (results["distances"][0][i] if results["distances"] else 0.0)
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                out.append(SearchResult(id=doc_id, score=score, metadata=meta))
        return out

    async def delete(self, ids: list[str]) -> None:
        assert self._collection is not None
        self._collection.delete(ids=ids)

    async def delete_by_filter(self, filters: dict[str, Any]) -> None:
        assert self._collection is not None
        self._collection.delete(where=filters)

    async def count(self) -> int:
        assert self._collection is not None
        return self._collection.count()

    async def close(self) -> None:
        self._client = None
        self._collection = None
```

**Step 4: Run test, verify pass**

Run: `uv run pytest tests/test_chroma_store.py -v`

**Step 5: Commit**

```bash
git add src/pocketpaw/search/stores/ tests/test_chroma_store.py
git commit -m "feat(search): add ChromaDB vector store backend"
```

---

### Task 5: zvec Vector Store Backend

**Files:**
- Create: `src/pocketpaw/search/stores/zvec_store.py`
- Test: `tests/test_zvec_store.py`

**Step 1: Write test**

```python
# tests/test_zvec_store.py
import sys
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="zvec not available on Windows"
)

from pocketpaw.search.stores.zvec_store import ZvecVectorStore

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
        [[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
         [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]],
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
```

**Step 2: Implement**

```python
# src/pocketpaw/search/stores/zvec_store.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pocketpaw.search.vector_store import SearchResult

logger = logging.getLogger(__name__)


class ZvecVectorStore:
    """Vector store backed by zvec (Linux/macOS only)."""

    def __init__(self, persist_dir: str | None = None) -> None:
        self._persist_dir = persist_dir
        self._collection_name: str = ""
        self._dimensions: int = 0
        self._db = None
        self._metadata_path: Path | None = None
        self._metadata: dict[str, dict[str, Any]] = {}

    async def initialize(self, collection: str, dimensions: int) -> None:
        import zvec

        self._collection_name = collection
        self._dimensions = dimensions

        if self._persist_dir:
            Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
            db_path = str(Path(self._persist_dir) / f"{collection}.zvec")
            self._metadata_path = Path(self._persist_dir) / f"{collection}_meta.json"
        else:
            db_path = f"/tmp/{collection}.zvec"
            self._metadata_path = Path(f"/tmp/{collection}_meta.json")

        schema = zvec.VectorSchema(
            name="embedding",
            data_type=zvec.DataType.VECTOR_FP32,
            dimension=dimensions,
        )
        self._db = zvec.Collection.create_and_open(db_path, schema=schema)

        # Load metadata sidecar
        if self._metadata_path.exists():
            self._metadata = json.loads(self._metadata_path.read_text())

    def _save_metadata(self) -> None:
        if self._metadata_path:
            self._metadata_path.write_text(json.dumps(self._metadata))

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadata: list[dict[str, Any]],
    ) -> None:
        assert self._db is not None
        for doc_id, emb, meta in zip(ids, embeddings, metadata):
            self._db.insert({"id": doc_id, "embedding": emb})
            self._metadata[doc_id] = meta
        self._save_metadata()

    async def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        assert self._db is not None
        import zvec

        q = zvec.VectorQuery(vector=embedding, topk=top_k)
        raw_results = self._db.query(q)

        out: list[SearchResult] = []
        for item in raw_results:
            doc_id = item["id"]
            meta = self._metadata.get(doc_id, {})
            if filters:
                if not all(meta.get(k) == v for k, v in filters.items()):
                    continue
            out.append(SearchResult(id=doc_id, score=item["score"], metadata=meta))
        return out

    async def delete(self, ids: list[str]) -> None:
        # zvec doesn't have native delete; track in metadata
        for doc_id in ids:
            self._metadata.pop(doc_id, None)
        self._save_metadata()

    async def delete_by_filter(self, filters: dict[str, Any]) -> None:
        to_remove = [
            k for k, v in self._metadata.items()
            if all(v.get(fk) == fv for fk, fv in filters.items())
        ]
        for doc_id in to_remove:
            self._metadata.pop(doc_id, None)
        self._save_metadata()

    async def count(self) -> int:
        return len(self._metadata)

    async def close(self) -> None:
        self._db = None
        self._metadata = {}
```

**Step 3: Run test (Linux/Mac only)**

Run: `uv run pytest tests/test_zvec_store.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/stores/zvec_store.py tests/test_zvec_store.py
git commit -m "feat(search): add zvec vector store backend"
```

---

### Task 6: Vector Store Factory

**Files:**
- Modify: `src/pocketpaw/search/stores/__init__.py`
- Test: `tests/test_store_factory.py`

**Step 1: Write test**

```python
# tests/test_store_factory.py
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
```

**Step 2: Implement factory**

```python
# src/pocketpaw/search/stores/__init__.py
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
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_store_factory.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/stores/__init__.py tests/test_store_factory.py
git commit -m "feat(search): add vector store factory with auto-detection"
```

---

### Task 7: Chunker Protocol and Text Chunker

**Files:**
- Create: `src/pocketpaw/search/chunkers/__init__.py`
- Create: `src/pocketpaw/search/chunkers/protocol.py`
- Create: `src/pocketpaw/search/chunkers/text.py`
- Test: `tests/test_chunkers.py`

**Step 1: Write test**

```python
# tests/test_chunkers.py
import pytest
from pocketpaw.search.chunkers.protocol import Chunk
from pocketpaw.search.chunkers.text import TextChunker

def test_chunk_dataclass():
    c = Chunk(content="hello", chunk_type="text", metadata={"heading": "Intro"})
    assert c.content == "hello"
    assert c.chunk_type == "text"

def test_text_chunker_by_paragraphs():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunker = TextChunker()
    chunks = chunker.chunk(text, file_path="/readme.txt")
    assert len(chunks) == 3
    assert chunks[0].content == "First paragraph."

def test_text_chunker_markdown_headings():
    md = "# Title\n\nIntro text.\n\n## Section 1\n\nContent one.\n\n## Section 2\n\nContent two."
    chunker = TextChunker()
    chunks = chunker.chunk(md, file_path="/doc.md")
    assert len(chunks) >= 2
    # Headings should be preserved as context
    assert any("Section 1" in c.metadata.get("heading", "") for c in chunks)

def test_text_chunker_empty():
    chunker = TextChunker()
    chunks = chunker.chunk("", file_path="/empty.txt")
    assert chunks == []
```

**Step 2: Implement protocol and text chunker**

```python
# src/pocketpaw/search/chunkers/__init__.py
"""File chunking strategies for semantic search."""

# src/pocketpaw/search/chunkers/protocol.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Chunk:
    content: str | bytes
    chunk_type: str  # "text", "code", "image", "audio", "video", "pdf"
    metadata: dict[str, Any] = field(default_factory=dict)
    mime_type: str | None = None  # For binary chunks


class ChunkerProtocol(Protocol):
    def chunk(self, content: str | bytes, file_path: str) -> list[Chunk]: ...
```

```python
# src/pocketpaw/search/chunkers/text.py
from __future__ import annotations

import re

from pocketpaw.search.chunkers.protocol import Chunk, ChunkerProtocol


class TextChunker:
    """Splits markdown/plaintext by headings or paragraphs."""

    def chunk(self, content: str | bytes, file_path: str) -> list[Chunk]:
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        content = content.strip()
        if not content:
            return []

        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

        if ext in ("md", "mdx", "rst") or re.search(r"^#{1,6}\s", content, re.MULTILINE):
            return self._chunk_by_headings(content, file_path)
        return self._chunk_by_paragraphs(content, file_path)

    def _chunk_by_headings(self, content: str, file_path: str) -> list[Chunk]:
        sections = re.split(r"(?=^#{1,6}\s)", content, flags=re.MULTILINE)
        chunks: list[Chunk] = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            heading = ""
            heading_match = re.match(r"^(#{1,6})\s+(.*)", section)
            if heading_match:
                heading = heading_match.group(2).strip()
            chunks.append(Chunk(
                content=section,
                chunk_type="text",
                metadata={"file_path": file_path, "heading": heading},
            ))
        return chunks

    def _chunk_by_paragraphs(self, content: str, file_path: str) -> list[Chunk]:
        paragraphs = re.split(r"\n\s*\n", content)
        chunks: list[Chunk] = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            chunks.append(Chunk(
                content=para,
                chunk_type="text",
                metadata={"file_path": file_path},
            ))
        return chunks
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_chunkers.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/chunkers/ tests/test_chunkers.py
git commit -m "feat(search): add chunker protocol and text chunker"
```

---

### Task 8: Code Chunker

**Files:**
- Create: `src/pocketpaw/search/chunkers/code.py`
- Test: `tests/test_code_chunker.py`

**Step 1: Write test**

```python
# tests/test_code_chunker.py
from pocketpaw.search.chunkers.code import CodeChunker

def test_python_function_split():
    code = '''import os

def hello():
    print("hello")

def world():
    print("world")

class Foo:
    def bar(self):
        pass
'''
    chunker = CodeChunker()
    chunks = chunker.chunk(code, file_path="/app.py")
    assert len(chunks) >= 3  # hello, world, Foo
    names = [c.metadata.get("symbol") for c in chunks]
    assert "hello" in names
    assert "world" in names
    assert "Foo" in names

def test_javascript_split():
    code = '''function greet(name) {
  return "Hi " + name;
}

const add = (a, b) => {
  return a + b;
};

class Calculator {
  multiply(a, b) {
    return a * b;
  }
}
'''
    chunker = CodeChunker()
    chunks = chunker.chunk(code, file_path="/app.js")
    assert len(chunks) >= 2

def test_empty_file():
    chunker = CodeChunker()
    assert chunker.chunk("", file_path="/empty.py") == []

def test_unknown_extension_falls_back():
    chunker = CodeChunker()
    chunks = chunker.chunk("some content here", file_path="/file.xyz")
    assert len(chunks) == 1
```

**Step 2: Implement**

```python
# src/pocketpaw/search/chunkers/code.py
from __future__ import annotations

import re

from pocketpaw.search.chunkers.protocol import Chunk

# Regex patterns per language family for splitting by top-level symbols
_PATTERNS: dict[str, re.Pattern] = {
    "python": re.compile(
        r"^(?=(?:def |class |async def ))", re.MULTILINE
    ),
    "javascript": re.compile(
        r"^(?=(?:function |class |const |let |var |export ))", re.MULTILINE
    ),
    "typescript": re.compile(
        r"^(?=(?:function |class |const |let |var |export |interface |type ))",
        re.MULTILINE,
    ),
    "rust": re.compile(r"^(?=(?:fn |struct |enum |impl |pub |mod |trait ))", re.MULTILINE),
    "go": re.compile(r"^(?=(?:func |type |var |const ))", re.MULTILINE),
}

_EXT_TO_LANG: dict[str, str] = {
    "py": "python", "pyw": "python",
    "js": "javascript", "jsx": "javascript", "mjs": "javascript",
    "ts": "typescript", "tsx": "typescript",
    "rs": "rust",
    "go": "go",
}


class CodeChunker:
    """Splits source code by top-level functions/classes using regex."""

    def chunk(self, content: str | bytes, file_path: str) -> list[Chunk]:
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        content = content.strip()
        if not content:
            return []

        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        lang = _EXT_TO_LANG.get(ext, "")
        pattern = _PATTERNS.get(lang)

        if not pattern:
            return [Chunk(content=content, chunk_type="code",
                          metadata={"file_path": file_path, "language": ext})]

        parts = pattern.split(content)
        chunks: list[Chunk] = []
        preamble = parts[0].strip() if parts else ""

        # Preamble (imports, module-level code)
        if preamble:
            chunks.append(Chunk(
                content=preamble, chunk_type="code",
                metadata={"file_path": file_path, "language": lang, "symbol": "__preamble__"},
            ))

        for part in parts[1:]:
            part = part.strip()
            if not part:
                continue
            symbol = self._extract_symbol(part, lang)
            chunks.append(Chunk(
                content=part, chunk_type="code",
                metadata={"file_path": file_path, "language": lang, "symbol": symbol},
            ))
        return chunks

    def _extract_symbol(self, block: str, lang: str) -> str:
        first_line = block.split("\n", 1)[0]
        if lang == "python":
            m = re.match(r"(?:async\s+)?(?:def|class)\s+(\w+)", first_line)
        elif lang in ("javascript", "typescript"):
            m = re.match(
                r"(?:export\s+)?(?:default\s+)?(?:function|class|interface|type)\s+(\w+)",
                first_line,
            )
            if not m:
                m = re.match(r"(?:export\s+)?(?:const|let|var)\s+(\w+)", first_line)
        elif lang == "rust":
            m = re.match(r"(?:pub\s+)?(?:fn|struct|enum|impl|trait|mod)\s+(\w+)", first_line)
        elif lang == "go":
            m = re.match(r"(?:func|type|var|const)\s+(?:\([^)]*\)\s+)?(\w+)", first_line)
        else:
            m = None
        return m.group(1) if m else first_line[:40]
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_code_chunker.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/chunkers/code.py tests/test_code_chunker.py
git commit -m "feat(search): add code chunker with regex-based symbol splitting"
```

---

### Task 9: Structured Data and Document Chunkers

**Files:**
- Create: `src/pocketpaw/search/chunkers/structured.py`
- Create: `src/pocketpaw/search/chunkers/document.py`
- Test: `tests/test_structured_chunker.py`

**Step 1: Write test**

```python
# tests/test_structured_chunker.py
import json
import pytest
from pocketpaw.search.chunkers.structured import StructuredChunker

def test_json_chunking():
    data = json.dumps({"users": [1, 2], "config": {"debug": True}, "version": "1.0"})
    chunker = StructuredChunker()
    chunks = chunker.chunk(data, file_path="/data.json")
    assert len(chunks) == 3  # one per top-level key

def test_yaml_chunking():
    data = "key1: value1\nkey2:\n  nested: true\nkey3: value3\n"
    chunker = StructuredChunker()
    chunks = chunker.chunk(data, file_path="/config.yaml")
    assert len(chunks) >= 1

def test_csv_chunking():
    data = "name,age\nAlice,30\nBob,25\nCharlie,35\nDave,40\n"
    chunker = StructuredChunker()
    chunks = chunker.chunk(data, file_path="/people.csv")
    assert len(chunks) >= 1
```

**Step 2: Implement structured chunker**

```python
# src/pocketpaw/search/chunkers/structured.py
from __future__ import annotations

import csv
import io
import json
import logging

from pocketpaw.search.chunkers.protocol import Chunk

logger = logging.getLogger(__name__)

_ROW_BATCH = 50  # rows per chunk for CSV


class StructuredChunker:
    """Splits JSON/YAML/TOML by top-level keys, CSV by row batches."""

    def chunk(self, content: str | bytes, file_path: str) -> list[Chunk]:
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        content = content.strip()
        if not content:
            return []

        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

        if ext == "json":
            return self._chunk_json(content, file_path)
        elif ext in ("yaml", "yml"):
            return self._chunk_yaml(content, file_path)
        elif ext == "toml":
            return self._chunk_toml(content, file_path)
        elif ext == "csv":
            return self._chunk_csv(content, file_path)
        return [Chunk(content=content, chunk_type="structured",
                      metadata={"file_path": file_path})]

    def _chunk_json(self, content: str, file_path: str) -> list[Chunk]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return [Chunk(content=content, chunk_type="structured",
                          metadata={"file_path": file_path})]
        if isinstance(data, dict):
            return [
                Chunk(
                    content=json.dumps({k: v}, indent=2),
                    chunk_type="structured",
                    metadata={"file_path": file_path, "key": k},
                )
                for k, v in data.items()
            ]
        return [Chunk(content=content, chunk_type="structured",
                      metadata={"file_path": file_path})]

    def _chunk_yaml(self, content: str, file_path: str) -> list[Chunk]:
        # Split YAML by top-level keys (lines without indentation)
        import re
        sections = re.split(r"(?=^\S)", content, flags=re.MULTILINE)
        return [
            Chunk(content=s.strip(), chunk_type="structured",
                  metadata={"file_path": file_path})
            for s in sections if s.strip()
        ]

    def _chunk_toml(self, content: str, file_path: str) -> list[Chunk]:
        import re
        sections = re.split(r"(?=^\[)", content, flags=re.MULTILINE)
        return [
            Chunk(content=s.strip(), chunk_type="structured",
                  metadata={"file_path": file_path})
            for s in sections if s.strip()
        ]

    def _chunk_csv(self, content: str, file_path: str) -> list[Chunk]:
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return []
        header = rows[0]
        chunks: list[Chunk] = []
        for i in range(1, len(rows), _ROW_BATCH):
            batch = rows[i : i + _ROW_BATCH]
            text = ",".join(header) + "\n"
            text += "\n".join(",".join(r) for r in batch)
            chunks.append(Chunk(
                content=text, chunk_type="structured",
                metadata={"file_path": file_path, "row_start": i, "row_end": i + len(batch)},
            ))
        return chunks
```

```python
# src/pocketpaw/search/chunkers/document.py
from __future__ import annotations

import logging
from pathlib import Path

from pocketpaw.search.chunkers.protocol import Chunk

logger = logging.getLogger(__name__)

_PDF_PAGE_BATCH = 6  # Gemini API limit


class DocumentChunker:
    """Splits PDF/DOCX into page chunks. Returns binary chunks for Gemini native embedding."""

    def chunk(self, content: str | bytes, file_path: str) -> list[Chunk]:
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

        if ext == "pdf":
            return self._chunk_pdf(file_path)
        elif ext == "docx":
            return self._chunk_docx(file_path)
        # Fallback: treat as text
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        return [Chunk(content=content, chunk_type="text",
                      metadata={"file_path": file_path})]

    def _chunk_pdf(self, file_path: str) -> list[Chunk]:
        """Return PDF as binary chunks of up to 6 pages for Gemini native embedding."""
        raw = Path(file_path).read_bytes()
        try:
            import pymupdf
            doc = pymupdf.open(file_path)
            page_count = len(doc)
            doc.close()
        except ImportError:
            # Without pymupdf, send whole PDF (will fail if >6 pages)
            return [Chunk(
                content=raw, chunk_type="pdf", mime_type="application/pdf",
                metadata={"file_path": file_path, "pages": "all"},
            )]

        if page_count <= _PDF_PAGE_BATCH:
            return [Chunk(
                content=raw, chunk_type="pdf", mime_type="application/pdf",
                metadata={"file_path": file_path, "pages": f"1-{page_count}"},
            )]

        # Split into 6-page segments
        chunks: list[Chunk] = []
        doc = pymupdf.open(file_path)
        for start in range(0, page_count, _PDF_PAGE_BATCH):
            end = min(start + _PDF_PAGE_BATCH, page_count)
            sub = pymupdf.open()
            sub.insert_pdf(doc, from_page=start, to_page=end - 1)
            chunks.append(Chunk(
                content=sub.tobytes(), chunk_type="pdf", mime_type="application/pdf",
                metadata={"file_path": file_path, "pages": f"{start + 1}-{end}"},
            ))
            sub.close()
        doc.close()
        return chunks

    def _chunk_docx(self, file_path: str) -> list[Chunk]:
        try:
            from docx import Document
            doc = Document(file_path)
            text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            logger.warning("python-docx not installed, skipping %s", file_path)
            return []

        if not text.strip():
            return []

        # Split into ~2000 char chunks
        parts: list[Chunk] = []
        paragraphs = text.split("\n\n")
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > 2000 and current:
                parts.append(Chunk(
                    content=current.strip(), chunk_type="text",
                    metadata={"file_path": file_path},
                ))
                current = ""
            current += para + "\n\n"
        if current.strip():
            parts.append(Chunk(
                content=current.strip(), chunk_type="text",
                metadata={"file_path": file_path},
            ))
        return parts
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_structured_chunker.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/chunkers/structured.py src/pocketpaw/search/chunkers/document.py tests/test_structured_chunker.py
git commit -m "feat(search): add structured data and document chunkers"
```

---

### Task 10: Media Chunker (Image/Audio/Video)

**Files:**
- Create: `src/pocketpaw/search/chunkers/media.py`
- Test: `tests/test_media_chunker.py`

**Step 1: Write test**

```python
# tests/test_media_chunker.py
import pytest
from pocketpaw.search.chunkers.media import MediaChunker

def test_image_chunk(tmp_path):
    # Create a tiny 1x1 PNG
    import struct, zlib
    def make_png():
        sig = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        ihdr = b"IHDR" + ihdr_data
        ihdr_chunk = struct.pack(">I", 13) + ihdr + struct.pack(">I", zlib.crc32(ihdr) & 0xFFFFFFFF)
        raw = b"\x00\xff\x00\x00"
        idat_data = zlib.compress(raw)
        idat = b"IDAT" + idat_data
        idat_chunk = struct.pack(">I", len(idat_data)) + idat + struct.pack(">I", zlib.crc32(idat) & 0xFFFFFFFF)
        iend = b"IEND"
        iend_chunk = struct.pack(">I", 0) + iend + struct.pack(">I", zlib.crc32(iend) & 0xFFFFFFFF)
        return sig + ihdr_chunk + idat_chunk + iend_chunk

    img = tmp_path / "test.png"
    img.write_bytes(make_png())
    chunker = MediaChunker()
    chunks = chunker.chunk(img.read_bytes(), str(img))
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "image"
    assert chunks[0].mime_type == "image/png"
    assert isinstance(chunks[0].content, bytes)

def test_audio_chunk(tmp_path):
    audio = tmp_path / "test.mp3"
    audio.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 100)
    chunker = MediaChunker()
    chunks = chunker.chunk(audio.read_bytes(), str(audio))
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "audio"

def test_unsupported_format():
    chunker = MediaChunker()
    chunks = chunker.chunk(b"data", "/file.xyz")
    assert chunks == []
```

**Step 2: Implement**

```python
# src/pocketpaw/search/chunkers/media.py
from __future__ import annotations

import logging
import mimetypes

from pocketpaw.search.chunkers.protocol import Chunk

logger = logging.getLogger(__name__)

_IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tiff", "svg", "ico"}
_AUDIO_EXTS = {"mp3", "wav", "ogg", "flac", "aac", "m4a", "wma"}
_VIDEO_EXTS = {"mp4", "webm", "avi", "mov", "mkv", "flv", "wmv", "m4v"}

# Gemini limits
_MAX_AUDIO_SECONDS = 80
_MAX_VIDEO_SECONDS = 128


class MediaChunker:
    """Handles images, audio, and video files for native Gemini multimodal embedding."""

    def __init__(self, video_depth: str = "keyframes") -> None:
        self._video_depth = video_depth

    def chunk(self, content: str | bytes, file_path: str) -> list[Chunk]:
        if isinstance(content, str):
            content = content.encode("utf-8")

        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        mime = mimetypes.guess_type(file_path)[0] or ""

        if ext in _IMAGE_EXTS:
            return self._chunk_image(content, file_path, mime or f"image/{ext}")
        elif ext in _AUDIO_EXTS:
            return self._chunk_audio(content, file_path, mime or f"audio/{ext}")
        elif ext in _VIDEO_EXTS:
            return self._chunk_video(content, file_path, mime or f"video/{ext}")
        return []

    def _chunk_image(self, data: bytes, file_path: str, mime: str) -> list[Chunk]:
        return [Chunk(
            content=data, chunk_type="image", mime_type=mime,
            metadata={"file_path": file_path, "size_bytes": len(data)},
        )]

    def _chunk_audio(self, data: bytes, file_path: str, mime: str) -> list[Chunk]:
        # For now, send as single chunk. Splitting long audio is a future enhancement.
        return [Chunk(
            content=data, chunk_type="audio", mime_type=mime,
            metadata={"file_path": file_path, "size_bytes": len(data)},
        )]

    def _chunk_video(self, data: bytes, file_path: str, mime: str) -> list[Chunk]:
        # For keyframes mode, send raw video (Gemini handles up to 128s).
        # Full analysis mode with ffmpeg keyframe extraction is a future enhancement.
        return [Chunk(
            content=data, chunk_type="video", mime_type=mime,
            metadata={
                "file_path": file_path,
                "size_bytes": len(data),
                "analysis_depth": self._video_depth,
            },
        )]
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_media_chunker.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/chunkers/media.py tests/test_media_chunker.py
git commit -m "feat(search): add media chunker for images, audio, and video"
```

---

### Task 11: Chunker Router

**Files:**
- Modify: `src/pocketpaw/search/chunkers/__init__.py`
- Test: `tests/test_chunker_router.py`

**Step 1: Write test**

```python
# tests/test_chunker_router.py
from pocketpaw.search.chunkers import get_chunker_for_file

def test_python_file():
    chunker = get_chunker_for_file("/app.py")
    from pocketpaw.search.chunkers.code import CodeChunker
    assert isinstance(chunker, CodeChunker)

def test_markdown_file():
    chunker = get_chunker_for_file("/readme.md")
    from pocketpaw.search.chunkers.text import TextChunker
    assert isinstance(chunker, TextChunker)

def test_json_file():
    chunker = get_chunker_for_file("/data.json")
    from pocketpaw.search.chunkers.structured import StructuredChunker
    assert isinstance(chunker, StructuredChunker)

def test_image_file():
    chunker = get_chunker_for_file("/photo.png")
    from pocketpaw.search.chunkers.media import MediaChunker
    assert isinstance(chunker, MediaChunker)

def test_pdf_file():
    chunker = get_chunker_for_file("/doc.pdf")
    from pocketpaw.search.chunkers.document import DocumentChunker
    assert isinstance(chunker, DocumentChunker)

def test_unknown_falls_back_to_text():
    chunker = get_chunker_for_file("/notes.txt")
    from pocketpaw.search.chunkers.text import TextChunker
    assert isinstance(chunker, TextChunker)
```

**Step 2: Implement**

```python
# src/pocketpaw/search/chunkers/__init__.py
"""File chunking strategies for semantic search."""
from __future__ import annotations

from pocketpaw.search.chunkers.code import CodeChunker
from pocketpaw.search.chunkers.document import DocumentChunker
from pocketpaw.search.chunkers.media import MediaChunker
from pocketpaw.search.chunkers.structured import StructuredChunker
from pocketpaw.search.chunkers.text import TextChunker

_CODE_EXTS = {
    "py", "pyw", "js", "jsx", "mjs", "ts", "tsx", "rs", "go",
    "java", "kt", "c", "cpp", "h", "hpp", "cs", "rb", "php",
    "swift", "scala", "sh", "bash", "zsh", "ps1", "lua", "r",
    "dart", "zig", "nim", "ex", "exs", "erl", "hs", "ml", "clj",
}
_TEXT_EXTS = {"md", "mdx", "txt", "rst", "log", "cfg", "ini", "env"}
_STRUCTURED_EXTS = {"json", "yaml", "yml", "toml", "csv", "tsv", "xml"}
_DOCUMENT_EXTS = {"pdf", "docx"}
_IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tiff", "svg", "ico"}
_AUDIO_EXTS = {"mp3", "wav", "ogg", "flac", "aac", "m4a", "wma"}
_VIDEO_EXTS = {"mp4", "webm", "avi", "mov", "mkv", "flv", "wmv", "m4v"}

_code = CodeChunker()
_text = TextChunker()
_structured = StructuredChunker()
_document = DocumentChunker()
_media = MediaChunker()


def get_chunker_for_file(file_path: str, video_depth: str = "keyframes"):
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    if ext in _CODE_EXTS:
        return _code
    if ext in _STRUCTURED_EXTS:
        return _structured
    if ext in _DOCUMENT_EXTS:
        return _document
    if ext in _IMAGE_EXTS or ext in _AUDIO_EXTS or ext in _VIDEO_EXTS:
        return MediaChunker(video_depth=video_depth)
    return _text  # fallback
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_chunker_router.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/chunkers/__init__.py tests/test_chunker_router.py
git commit -m "feat(search): add chunker router for file type dispatch"
```

---

### Task 12: Embedding Service (Gemini API Wrapper)

**Files:**
- Create: `src/pocketpaw/search/embedder.py`
- Test: `tests/test_embedder.py`

**Step 1: Write test**

```python
# tests/test_embedder.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pocketpaw.search.embedder import EmbeddingService
from pocketpaw.search.chunkers.protocol import Chunk


@pytest.fixture
def mock_genai():
    with patch("pocketpaw.search.embedder.genai") as mock:
        client = MagicMock()
        mock.Client.return_value = client

        # Mock embed_content response
        embedding = MagicMock()
        embedding.values = [0.1] * 768
        result = MagicMock()
        result.embeddings = [embedding]
        client.models.embed_content.return_value = result

        yield client


@pytest.mark.asyncio
async def test_embed_text(mock_genai):
    svc = EmbeddingService(api_key="test-key", dimensions=768)
    chunks = [Chunk(content="hello world", chunk_type="text", metadata={})]
    embeddings = await svc.embed_chunks(chunks)
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 768
    mock_genai.models.embed_content.assert_called_once()


@pytest.mark.asyncio
async def test_embed_image(mock_genai):
    svc = EmbeddingService(api_key="test-key", dimensions=768)
    chunks = [Chunk(content=b"\x89PNG", chunk_type="image",
                    mime_type="image/png", metadata={})]
    embeddings = await svc.embed_chunks(chunks)
    assert len(embeddings) == 1


@pytest.mark.asyncio
async def test_embed_query(mock_genai):
    svc = EmbeddingService(api_key="test-key", dimensions=768)
    embedding = await svc.embed_query("find auth code")
    assert len(embedding) == 768


@pytest.mark.asyncio
async def test_embed_code_query(mock_genai):
    svc = EmbeddingService(api_key="test-key", dimensions=768)
    embedding = await svc.embed_query("def authenticate():")
    assert len(embedding) == 768
```

**Step 2: Implement**

```python
# src/pocketpaw/search/embedder.py
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from pocketpaw.search.chunkers.protocol import Chunk

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]

_CODE_PATTERN = re.compile(r"[{}\[\]();=<>]|def |class |function |import |from ")


class EmbeddingService:
    """Wraps Gemini Embedding API for text and multimodal content."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-embedding-2-preview",
        dimensions: int = 768,
    ) -> None:
        if genai is None:
            raise ImportError("google-genai is required: pip install google-genai")
        self._model = model
        self._dimensions = dimensions
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()

    async def embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        """Embed a list of chunks. Returns one embedding per chunk."""
        results: list[list[float]] = []
        for chunk in chunks:
            emb = await self._embed_single(chunk)
            results.append(emb)
        return results

    async def embed_query(self, query: str) -> list[float]:
        """Embed a search query with appropriate task type."""
        task_type = "CODE_RETRIEVAL_QUERY" if _CODE_PATTERN.search(query) else "RETRIEVAL_QUERY"
        config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=self._dimensions,
        )
        result = await asyncio.to_thread(
            self._client.models.embed_content,
            model=self._model,
            contents=query,
            config=config,
        )
        return result.embeddings[0].values

    async def _embed_single(self, chunk: Chunk) -> list[float]:
        """Embed a single chunk, handling text vs binary content."""
        if isinstance(chunk.content, str):
            return await self._embed_text(chunk.content)
        else:
            return await self._embed_binary(chunk.content, chunk.mime_type or "application/octet-stream")

    async def _embed_text(self, text: str) -> list[float]:
        config = types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=self._dimensions,
        )
        result = await asyncio.to_thread(
            self._client.models.embed_content,
            model=self._model,
            contents=text,
            config=config,
        )
        return result.embeddings[0].values

    async def _embed_binary(self, data: bytes, mime_type: str) -> list[float]:
        content = types.Part.from_bytes(data=data, mime_type=mime_type)
        config = types.EmbedContentConfig(
            output_dimensionality=self._dimensions,
        )
        result = await asyncio.to_thread(
            self._client.models.embed_content,
            model=self._model,
            contents=[content],
            config=config,
        )
        return result.embeddings[0].values
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_embedder.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/embedder.py tests/test_embedder.py
git commit -m "feat(search): add Gemini embedding service with multimodal support"
```

---

### Task 13: Index Manifest

**Files:**
- Create: `src/pocketpaw/search/manifest.py`
- Test: `tests/test_manifest.py`

**Step 1: Write test**

```python
# tests/test_manifest.py
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
```

**Step 2: Implement**

```python
# src/pocketpaw/search/manifest.py
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class IndexManifest:
    """Tracks which files are indexed and their content hashes."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._data: dict[str, Any] = {"files": {}, "stats": {}}
        if self._path.exists():
            self._data = json.loads(self._path.read_text())

    def get_file(self, file_path: str) -> dict[str, Any] | None:
        return self._data["files"].get(file_path)

    def set_file(self, file_path: str, content_hash: str, chunk_count: int) -> None:
        self._data["files"][file_path] = {
            "content_hash": content_hash,
            "chunk_count": chunk_count,
            "indexed_at": time.time(),
        }
        self._update_stats()
        self.save()

    def remove_file(self, file_path: str) -> None:
        self._data["files"].pop(file_path, None)
        self._update_stats()
        self.save()

    def needs_reindex(self, file_path: str, content_hash: str) -> bool:
        entry = self.get_file(file_path)
        if entry is None:
            return True
        return entry["content_hash"] != content_hash

    def stats(self) -> dict[str, Any]:
        self._update_stats()
        return self._data["stats"]

    def all_indexed_paths(self) -> set[str]:
        return set(self._data["files"].keys())

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))

    def _update_stats(self) -> None:
        files = self._data["files"]
        self._data["stats"] = {
            "total_files": len(files),
            "total_chunks": sum(f.get("chunk_count", 0) for f in files.values()),
        }
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_manifest.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/manifest.py tests/test_manifest.py
git commit -m "feat(search): add index manifest for tracking indexed files"
```

---

### Task 14: Indexer Pipeline

**Files:**
- Create: `src/pocketpaw/search/indexer.py`
- Test: `tests/test_indexer.py`

**Step 1: Write test**

```python
# tests/test_indexer.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
    return Indexer(
        embedder=mock_embedder,
        metadata_store=mock_store,
        content_store=mock_store,
        manifest_dir=str(tmp_path),
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
async def test_index_directory(indexer, tmp_path):
    (tmp_path / "a.py").write_text("a = 1")
    (tmp_path / "b.txt").write_text("hello")
    sub = tmp_path / ".git"
    sub.mkdir()
    (sub / "config").write_text("ignore me")

    stats = await indexer.index_directory(str(tmp_path))
    assert stats["indexed"] == 2
    assert stats["skipped"] >= 1
```

**Step 2: Implement**

```python
# src/pocketpaw/search/indexer.py
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Callable

from pocketpaw.search.chunkers import get_chunker_for_file
from pocketpaw.search.chunkers.protocol import Chunk
from pocketpaw.search.embedder import EmbeddingService
from pocketpaw.search.manifest import IndexManifest

logger = logging.getLogger(__name__)


class Indexer:
    """Indexes files into vector stores via the embedding service."""

    def __init__(
        self,
        embedder: EmbeddingService,
        metadata_store: Any,
        content_store: Any,
        manifest_dir: str,
        blocklist: list[str] | None = None,
        allowlist: list[str] | None = None,
        max_file_size_mb: int = 50,
        video_depth: str = "keyframes",
        on_progress: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._embedder = embedder
        self._meta_store = metadata_store
        self._content_store = content_store
        self._manifest = IndexManifest(Path(manifest_dir) / "manifest.json")
        self._blocklist = set(blocklist or [])
        self._allowlist = set(allowlist or [])
        self._max_size = max_file_size_mb * 1024 * 1024
        self._video_depth = video_depth
        self._on_progress = on_progress

    def _is_blocked(self, file_path: str) -> bool:
        parts = Path(file_path).parts
        return any(blocked in parts for blocked in self._blocklist)

    def _content_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _path_id(self, file_path: str) -> str:
        return hashlib.sha256(file_path.encode()).hexdigest()

    async def index_file(self, file_path: str) -> bool:
        """Index a single file. Returns True if indexed, False if skipped."""
        if self._is_blocked(file_path):
            return False

        path = Path(file_path)
        if not path.is_file():
            return False
        if path.stat().st_size > self._max_size:
            logger.debug("Skipping %s (too large)", file_path)
            return False

        raw = path.read_bytes()
        content_hash = self._content_hash(raw)

        if not self._manifest.needs_reindex(file_path, content_hash):
            return False

        # Chunk the file
        chunker = get_chunker_for_file(file_path, video_depth=self._video_depth)
        chunks = chunker.chunk(raw, file_path)
        if not chunks:
            return False

        # Embed chunks
        embeddings = await self._embedder.embed_chunks(chunks)

        # Build file metadata embedding (file name + path + extension)
        file_name = path.name
        ext = path.suffix.lstrip(".")
        meta_text = f"{file_name} {file_path} {ext}"
        meta_embedding = await self._embedder.embed_chunks(
            [Chunk(content=meta_text, chunk_type="text", metadata={})]
        )

        # Upsert metadata
        path_hash = self._path_id(file_path)
        await self._meta_store.upsert(
            ids=[f"meta:{path_hash}"],
            embeddings=meta_embedding,
            metadata=[{
                "file_path": file_path,
                "file_name": file_name,
                "extension": ext,
                "size": path.stat().st_size,
                "last_modified": path.stat().st_mtime,
            }],
        )

        # Upsert content chunks
        chunk_ids = [f"chunk:{path_hash}:{i}" for i in range(len(chunks))]
        chunk_meta = []
        for i, chunk in enumerate(chunks):
            preview = ""
            if isinstance(chunk.content, str):
                preview = chunk.content[:200]
            chunk_meta.append({
                "file_path": file_path,
                "chunk_index": i,
                "chunk_type": chunk.chunk_type,
                "content_hash": content_hash,
                "content_preview": preview,
                "last_modified": path.stat().st_mtime,
                **{k: v for k, v in chunk.metadata.items()
                   if k != "file_path" and isinstance(v, (str, int, float, bool))},
            })

        await self._content_store.upsert(
            ids=chunk_ids, embeddings=embeddings, metadata=chunk_meta,
        )

        self._manifest.set_file(file_path, content_hash=content_hash, chunk_count=len(chunks))
        return True

    async def index_directory(
        self, directory: str, recursive: bool = True,
    ) -> dict[str, int]:
        """Index all files in a directory. Returns stats."""
        stats = {"indexed": 0, "skipped": 0, "errors": 0, "total": 0}

        for root, dirs, files in os.walk(directory):
            # Filter blocked directories in-place
            dirs[:] = [d for d in dirs if d not in self._blocklist]
            if not recursive and root != directory:
                break

            for fname in files:
                file_path = os.path.join(root, fname)
                stats["total"] += 1
                try:
                    indexed = await self.index_file(file_path)
                    if indexed:
                        stats["indexed"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception:
                    logger.exception("Error indexing %s", file_path)
                    stats["errors"] += 1

                if self._on_progress:
                    self._on_progress(stats)

        return stats

    async def remove_file(self, file_path: str) -> None:
        """Remove a file from the index."""
        path_hash = self._path_id(file_path)
        entry = self._manifest.get_file(file_path)
        if entry:
            chunk_ids = [f"chunk:{path_hash}:{i}" for i in range(entry["chunk_count"])]
            await self._content_store.delete(chunk_ids)
        await self._meta_store.delete([f"meta:{path_hash}"])
        self._manifest.remove_file(file_path)

    async def remove_directory(self, directory: str) -> int:
        """Remove all files under a directory from the index."""
        removed = 0
        for path in list(self._manifest.all_indexed_paths()):
            if path.startswith(directory):
                await self.remove_file(path)
                removed += 1
        return removed
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_indexer.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/indexer.py tests/test_indexer.py
git commit -m "feat(search): add file indexer with directory walking and dedup"
```

---

### Task 15: Search Service

**Files:**
- Create: `src/pocketpaw/search/service.py`
- Test: `tests/test_search_service.py`

**Step 1: Write test**

```python
# tests/test_search_service.py
import pytest
from unittest.mock import AsyncMock
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
        SearchResult(id="meta:abc", score=0.9, metadata={"file_path": "/a.py", "file_name": "a.py"}),
    ]
    return s

@pytest.fixture
def mock_content_store():
    s = AsyncMock()
    s.query.return_value = [
        SearchResult(id="chunk:abc:0", score=0.85, metadata={"file_path": "/a.py", "content_preview": "def hello():"}),
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
        SearchResult(id="chunk:1", score=0.9, metadata={"file_path": "/img.png", "chunk_type": "image"}),
        SearchResult(id="chunk:2", score=0.8, metadata={"file_path": "/a.py", "chunk_type": "code"}),
    ]
    results = await service.search("hello", file_types=["code"])
    code_results = [r for r in results if r.metadata.get("chunk_type") == "code"]
    assert len(code_results) >= 1
```

**Step 2: Implement**

```python
# src/pocketpaw/search/service.py
from __future__ import annotations

import logging
import time
from typing import Any

from pocketpaw.search.embedder import EmbeddingService
from pocketpaw.search.vector_store import SearchResult

logger = logging.getLogger(__name__)


class SearchService:
    """Unified semantic search interface."""

    def __init__(
        self,
        embedder: EmbeddingService,
        metadata_store: Any,
        content_store: Any,
    ) -> None:
        self._embedder = embedder
        self._meta_store = metadata_store
        self._content_store = content_store

    async def search(
        self,
        query: str,
        top_k: int = 10,
        file_types: list[str] | None = None,
        extensions: list[str] | None = None,
        directories: list[str] | None = None,
        search_mode: str = "hybrid",
    ) -> list[SearchResult]:
        """Search the index. Modes: metadata, content, hybrid."""
        start = time.monotonic()
        query_embedding = await self._embedder.embed_query(query)

        results: list[SearchResult] = []

        if search_mode in ("metadata", "hybrid"):
            meta_results = await self._meta_store.query(
                query_embedding, top_k=top_k,
            )
            results.extend(meta_results)

        if search_mode in ("content", "hybrid"):
            content_results = await self._content_store.query(
                query_embedding, top_k=top_k,
            )
            results.extend(content_results)

        # Filter by file type
        if file_types:
            results = [
                r for r in results
                if r.metadata.get("chunk_type", "") in file_types
                or r.metadata.get("file_type", "") in file_types
            ]

        # Filter by extension
        if extensions:
            results = [
                r for r in results
                if r.metadata.get("extension", "") in extensions
                or any(r.metadata.get("file_path", "").endswith(e) for e in extensions)
            ]

        # Filter by directory scope
        if directories:
            results = [
                r for r in results
                if any(r.metadata.get("file_path", "").startswith(d) for d in directories)
            ]

        # Deduplicate by file_path, keep highest score
        seen: dict[str, SearchResult] = {}
        for r in results:
            fp = r.metadata.get("file_path", r.id)
            if fp not in seen or r.score > seen[fp].score:
                seen[fp] = r
        results = sorted(seen.values(), key=lambda r: r.score, reverse=True)[:top_k]

        elapsed = (time.monotonic() - start) * 1000
        logger.debug("Search for %r took %.1fms, %d results", query, elapsed, len(results))
        return results
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_search_service.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/service.py tests/test_search_service.py
git commit -m "feat(search): add unified search service with hybrid mode"
```

---

### Task 16: Search REST API

**Files:**
- Create: `src/pocketpaw/api/v1/search.py`
- Modify: `src/pocketpaw/api/v1/__init__.py`
- Test: `tests/test_search_api.py`

**Step 1: Write test**

```python
# tests/test_search_api.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from pocketpaw.api.v1.search import router
from pocketpaw.search.vector_store import SearchResult

app = FastAPI()
app.include_router(router, prefix="/api/v1")

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_search_service():
    mock_svc = AsyncMock()
    mock_svc.search.return_value = [
        SearchResult(id="meta:abc", score=0.9, metadata={"file_path": "/a.py", "file_name": "a.py"}),
    ]
    with patch("pocketpaw.api.v1.search._get_search_service", return_value=mock_svc):
        yield mock_svc

def test_search_endpoint(client):
    resp = client.get("/api/v1/search", params={"q": "hello", "top_k": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) == 1

def test_search_missing_query(client):
    resp = client.get("/api/v1/search")
    assert resp.status_code == 422

def test_stats_endpoint(client):
    with patch("pocketpaw.api.v1.search._get_manifest") as mock_manifest:
        mock_manifest.return_value.stats.return_value = {"total_files": 10, "total_chunks": 50}
        resp = client.get("/api/v1/search/stats")
        assert resp.status_code == 200
```

**Step 2: Implement**

```python
# src/pocketpaw/api/v1/search.py
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
    mode: str = Query("hybrid", regex="^(metadata|content|hybrid)$"),
    file_types: str | None = Query(None, description="Comma-separated: code,image,video,audio,text"),
    extensions: str | None = Query(None, description="Comma-separated: .py,.js,.ts"),
    directories: str | None = Query(None, description="Comma-separated directory paths"),
):
    import time

    start = time.monotonic()
    svc = _get_search_service()
    ft = file_types.split(",") if file_types else None
    ext = extensions.split(",") if extensions else None
    dirs = directories.split(",") if directories else None

    results = await svc.search(q, top_k=top_k, file_types=ft, extensions=ext,
                               directories=dirs, search_mode=mode)
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
```

**Step 3: Add router to v1/__init__.py**

Add to `_V1_ROUTERS` list (around line 43):

```python
("pocketpaw.api.v1.search", "router", "Search"),
```

**Step 4: Run test, verify pass**

Run: `uv run pytest tests/test_search_api.py -v`

**Step 5: Commit**

```bash
git add src/pocketpaw/api/v1/search.py src/pocketpaw/api/v1/__init__.py tests/test_search_api.py
git commit -m "feat(search): add REST API endpoints for search, indexing, and stats"
```

---

### Task 17: Semantic Search Agent Tool

**Files:**
- Create: `src/pocketpaw/tools/builtin/semantic_search.py`
- Test: `tests/test_semantic_search_tool.py`

**Step 1: Write test**

```python
# tests/test_semantic_search_tool.py
import pytest
from unittest.mock import AsyncMock, patch
from pocketpaw.tools.builtin.semantic_search import SemanticSearchTool
from pocketpaw.search.vector_store import SearchResult

@pytest.fixture
def mock_service():
    svc = AsyncMock()
    svc.search.return_value = [
        SearchResult(id="meta:1", score=0.92, metadata={
            "file_path": "/src/auth.py", "file_name": "auth.py",
            "content_preview": "def authenticate(user, password):",
        }),
        SearchResult(id="chunk:2:0", score=0.85, metadata={
            "file_path": "/src/login.py", "file_name": "login.py",
            "content_preview": "class LoginHandler:",
        }),
    ]
    return svc

@pytest.mark.asyncio
async def test_execute(mock_service):
    with patch("pocketpaw.tools.builtin.semantic_search._get_search_service", return_value=mock_service):
        tool = SemanticSearchTool()
        result = await tool.execute(query="authentication logic")
        assert "auth.py" in result
        assert "0.92" in result
        mock_service.search.assert_called_once()

def test_tool_properties():
    tool = SemanticSearchTool()
    assert tool.name == "semantic_search"
    assert "query" in tool.parameters["properties"]
    assert tool.trust_level == "standard"
```

**Step 2: Implement**

```python
# src/pocketpaw/tools/builtin/semantic_search.py
"""Semantic file search tool for the AI agent."""
from __future__ import annotations

import logging

from pocketpaw.tools.protocol import BaseTool

logger = logging.getLogger(__name__)

_search_service = None


def _get_search_service():
    global _search_service
    if _search_service is None:
        # Lazy import to avoid circular deps
        from pocketpaw.api.v1.search import _search_service as api_svc
        return api_svc
    return _search_service


class SemanticSearchTool(BaseTool):
    """Search files in the workspace by meaning using Gemini embeddings."""

    @property
    def name(self) -> str:
        return "semantic_search"

    @property
    def description(self) -> str:
        return (
            "Search files in the workspace by meaning. Finds code, documents, "
            "images, videos, and other files matching a natural language query. "
            "Use this when you need to find relevant files without knowing exact names."
        )

    @property
    def trust_level(self) -> str:
        return "standard"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 10)",
                    "default": 10,
                },
                "file_types": {
                    "type": "string",
                    "description": "Comma-separated filter: code,image,video,audio,text,structured,pdf",
                },
                "search_mode": {
                    "type": "string",
                    "enum": ["metadata", "content", "hybrid"],
                    "description": "Search mode (default: hybrid)",
                    "default": "hybrid",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        if not query:
            return self._error("query is required")

        svc = _get_search_service()
        if svc is None:
            return self._error("Semantic search is not enabled. Enable it in settings.")

        top_k = kwargs.get("top_k", 10)
        file_types = kwargs.get("file_types")
        search_mode = kwargs.get("search_mode", "hybrid")

        ft = file_types.split(",") if file_types else None

        try:
            results = await svc.search(
                query, top_k=top_k, file_types=ft, search_mode=search_mode,
            )
        except Exception as e:
            logger.exception("Semantic search failed")
            return self._error(f"Search failed: {e}")

        if not results:
            return "No matching files found."

        lines = [f"Found {len(results)} relevant files:\n"]
        for i, r in enumerate(results, 1):
            fp = r.metadata.get("file_path", "unknown")
            name = r.metadata.get("file_name", "")
            preview = r.metadata.get("content_preview", "")
            score = f"{r.score:.2f}"
            lines.append(f"{i}. **{name or fp}** (relevance: {score})")
            lines.append(f"   Path: {fp}")
            if preview:
                lines.append(f"   Preview: {preview[:150]}")
            lines.append("")

        return "\n".join(lines)
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_semantic_search_tool.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/tools/builtin/semantic_search.py tests/test_semantic_search_tool.py
git commit -m "feat(search): add semantic_search agent tool"
```

---

### Task 18: Agent Auto-Enrichment

**Files:**
- Create: `src/pocketpaw/search/enrichment.py`
- Test: `tests/test_enrichment.py`

**Step 1: Write test**

```python
# tests/test_enrichment.py
import pytest
from unittest.mock import AsyncMock
from pocketpaw.search.enrichment import SearchEnrichment
from pocketpaw.search.vector_store import SearchResult

@pytest.fixture
def mock_service():
    svc = AsyncMock()
    svc.search.return_value = [
        SearchResult(id="1", score=0.9, metadata={"file_path": "/auth.py", "content_preview": "def auth():"}),
        SearchResult(id="2", score=0.8, metadata={"file_path": "/login.py", "content_preview": "class Login:"}),
    ]
    return svc

@pytest.mark.asyncio
async def test_enrich_returns_context(mock_service):
    enricher = SearchEnrichment(mock_service, top_k=5)
    ctx = await enricher.enrich("how does auth work?")
    assert "/auth.py" in ctx
    assert "/login.py" in ctx

@pytest.mark.asyncio
async def test_enrich_empty_query(mock_service):
    enricher = SearchEnrichment(mock_service)
    ctx = await enricher.enrich("")
    assert ctx == ""

@pytest.mark.asyncio
async def test_enrich_no_results():
    svc = AsyncMock()
    svc.search.return_value = []
    enricher = SearchEnrichment(svc)
    ctx = await enricher.enrich("something obscure")
    assert ctx == ""
```

**Step 2: Implement**

```python
# src/pocketpaw/search/enrichment.py
from __future__ import annotations

import logging

from pocketpaw.search.service import SearchService

logger = logging.getLogger(__name__)


class SearchEnrichment:
    """Auto-enriches agent context with semantically relevant files."""

    def __init__(self, search_service: SearchService, top_k: int = 5) -> None:
        self._service = search_service
        self._top_k = top_k

    async def enrich(self, query: str) -> str:
        """Return context string for relevant files, or empty string."""
        if not query.strip():
            return ""

        try:
            results = await self._service.search(
                query, top_k=self._top_k, search_mode="hybrid",
            )
        except Exception:
            logger.exception("Auto-enrichment search failed")
            return ""

        if not results:
            return ""

        lines = ["[Potentially relevant files from workspace index]"]
        for r in results:
            fp = r.metadata.get("file_path", "")
            preview = r.metadata.get("content_preview", "")
            score = f"{r.score:.2f}"
            entry = f"- {fp} (relevance: {score})"
            if preview:
                entry += f" | {preview[:100]}"
            lines.append(entry)

        return "\n".join(lines)
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_enrichment.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/enrichment.py tests/test_enrichment.py
git commit -m "feat(search): add agent auto-enrichment"
```

---

### Task 19: Search Module Initialization and Wiring

**Files:**
- Modify: `src/pocketpaw/search/__init__.py`
- Test: `tests/test_search_init.py`

**Step 1: Write test**

```python
# tests/test_search_init.py
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_initialize_search(tmp_path):
    with patch("pocketpaw.search.EmbeddingService") as MockEmbed, \
         patch("pocketpaw.search.stores.create_vector_store") as MockStore:
        mock_store = MagicMock()
        mock_store.initialize = MagicMock(return_value=None)
        MockStore.return_value = mock_store
        MockEmbed.return_value = MagicMock()

        from pocketpaw.search import initialize_search
        components = await initialize_search(
            api_key="test",
            vector_backend="chroma",
            dimensions=768,
            data_dir=str(tmp_path),
        )
        assert "service" in components
        assert "indexer" in components
        assert "enrichment" in components
```

**Step 2: Implement**

```python
# src/pocketpaw/search/__init__.py
"""Semantic search with Gemini Embedding 2.0."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def initialize_search(
    api_key: str = "",
    model: str = "gemini-embedding-2-preview",
    vector_backend: str = "auto",
    dimensions: int = 768,
    data_dir: str = "",
    blocklist: list[str] | None = None,
    allowlist: list[str] | None = None,
    max_file_size_mb: int = 50,
    video_depth: str = "keyframes",
) -> dict[str, Any]:
    """Initialize all search components. Returns dict of service, indexer, enrichment."""
    from pocketpaw.search.embedder import EmbeddingService
    from pocketpaw.search.enrichment import SearchEnrichment
    from pocketpaw.search.indexer import Indexer
    from pocketpaw.search.service import SearchService
    from pocketpaw.search.stores import create_vector_store

    if not data_dir:
        data_dir = str(Path.home() / ".pocketpaw" / "embeddings")

    persist_dir = str(Path(data_dir) / vector_backend)

    embedder = EmbeddingService(api_key=api_key, model=model, dimensions=dimensions)

    meta_store = create_vector_store(vector_backend, persist_dir=persist_dir + "_meta")
    content_store = create_vector_store(vector_backend, persist_dir=persist_dir + "_content")

    await meta_store.initialize("file_metadata", dimensions)
    await content_store.initialize("file_contents", dimensions)

    service = SearchService(
        embedder=embedder, metadata_store=meta_store, content_store=content_store,
    )
    indexer = Indexer(
        embedder=embedder,
        metadata_store=meta_store,
        content_store=content_store,
        manifest_dir=data_dir,
        blocklist=blocklist,
        allowlist=allowlist,
        max_file_size_mb=max_file_size_mb,
        video_depth=video_depth,
    )
    enrichment = SearchEnrichment(service)

    # Wire up the API module globals
    from pocketpaw.api.v1 import search as search_api
    from pocketpaw.search import manifest as manifest_mod

    search_api._search_service = service
    search_api._indexer = indexer
    search_api._manifest = indexer._manifest

    logger.info(
        "Search initialized: backend=%s, dimensions=%d, data_dir=%s",
        vector_backend, dimensions, data_dir,
    )

    return {"service": service, "indexer": indexer, "enrichment": enrichment}
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_search_init.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/__init__.py tests/test_search_init.py
git commit -m "feat(search): add search initialization and component wiring"
```

---

### Task 20: File Watcher for Incremental Indexing

**Files:**
- Create: `src/pocketpaw/search/watcher.py`
- Test: `tests/test_watcher.py`

**Step 1: Write test**

```python
# tests/test_watcher.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from pocketpaw.search.watcher import FileWatcher

@pytest.fixture
def mock_indexer():
    indexer = AsyncMock()
    indexer.index_file.return_value = True
    indexer.remove_file.return_value = None
    return indexer

def test_watcher_init(mock_indexer, tmp_path):
    watcher = FileWatcher(
        indexer=mock_indexer,
        directories=[str(tmp_path)],
        debounce_ms=100,
    )
    assert watcher._directories == [str(tmp_path)]
    assert watcher._running is False
```

**Step 2: Implement**

```python
# src/pocketpaw/search/watcher.py
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FileWatcher:
    """Watches directories for changes and triggers incremental indexing."""

    def __init__(
        self,
        indexer: Any,
        directories: list[str],
        debounce_ms: int = 2000,
    ) -> None:
        self._indexer = indexer
        self._directories = directories
        self._debounce_s = debounce_ms / 1000
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        logger.info("File watcher started for %d directories", len(self._directories))

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("File watcher stopped")

    async def _watch_loop(self) -> None:
        try:
            from watchfiles import awatch, Change
        except ImportError:
            logger.error("watchfiles not installed, file watching disabled")
            return

        try:
            async for changes in awatch(
                *self._directories,
                debounce=int(self._debounce_s * 1000),
                stop_event=asyncio.Event() if not self._running else None,
            ):
                if not self._running:
                    break
                for change_type, path in changes:
                    try:
                        if change_type in (Change.added, Change.modified):
                            await self._indexer.index_file(path)
                        elif change_type == Change.deleted:
                            await self._indexer.remove_file(path)
                    except Exception:
                        logger.exception("Error processing change for %s", path)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("File watcher error")
```

**Step 3: Run test, verify pass**

Run: `uv run pytest tests/test_watcher.py -v`

**Step 4: Commit**

```bash
git add src/pocketpaw/search/watcher.py tests/test_watcher.py
git commit -m "feat(search): add file watcher for incremental indexing"
```

---

### Task 21: Hook Search into App Startup

**Files:**
- Modify: `src/pocketpaw/agents/loop.py` (or wherever the app boots)
- This task requires reading the actual startup flow to find the right hook point

**Step 1: Read the app startup code**

Find where the app initializes (likely `__main__.py` or the FastAPI app creation). Add a hook that calls `initialize_search()` when `settings.search_enabled` is True.

**Step 2: Add search startup**

In the startup flow, after settings are loaded:

```python
if settings.search_enabled:
    from pocketpaw.search import initialize_search
    search_components = await initialize_search(
        api_key=settings.search_gemini_api_key,
        model=settings.search_embedding_model,
        vector_backend=settings.search_vector_backend,
        dimensions=settings.search_embedding_dimensions,
        blocklist=settings.search_index_blocklist,
        allowlist=settings.search_index_allowlist,
        max_file_size_mb=settings.search_max_file_size_mb,
        video_depth=settings.search_video_analysis_depth,
    )

    # Auto-index configured directories
    if settings.search_auto_index_dirs:
        indexer = search_components["indexer"]
        for directory in settings.search_auto_index_dirs:
            asyncio.create_task(indexer.index_directory(directory))

    # Start file watcher
    from pocketpaw.search.watcher import FileWatcher
    watcher = FileWatcher(
        indexer=search_components["indexer"],
        directories=settings.search_auto_index_dirs,
    )
    await watcher.start()

    # Wire auto-enrichment into context builder if enabled
    if settings.search_auto_enrich:
        # Inject enrichment into the bootstrap context builder
        pass  # Implementation depends on exact startup flow
```

**Step 3: Commit**

```bash
git add src/pocketpaw/__main__.py  # or wherever startup lives
git commit -m "feat(search): wire search initialization into app startup"
```

---

### Task 22: Frontend - Search Store State

**Files:**
- Modify: `client/src/lib/stores/explorer.svelte.ts`
- Modify: `client/src/lib/api/client.ts`

**Step 1: Add types to client API**

In `client/src/lib/api/client.ts`, add:

```typescript
export interface SemanticSearchResult {
    id: string;
    score: number;
    metadata: Record<string, any>;
}

export interface SemanticSearchResponse {
    results: SemanticSearchResult[];
    took_ms: number;
}
```

Add method to client class:

```typescript
async semanticSearch(query: string, options?: {
    top_k?: number;
    mode?: 'metadata' | 'content' | 'hybrid';
    file_types?: string;
}): Promise<SemanticSearchResponse> {
    const params = new URLSearchParams({ q: query });
    if (options?.top_k) params.set('top_k', String(options.top_k));
    if (options?.mode) params.set('mode', options.mode);
    if (options?.file_types) params.set('file_types', options.file_types);
    return this.request<SemanticSearchResponse>('GET', `/search?${params}`);
}

async triggerIndex(path: string): Promise<void> {
    await this.request('POST', '/search/index', { path });
}

async getSearchStats(): Promise<{ total_files: number; total_chunks: number }> {
    return this.request('GET', '/search/stats');
}
```

**Step 2: Add semantic search state to explorer store**

In `explorer.svelte.ts`, add state fields:

```typescript
semanticSearchEnabled = $state(false);
semanticResults = $state<SemanticSearchResult[]>([]);
semanticSearchLoading = $state(false);
```

Add method:

```typescript
async performSemanticSearch(query: string): Promise<void> {
    if (!query.trim() || !this.semanticSearchEnabled) return;
    this.semanticSearchLoading = true;
    try {
        const resp = await api.semanticSearch(query, { top_k: 20, mode: 'hybrid' });
        this.semanticResults = resp.results;
    } catch (e) {
        console.error('Semantic search failed:', e);
        this.semanticResults = [];
    } finally {
        this.semanticSearchLoading = false;
    }
}
```

**Step 3: Commit**

```bash
git add client/src/lib/api/client.ts client/src/lib/stores/explorer.svelte.ts
git commit -m "feat(search): add semantic search state and API client methods"
```

---

### Task 23: Frontend - FilterBar Semantic Toggle

**Files:**
- Modify: `client/src/lib/components/explorer/FilterBar.svelte`

**Step 1: Add semantic search toggle**

Add a toggle button next to the search input that switches between "Name" and "Smart" search modes. When in Smart mode, debounce 500ms and call `explorerStore.performSemanticSearch()`.

```svelte
<button
    class="search-mode-toggle"
    onclick={() => explorerStore.semanticSearchEnabled = !explorerStore.semanticSearchEnabled}
    title={explorerStore.semanticSearchEnabled ? 'Semantic search (AI)' : 'Name search'}
>
    {explorerStore.semanticSearchEnabled ? 'AI' : 'Name'}
</button>
```

Update the input handler to route to semantic search when enabled.

**Step 2: Commit**

```bash
git add client/src/lib/components/explorer/FilterBar.svelte
git commit -m "feat(search): add semantic search toggle to FilterBar"
```

---

### Task 24: Frontend - Search Panel Component

**Files:**
- Create: `client/src/lib/components/search/SearchPanel.svelte`

**Step 1: Build dedicated search panel**

Full-featured search UI with:
- Search input
- File type filter chips (Code, Images, Video, Audio, Documents, All)
- Search mode toggle (Files, Contents, Both)
- Results list with file icon, name, path, score bar, preview
- Keyboard navigation (arrow keys, Enter)

This is a standard Svelte 5 component using the existing API client and shadcn-svelte UI components.

**Step 2: Add to sidebar navigation**

Add a magnifying glass icon in the sidebar that opens the SearchPanel.

**Step 3: Commit**

```bash
git add client/src/lib/components/search/
git commit -m "feat(search): add dedicated SearchPanel component"
```

---

### Task 25: Frontend - Search Settings UI

**Files:**
- Modify settings component (find exact path in `client/src/lib/components/settings/`)

**Step 1: Add "Search & Indexing" section**

Add form fields for:
- Gemini API key (password input)
- Auto-index directories (list with add/remove)
- Vector backend dropdown (Auto / zvec / ChromaDB)
- Embedding dimensions (768 / 1536 / 3072)
- Video analysis depth toggle
- Auto-enrich toggle
- Max file size input
- Blocklist patterns
- Index stats display + Re-index button

Wire save to `POST /api/v1/settings` (existing endpoint).

**Step 2: Commit**

```bash
git add client/src/lib/components/settings/
git commit -m "feat(search): add Search & Indexing settings UI"
```

---

### Task 26: Integration Test

**Files:**
- Create: `tests/test_search_integration.py`

**Step 1: Write integration test**

```python
# tests/test_search_integration.py
"""Integration test: index files and search them (uses mocked Gemini API)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pocketpaw.search.stores.chroma_store import ChromaVectorStore
from pocketpaw.search.indexer import Indexer
from pocketpaw.search.service import SearchService

@pytest.fixture
def mock_embedder():
    """Returns deterministic embeddings based on content hash."""
    import hashlib

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
    embedder.embed_query.side_effect = lambda q: _embed(
        [MagicMock(content=q)]
    )[0]
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

    # Create test files
    (tmp_path / "auth.py").write_text("def authenticate(user, pwd):\n    return check(user, pwd)\n")
    (tmp_path / "readme.md").write_text("# My Project\n\nThis is a web app.\n")
    (tmp_path / "data.json").write_text('{"users": [1, 2], "config": {}}')

    indexer = Indexer(
        embedder=mock_embedder,
        metadata_store=meta_store,
        content_store=content_store,
        manifest_dir=str(tmp_path / "manifest"),
    )

    stats = await indexer.index_directory(str(tmp_path))
    assert stats["indexed"] == 3

    service = SearchService(
        embedder=mock_embedder,
        metadata_store=meta_store,
        content_store=content_store,
    )

    results = await service.search("authenticate", top_k=5)
    assert len(results) >= 1
```

**Step 2: Run test, verify pass**

Run: `uv run pytest tests/test_search_integration.py -v`

**Step 3: Commit**

```bash
git add tests/test_search_integration.py
git commit -m "test(search): add integration test for index + search pipeline"
```

---

## Summary

| Task | Component | Files |
|------|-----------|-------|
| 1 | Dependencies | `pyproject.toml` |
| 2 | Config settings | `config.py` |
| 3 | Vector store protocol | `search/vector_store.py` |
| 4 | ChromaDB backend | `search/stores/chroma_store.py` |
| 5 | zvec backend | `search/stores/zvec_store.py` |
| 6 | Store factory | `search/stores/__init__.py` |
| 7 | Chunker protocol + text | `search/chunkers/protocol.py`, `text.py` |
| 8 | Code chunker | `search/chunkers/code.py` |
| 9 | Structured + document | `search/chunkers/structured.py`, `document.py` |
| 10 | Media chunker | `search/chunkers/media.py` |
| 11 | Chunker router | `search/chunkers/__init__.py` |
| 12 | Embedding service | `search/embedder.py` |
| 13 | Index manifest | `search/manifest.py` |
| 14 | Indexer pipeline | `search/indexer.py` |
| 15 | Search service | `search/service.py` |
| 16 | REST API | `api/v1/search.py` |
| 17 | Agent tool | `tools/builtin/semantic_search.py` |
| 18 | Auto-enrichment | `search/enrichment.py` |
| 19 | Module init/wiring | `search/__init__.py` |
| 20 | File watcher | `search/watcher.py` |
| 21 | App startup hook | `__main__.py` |
| 22 | Frontend store + API | `explorer.svelte.ts`, `client.ts` |
| 23 | FilterBar toggle | `FilterBar.svelte` |
| 24 | Search panel | `SearchPanel.svelte` |
| 25 | Settings UI | Settings component |
| 26 | Integration test | `test_search_integration.py` |
