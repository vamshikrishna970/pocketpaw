# Gemini Embedding 2.0 Semantic Search - Design Document

**Date:** 2026-03-11
**Status:** Approved

## Overview

Add semantic search to PocketPaw using Google Gemini Embedding 2.0, enabling natural language search across all file types (code, text, images, video, audio, documents). Shared embedding index powers both the file explorer UI and the AI agent.

## Architecture

```
+---------------------------------------------------+
|              Gemini Embedding 2.0 API              |
|        (multimodal: text, image, video, audio)     |
+-------------------------+-------------------------+
                          |
+-------------------------v-------------------------+
|                 Embedding Service                  |
|  - Auth: Google OAuth OR standalone API key        |
|  - Chunking engine (per file-type strategies)      |
|  - Native multimodal embedding (no description     |
|    generation needed for images/audio/video)       |
+-------------------------+-------------------------+
                          |
+-------------------------v-------------------------+
|              Vector Store Abstraction              |
|  +-------------+    +------------------+          |
|  |    zvec     |    |  ChromaDB local  |          |
|  | (Linux/Mac) |    |  (Windows/all)   |          |
|  +-------------+    +------------------+          |
|  Storage: ~/.pocketpaw/embeddings/                |
+-------------------------+-------------------------+
                          |
          +---------------+---------------+
          v               v               v
   +-----------+   +-----------+   +-------------+
   | Explorer  |   |  Agent    |   | Agent Auto  |
   | Search UI |   |  Tool     |   | Enrichment  |
   +-----------+   +-----------+   +-------------+
```

## Embedding Service

### Model & SDK

- **Model:** `gemini-embedding-2-preview` (multimodal) / `gemini-embedding-001` (text-only stable)
- **SDK:** `google-genai` package, `client.models.embed_content()`
- **Dimensions:** Configurable 128-3072 via Matryoshka Representation Learning. Default: **768**
- **Auth:** Google OAuth (reuse existing `OAuthManager`) or standalone `POCKETPAW_SEARCH_GEMINI_API_KEY`

### Multimodal Input Limits

| Type | Method | Limits |
|------|--------|--------|
| Text | `contents="string"` | 8,192 tokens max |
| Images | `Part.from_bytes(data, mime_type)` | Max 6 per request |
| Audio | `Part.from_bytes(data, mime_type)` | Max 80 seconds |
| Video | `Part.from_bytes(data, mime_type)` | Max 128 seconds |
| PDF | `Part.from_bytes(data, mime_type)` | Max 6 pages |

### Task Types (text embedding optimization)

- `RETRIEVAL_DOCUMENT` - for indexing files
- `RETRIEVAL_QUERY` - for search queries
- `CODE_RETRIEVAL_QUERY` - for code search queries
- `SEMANTIC_SIMILARITY` - for similarity comparisons

## Chunking Engine

Protocol-based, one chunker per content category in `src/pocketpaw/search/chunkers/`:

| Category | Strategy | Output |
|----------|----------|--------|
| **Code** (`.py`, `.js`, `.ts`, etc.) | Split by functions/classes via tree-sitter or regex fallback | Code blocks with context (file path, function name) |
| **Markdown/text** (`.md`, `.txt`, `.rst`) | Split by headings/paragraphs | Sections with heading hierarchy |
| **Structured data** (`.json`, `.yaml`, `.toml`, `.csv`) | Split by top-level keys or row batches | Key-value groups or row chunks |
| **Documents** (`.pdf`, `.docx`) | Page-level extraction via `pymupdf`/`python-docx` | Page text chunks (PDF: 6-page chunks per API limit) |
| **Images** (`.png`, `.jpg`, `.svg`, etc.) | Native multimodal embed via `Part.from_bytes()` | Single embedding per image |
| **Video** (`.mp4`, `.webm`, etc.) | Keyframes via `ffmpeg` (default) or full analysis (configurable) | Keyframe embeddings or frame + transcript chunks |
| **Audio** (`.mp3`, `.wav`, etc.) | Native multimodal embed (up to 80s), split longer files | Audio segment embeddings |

Each chunk stores metadata: `file_path`, `chunk_index`, `chunk_type`, `content_hash`, `last_modified`.

## Vector Store Abstraction

### Protocol (`src/pocketpaw/search/vector_store.py`)

```python
class VectorStoreProtocol(Protocol):
    async def initialize(self, collection: str, dimensions: int) -> None: ...
    async def upsert(self, ids: list[str], embeddings: list[list[float]], metadata: list[dict]) -> None: ...
    async def query(self, embedding: list[float], top_k: int = 10, filters: dict | None = None) -> list[SearchResult]: ...
    async def delete(self, ids: list[str]) -> None: ...
    async def delete_by_filter(self, filters: dict) -> None: ...
    async def count(self) -> int: ...
    async def close(self) -> None: ...
```

### Backends

- **zvec** (Linux x86_64/ARM64, macOS ARM64): In-process, file-based at `~/.pocketpaw/embeddings/zvec/`
- **ChromaDB** (Windows, all platforms as fallback): Persistent local mode at `~/.pocketpaw/embeddings/chroma/`

Auto-selection: Windows -> ChromaDB. Linux/macOS -> try zvec, fall back to ChromaDB. Override via setting.

### Collections

| Collection | Content | Metadata fields |
|-----------|---------|-----------------|
| `file_metadata` | One embedding per file (path + name + extension + type) | `file_path`, `file_name`, `extension`, `file_type`, `size`, `last_modified` |
| `file_contents` | Multiple embeddings per file (chunks) | `file_path`, `chunk_index`, `chunk_type`, `content_hash`, `content_preview`, `last_modified` |

### ID Scheme

- Metadata: `meta:{sha256(absolute_path)}`
- Content chunks: `chunk:{sha256(absolute_path)}:{chunk_index}`

## Indexing Pipeline

### Three modes

1. **Manual** - User triggers from explorer context menu or search panel. `POST /api/v1/search/index`
2. **Auto on startup** - Configured directories in `search_auto_index_dirs` setting
3. **File watcher** - `watchfiles` monitors indexed directories, debounced 2s, incremental updates

### Processing flow

```
File detected
  -> Check blocklist (.git, node_modules, __pycache__, etc.)
  -> Check allowlist (if configured)
  -> Detect file type by extension + mime
  -> Route to appropriate chunker
  -> Check content_hash against stored hash in manifest
  -> If changed: call Gemini embed_content()
      - Text chunks: task_type=RETRIEVAL_DOCUMENT
      - Media files: raw bytes via Part.from_bytes()
      - Large files: split into API-compatible segments
  -> Upsert vectors + metadata into store
  -> Update index manifest
```

### Index manifest (`~/.pocketpaw/embeddings/manifest.json`)

Tracks indexed files with content hashes to avoid re-embedding unchanged files. Stores per-file: `content_hash`, `last_modified`, `chunk_count`, `indexed_at`. Plus aggregate stats.

### Rate limiting & batching

- Batch chunks (configurable, default 32) before API calls
- Exponential backoff on rate limits
- Progress events on the bus as `SystemEvent(type="index_progress")`

## Search API

### Unified service (`src/pocketpaw/search/service.py`)

```python
class SearchService:
    async def search(
        self,
        query: str,
        top_k: int = 10,
        file_types: list[str] | None = None,
        extensions: list[str] | None = None,
        directories: list[str] | None = None,
        search_mode: str = "hybrid",  # "metadata", "content", "hybrid"
    ) -> list[SearchResult]
```

Query embedding uses `RETRIEVAL_QUERY` task type, or `CODE_RETRIEVAL_QUERY` when query looks like code.

### REST endpoints (`src/pocketpaw/api/v1/search.py`)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/search?q=...&top_k=10&mode=hybrid` | Search query |
| `POST /api/v1/search/index` | Trigger manual indexing |
| `GET /api/v1/search/index/status` | Indexing progress |
| `DELETE /api/v1/search/index?path=...` | Remove path from index |
| `GET /api/v1/search/stats` | Index stats |

### WebSocket events

```
Client sends:  {"type": "search", "query": "...", "options": {...}}
Server sends:  {"type": "search_results", "results": [...], "took_ms": 45}
```

## Agent Integration

### Semantic search tool (`src/pocketpaw/tools/builtin/semantic_search.py`)

```python
class SemanticSearchTool(BaseTool):
    name = "semantic_search"
    description = "Search files in the workspace by meaning."
    parameters = {
        "query": "Natural language search query",
        "top_k": "Number of results (default 10)",
        "file_types": "Optional filter: code, image, video, audio, document",
        "search_mode": "metadata, content, or hybrid (default)"
    }
```

### Auto-enrichment (`src/pocketpaw/search/enrichment.py`)

Optional pre-processing in AgentLoop. When `search_auto_enrich=True`:
- Embed user's message
- Query top 5 relevant files
- Inject as context before passing to agent
- Off by default, user opts in via settings

## Frontend

### Explorer FilterBar enhancement

- Toggle between "Name" (filesystem search) and "Smart" (semantic search)
- 500ms debounce in Smart mode
- Results show relevance score badge + content preview snippet

### Dedicated SearchPanel (`client/src/lib/components/search/SearchPanel.svelte`)

- Full search input with filters: file type chips, search mode toggle, directory scope
- Results with file icon, name, path, relevance bar, content preview/thumbnail
- Keyboard navigable, search history (last 20 queries)

### Settings UI - "Search & Indexing" section

- Gemini API key input / OAuth indicator
- Auto-index directories list with folder picker
- Vector backend selector (Auto / zvec / ChromaDB)
- Embedding dimensions dropdown (768 / 1536 / 3072)
- Video analysis depth toggle
- Auto-enrich agent context toggle
- Max file size, blocklist patterns
- Index stats + re-index button + progress bar

### Explorer indexing controls

- Context menu: "Index this folder" / "Remove from index"
- Indexed status indicator in toolbar
- Progress indicator in status bar

## Configuration

### New settings (`config.py`)

```python
search_enabled: bool = False
search_gemini_api_key: str = ""
search_use_oauth: bool = True
search_embedding_model: str = "gemini-embedding-2-preview"
search_embedding_dimensions: int = 768
search_vector_backend: str = "auto"          # "auto", "zvec", "chroma"
search_auto_index_dirs: list[str] = []
search_auto_enrich: bool = False
search_max_file_size_mb: int = 50
search_video_analysis_depth: str = "keyframes"  # "keyframes" or "full"
search_batch_size: int = 32
search_index_blocklist: list[str] = [".git", "node_modules", "__pycache__", ".venv", "venv", ".env", "dist", "build", ".next"]
search_index_allowlist: list[str] = []
```

All env vars prefixed with `POCKETPAW_SEARCH_*`.

## Dependencies

| Package | Purpose | Optional? |
|---------|---------|-----------|
| `google-genai` | Gemini Embedding API client | Required when search enabled |
| `zvec` | Vector store (Linux/macOS) | Optional, auto-detected |
| `chromadb` | Vector store (Windows/fallback) | Optional, auto-detected |
| `watchfiles` | File system watcher | Required when search enabled |
| `pymupdf` | PDF text extraction | Optional |
| `python-docx` | DOCX text extraction | Optional |

Packaged as: `pip install pocketpaw[search]`

## File Structure

```
src/pocketpaw/search/
    __init__.py
    service.py              # SearchService - unified query interface
    embedder.py             # Gemini API wrapper
    indexer.py              # Indexing pipeline + file watcher
    enrichment.py           # Agent auto-enrichment
    manifest.py             # Index manifest management
    vector_store.py         # VectorStoreProtocol
    stores/
        __init__.py
        zvec_store.py
        chroma_store.py
    chunkers/
        __init__.py
        protocol.py
        code.py
        text.py
        structured.py
        document.py
        media.py

src/pocketpaw/api/v1/search.py
src/pocketpaw/tools/builtin/semantic_search.py
client/src/lib/components/search/SearchPanel.svelte
```
