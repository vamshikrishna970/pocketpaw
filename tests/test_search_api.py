from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pocketpaw.api.v1.search import router
from pocketpaw.search.vector_store import SearchResult

app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_search_service():
    mock_svc = AsyncMock()
    mock_svc.search.return_value = [
        SearchResult(
            id="meta:abc",
            score=0.9,
            metadata={"file_path": "/a.py", "file_name": "a.py"},
        ),
    ]
    with patch("pocketpaw.api.v1.search._get_search_service", return_value=mock_svc):
        yield mock_svc


def test_search_endpoint(client):
    resp = client.get("/api/v1/search", params={"q": "hello", "top_k": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) == 1


def test_search_missing_query(client):
    resp = client.get("/api/v1/search")
    assert resp.status_code == 422


def test_stats_endpoint(client):
    with patch("pocketpaw.api.v1.search._get_manifest") as mock_manifest:
        mock_manifest.return_value.stats.return_value = {
            "total_files": 10,
            "total_chunks": 50,
        }
        resp = client.get("/api/v1/search/stats")
        assert resp.status_code == 200
