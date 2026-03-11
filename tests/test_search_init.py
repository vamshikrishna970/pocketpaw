from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_initialize_search(tmp_path):
    with (
        patch("pocketpaw.search.embedder.EmbeddingService") as MockEmbed,
        patch("pocketpaw.search.stores.create_vector_store") as MockStore,
    ):
        mock_store = AsyncMock()
        MockStore.return_value = mock_store
        MockEmbed.return_value = MagicMock()

        from pocketpaw.search import initialize_search

        components = await initialize_search(
            api_key="test",
            vector_backend="chroma",
            dimensions=768,
            data_dir=str(tmp_path),
        )
        assert "service" in components
        assert "indexer" in components
        assert "enrichment" in components


@pytest.mark.asyncio
async def test_module_singletons_set(tmp_path):
    """initialize_search should populate module-level singletons."""
    with (
        patch("pocketpaw.search.embedder.EmbeddingService") as MockEmbed,
        patch("pocketpaw.search.stores.create_vector_store") as MockStore,
    ):
        mock_store = AsyncMock()
        MockStore.return_value = mock_store
        MockEmbed.return_value = MagicMock()

        import pocketpaw.search as search_mod
        from pocketpaw.search import initialize_search

        await initialize_search(
            api_key="test",
            vector_backend="chroma",
            dimensions=768,
            data_dir=str(tmp_path),
        )

        assert search_mod.get_enrichment() is not None
        assert search_mod.get_search_service() is not None
