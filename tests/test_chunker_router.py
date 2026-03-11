from pocketpaw.search.chunkers import get_chunker_for_file


def test_python_file():
    chunker = get_chunker_for_file("/app.py")
    from pocketpaw.search.chunkers.code import CodeChunker

    assert isinstance(chunker, CodeChunker)


def test_markdown_file():
    chunker = get_chunker_for_file("/readme.md")
    from pocketpaw.search.chunkers.text import TextChunker

    assert isinstance(chunker, TextChunker)


def test_json_file():
    chunker = get_chunker_for_file("/data.json")
    from pocketpaw.search.chunkers.structured import StructuredChunker

    assert isinstance(chunker, StructuredChunker)


def test_image_file():
    chunker = get_chunker_for_file("/photo.png")
    from pocketpaw.search.chunkers.media import MediaChunker

    assert isinstance(chunker, MediaChunker)


def test_pdf_file():
    chunker = get_chunker_for_file("/doc.pdf")
    from pocketpaw.search.chunkers.document import DocumentChunker

    assert isinstance(chunker, DocumentChunker)


def test_unknown_falls_back_to_text():
    chunker = get_chunker_for_file("/notes.txt")
    from pocketpaw.search.chunkers.text import TextChunker

    assert isinstance(chunker, TextChunker)
