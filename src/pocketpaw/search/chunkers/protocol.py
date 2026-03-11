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
