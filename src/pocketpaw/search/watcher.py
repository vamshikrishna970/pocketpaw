from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class FileWatcher:
    """Watches directories for changes and triggers incremental indexing."""

    def __init__(
        self,
        indexer: Any,
        directories: list[str],
        debounce_ms: int = 2000,
    ) -> None:
        self._indexer = indexer
        self._directories = directories
        self._debounce_s = debounce_ms / 1000
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        logger.info("File watcher started for %d directories", len(self._directories))

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("File watcher stopped")

    async def _watch_loop(self) -> None:
        try:
            from watchfiles import Change, awatch
        except ImportError:
            logger.error("watchfiles not installed, file watching disabled")
            return

        try:
            async for changes in awatch(
                *self._directories,
                debounce=int(self._debounce_s * 1000),
                stop_event=asyncio.Event() if not self._running else None,
            ):
                if not self._running:
                    break
                for change_type, path in changes:
                    try:
                        if change_type in (Change.added, Change.modified):
                            await self._indexer.index_file(path)
                        elif change_type == Change.deleted:
                            await self._indexer.remove_file(path)
                    except Exception:
                        logger.exception("Error processing change for %s", path)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("File watcher error")
