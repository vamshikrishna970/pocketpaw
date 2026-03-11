from unittest.mock import AsyncMock, patch

import pytest

from pocketpaw.search.vector_store import SearchResult
from pocketpaw.tools.builtin.semantic_search import SemanticSearchTool


@pytest.fixture
def mock_service():
    svc = AsyncMock()
    svc.search.return_value = [
        SearchResult(
            id="meta:1",
            score=0.92,
            metadata={
                "file_path": "/src/auth.py",
                "file_name": "auth.py",
                "content_preview": "def authenticate(user, password):",
            },
        ),
        SearchResult(
            id="chunk:2:0",
            score=0.85,
            metadata={
                "file_path": "/src/login.py",
                "file_name": "login.py",
                "content_preview": "class LoginHandler:",
            },
        ),
    ]
    return svc


@pytest.mark.asyncio
async def test_execute(mock_service):
    with patch(
        "pocketpaw.tools.builtin.semantic_search._get_search_service",
        return_value=mock_service,
    ):
        tool = SemanticSearchTool()
        result = await tool.execute(query="authentication logic")
        assert "auth.py" in result
        assert "0.92" in result
        mock_service.search.assert_called_once()


def test_tool_properties():
    tool = SemanticSearchTool()
    assert tool.name == "semantic_search"
    assert "query" in tool.parameters["properties"]
    assert tool.trust_level == "standard"
