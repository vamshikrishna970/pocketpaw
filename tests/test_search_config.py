from pocketpaw.config import Settings


def test_search_defaults():
    s = Settings()
    assert s.search_enabled is False
    assert s.search_embedding_model == "gemini-embedding-2-preview"
    assert s.search_embedding_dimensions == 768
    assert s.search_vector_backend == "auto"
    assert s.search_auto_index_dirs == []
    assert s.search_auto_enrich is False
    assert s.search_max_file_size_mb == 50
    assert s.search_video_analysis_depth == "keyframes"
    assert s.search_batch_size == 32
    assert ".git" in s.search_index_blocklist
    assert s.search_index_allowlist == []


def test_search_env_override(monkeypatch):
    monkeypatch.setenv("POCKETPAW_SEARCH_ENABLED", "true")
    monkeypatch.setenv("POCKETPAW_SEARCH_EMBEDDING_DIMENSIONS", "1536")
    s = Settings()
    assert s.search_enabled is True
    assert s.search_embedding_dimensions == 1536
