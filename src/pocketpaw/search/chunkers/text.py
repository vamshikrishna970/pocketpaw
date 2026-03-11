from __future__ import annotations

import re

from pocketpaw.search.chunkers.protocol import Chunk


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
            chunks.append(
                Chunk(
                    content=section,
                    chunk_type="text",
                    metadata={"file_path": file_path, "heading": heading},
                )
            )
        return chunks

    def _chunk_by_paragraphs(self, content: str, file_path: str) -> list[Chunk]:
        paragraphs = re.split(r"\n\s*\n", content)
        chunks: list[Chunk] = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            chunks.append(
                Chunk(
                    content=para,
                    chunk_type="text",
                    metadata={"file_path": file_path},
                )
            )
        return chunks
