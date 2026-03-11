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
        return [
            Chunk(
                content=data,
                chunk_type="image",
                mime_type=mime,
                metadata={"file_path": file_path, "size_bytes": len(data)},
            )
        ]

    def _chunk_audio(self, data: bytes, file_path: str, mime: str) -> list[Chunk]:
        # For now, send as single chunk. Splitting long audio is a future enhancement.
        return [
            Chunk(
                content=data,
                chunk_type="audio",
                mime_type=mime,
                metadata={"file_path": file_path, "size_bytes": len(data)},
            )
        ]

    def _chunk_video(self, data: bytes, file_path: str, mime: str) -> list[Chunk]:
        # For keyframes mode, send raw video (Gemini handles up to 128s).
        # Full analysis mode with ffmpeg keyframe extraction is a future enhancement.
        return [
            Chunk(
                content=data,
                chunk_type="video",
                mime_type=mime,
                metadata={
                    "file_path": file_path,
                    "size_bytes": len(data),
                    "analysis_depth": self._video_depth,
                },
            )
        ]
