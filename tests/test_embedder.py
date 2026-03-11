from unittest.mock import MagicMock, patch

import pytest

from pocketpaw.search.chunkers.protocol import Chunk
from pocketpaw.search.embedder import EmbeddingService


@pytest.fixture
def mock_genai():
    with patch("pocketpaw.search.embedder.genai") as mock:
        client = MagicMock()
        mock.Client.return_value = client

        # Mock embed_content response
        embedding = MagicMock()
        embedding.values = [0.1] * 768
        result = MagicMock()
        result.embeddings = [embedding]
        client.models.embed_content.return_value = result

        yield client


@pytest.mark.asyncio
async def test_embed_text(mock_genai):
    svc = EmbeddingService(api_key="test-key", dimensions=768)
    chunks = [Chunk(content="hello world", chunk_type="text", metadata={})]
    embeddings = await svc.embed_chunks(chunks)
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 768
    mock_genai.models.embed_content.assert_called_once()


@pytest.mark.asyncio
async def test_embed_image(mock_genai):
    svc = EmbeddingService(api_key="test-key", dimensions=768)
    chunks = [Chunk(content=b"\x89PNG", chunk_type="image", mime_type="image/png", metadata={})]
    embeddings = await svc.embed_chunks(chunks)
    assert len(embeddings) == 1


@pytest.mark.asyncio
async def test_embed_query(mock_genai):
    svc = EmbeddingService(api_key="test-key", dimensions=768)
    embedding = await svc.embed_query("find auth code")
    assert len(embedding) == 768


@pytest.mark.asyncio
async def test_embed_code_query(mock_genai):
    svc = EmbeddingService(api_key="test-key", dimensions=768)
    embedding = await svc.embed_query("def authenticate():")
    assert len(embedding) == 768
