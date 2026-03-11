"""File chunking strategies for semantic search."""

from __future__ import annotations

from pocketpaw.search.chunkers.code import CodeChunker
from pocketpaw.search.chunkers.document import DocumentChunker
from pocketpaw.search.chunkers.media import MediaChunker
from pocketpaw.search.chunkers.structured import StructuredChunker
from pocketpaw.search.chunkers.text import TextChunker

_CODE_EXTS = {
    "py",
    "pyw",
    "js",
    "jsx",
    "mjs",
    "ts",
    "tsx",
    "rs",
    "go",
    "java",
    "kt",
    "c",
    "cpp",
    "h",
    "hpp",
    "cs",
    "rb",
    "php",
    "swift",
    "scala",
    "sh",
    "bash",
    "zsh",
    "ps1",
    "lua",
    "r",
    "dart",
    "zig",
    "nim",
    "ex",
    "exs",
    "erl",
    "hs",
    "ml",
    "clj",
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
