from __future__ import annotations

import hashlib
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

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
            metadata=[
                {
                    "file_path": file_path,
                    "file_name": file_name,
                    "extension": ext,
                    "size": path.stat().st_size,
                    "last_modified": path.stat().st_mtime,
                }
            ],
        )

        # Upsert content chunks
        chunk_ids = [f"chunk:{path_hash}:{i}" for i in range(len(chunks))]
        chunk_meta = []
        for i, chunk in enumerate(chunks):
            preview = ""
            if isinstance(chunk.content, str):
                preview = chunk.content[:200]
            chunk_meta.append(
                {
                    "file_path": file_path,
                    "chunk_index": i,
                    "chunk_type": chunk.chunk_type,
                    "content_hash": content_hash,
                    "content_preview": preview,
                    "last_modified": path.stat().st_mtime,
                    **{
                        k: v
                        for k, v in chunk.metadata.items()
                        if k != "file_path" and isinstance(v, str | int | float | bool)
                    },
                }
            )

        await self._content_store.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            metadata=chunk_meta,
        )

        self._manifest.set_file(file_path, content_hash=content_hash, chunk_count=len(chunks))
        return True

    async def index_directory(
        self,
        directory: str,
        recursive: bool = True,
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
