from __future__ import annotations

import re

from pocketpaw.search.chunkers.protocol import Chunk

# Regex patterns per language family for splitting by top-level symbols
_PATTERNS: dict[str, re.Pattern] = {
    "python": re.compile(r"^(?=(?:def |class |async def ))", re.MULTILINE),
    "javascript": re.compile(r"^(?=(?:function |class |const |let |var |export ))", re.MULTILINE),
    "typescript": re.compile(
        r"^(?=(?:function |class |const |let |var |export |interface |type ))",
        re.MULTILINE,
    ),
    "rust": re.compile(r"^(?=(?:fn |struct |enum |impl |pub |mod |trait ))", re.MULTILINE),
    "go": re.compile(r"^(?=(?:func |type |var |const ))", re.MULTILINE),
}

_EXT_TO_LANG: dict[str, str] = {
    "py": "python",
    "pyw": "python",
    "js": "javascript",
    "jsx": "javascript",
    "mjs": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
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
            return [
                Chunk(
                    content=content,
                    chunk_type="code",
                    metadata={"file_path": file_path, "language": ext},
                )
            ]

        parts = pattern.split(content)
        chunks: list[Chunk] = []
        preamble = parts[0].strip() if parts else ""

        # Preamble (imports, module-level code)
        if preamble:
            chunks.append(
                Chunk(
                    content=preamble,
                    chunk_type="code",
                    metadata={"file_path": file_path, "language": lang, "symbol": "__preamble__"},
                )
            )

        for part in parts[1:]:
            part = part.strip()
            if not part:
                continue
            symbol = self._extract_symbol(part, lang)
            chunks.append(
                Chunk(
                    content=part,
                    chunk_type="code",
                    metadata={"file_path": file_path, "language": lang, "symbol": symbol},
                )
            )
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
