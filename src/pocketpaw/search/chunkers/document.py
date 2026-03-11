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
        return [Chunk(content=content, chunk_type="text", metadata={"file_path": file_path})]

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
            return [
                Chunk(
                    content=raw,
                    chunk_type="pdf",
                    mime_type="application/pdf",
                    metadata={"file_path": file_path, "pages": "all"},
                )
            ]

        if page_count <= _PDF_PAGE_BATCH:
            return [
                Chunk(
                    content=raw,
                    chunk_type="pdf",
                    mime_type="application/pdf",
                    metadata={"file_path": file_path, "pages": f"1-{page_count}"},
                )
            ]

        # Split into 6-page segments
        chunks: list[Chunk] = []
        doc = pymupdf.open(file_path)
        for start in range(0, page_count, _PDF_PAGE_BATCH):
            end = min(start + _PDF_PAGE_BATCH, page_count)
            sub = pymupdf.open()
            sub.insert_pdf(doc, from_page=start, to_page=end - 1)
            chunks.append(
                Chunk(
                    content=sub.tobytes(),
                    chunk_type="pdf",
                    mime_type="application/pdf",
                    metadata={"file_path": file_path, "pages": f"{start + 1}-{end}"},
                )
            )
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
                parts.append(
                    Chunk(
                        content=current.strip(),
                        chunk_type="text",
                        metadata={"file_path": file_path},
                    )
                )
                current = ""
            current += para + "\n\n"
        if current.strip():
            parts.append(
                Chunk(
                    content=current.strip(),
                    chunk_type="text",
                    metadata={"file_path": file_path},
                )
            )
        return parts
