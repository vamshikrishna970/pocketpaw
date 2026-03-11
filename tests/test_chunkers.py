from pocketpaw.search.chunkers.protocol import Chunk
from pocketpaw.search.chunkers.text import TextChunker


def test_chunk_dataclass():
    c = Chunk(content="hello", chunk_type="text", metadata={"heading": "Intro"})
    assert c.content == "hello"
    assert c.chunk_type == "text"


def test_text_chunker_by_paragraphs():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunker = TextChunker()
    chunks = chunker.chunk(text, file_path="/readme.txt")
    assert len(chunks) == 3
    assert chunks[0].content == "First paragraph."


def test_text_chunker_markdown_headings():
    md = "# Title\n\nIntro text.\n\n## Section 1\n\nContent one.\n\n## Section 2\n\nContent two."
    chunker = TextChunker()
    chunks = chunker.chunk(md, file_path="/doc.md")
    assert len(chunks) >= 2
    # Headings should be preserved as context
    assert any("Section 1" in c.metadata.get("heading", "") for c in chunks)


def test_text_chunker_empty():
    chunker = TextChunker()
    chunks = chunker.chunk("", file_path="/empty.txt")
    assert chunks == []
