from unittest.mock import AsyncMock

import pytest

from pocketpaw.search.watcher import FileWatcher


@pytest.fixture
def mock_indexer():
    indexer = AsyncMock()
    indexer.index_file.return_value = True
    indexer.remove_file.return_value = None
    return indexer


def test_watcher_init(mock_indexer, tmp_path):
    watcher = FileWatcher(
        indexer=mock_indexer,
        directories=[str(tmp_path)],
        debounce_ms=100,
    )
    assert watcher._directories == [str(tmp_path)]
    assert watcher._running is False
