from unittest.mock import AsyncMock

import pytest

from pocketpaw.search.enrichment import SearchEnrichment
from pocketpaw.search.vector_store import SearchResult


@pytest.fixture
def mock_service():
    svc = AsyncMock()
    svc.search.return_value = [
        SearchResult(
            id="1",
            score=0.9,
            metadata={"file_path": "/auth.py", "content_preview": "def auth():"},
        ),
        SearchResult(
            id="2",
            score=0.8,
            metadata={"file_path": "/login.py", "content_preview": "class Login:"},
        ),
    ]
    return svc


@pytest.mark.asyncio
async def test_enrich_returns_context(mock_service):
    enricher = SearchEnrichment(mock_service, top_k=5)
    ctx = await enricher.enrich("how does auth work?")
    assert "/auth.py" in ctx
    assert "/login.py" in ctx


@pytest.mark.asyncio
async def test_enrich_empty_query(mock_service):
    enricher = SearchEnrichment(mock_service)
    ctx = await enricher.enrich("")
    assert ctx == ""


@pytest.mark.asyncio
async def test_enrich_no_results():
    svc = AsyncMock()
    svc.search.return_value = []
    enricher = SearchEnrichment(svc)
    ctx = await enricher.enrich("something obscure")
    assert ctx == ""
