import json

from pocketpaw.search.chunkers.structured import StructuredChunker


def test_json_chunking():
    data = json.dumps({"users": [1, 2], "config": {"debug": True}, "version": "1.0"})
    chunker = StructuredChunker()
    chunks = chunker.chunk(data, file_path="/data.json")
    assert len(chunks) == 3  # one per top-level key


def test_yaml_chunking():
    data = "key1: value1\nkey2:\n  nested: true\nkey3: value3\n"
    chunker = StructuredChunker()
    chunks = chunker.chunk(data, file_path="/config.yaml")
    assert len(chunks) >= 1


def test_csv_chunking():
    data = "name,age\nAlice,30\nBob,25\nCharlie,35\nDave,40\n"
    chunker = StructuredChunker()
    chunks = chunker.chunk(data, file_path="/people.csv")
    assert len(chunks) >= 1
