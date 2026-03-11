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
