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
        return [Chunk(content=content, chunk_type="structured", metadata={"file_path": file_path})]

    def _chunk_json(self, content: str, file_path: str) -> list[Chunk]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return [
                Chunk(content=content, chunk_type="structured", metadata={"file_path": file_path})
            ]
        if isinstance(data, dict):
            return [
                Chunk(
                    content=json.dumps({k: v}, indent=2),
                    chunk_type="structured",
                    metadata={"file_path": file_path, "key": k},
                )
                for k, v in data.items()
            ]
        return [Chunk(content=content, chunk_type="structured", metadata={"file_path": file_path})]

    def _chunk_yaml(self, content: str, file_path: str) -> list[Chunk]:
        # Split YAML by top-level keys (lines without indentation)
        import re

        sections = re.split(r"(?=^\S)", content, flags=re.MULTILINE)
        return [
            Chunk(content=s.strip(), chunk_type="structured", metadata={"file_path": file_path})
            for s in sections
            if s.strip()
        ]

    def _chunk_toml(self, content: str, file_path: str) -> list[Chunk]:
        import re

        sections = re.split(r"(?=^\[)", content, flags=re.MULTILINE)
        return [
            Chunk(content=s.strip(), chunk_type="structured", metadata={"file_path": file_path})
            for s in sections
            if s.strip()
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
            chunks.append(
                Chunk(
                    content=text,
                    chunk_type="structured",
                    metadata={"file_path": file_path, "row_start": i, "row_end": i + len(batch)},
                )
            )
        return chunks
