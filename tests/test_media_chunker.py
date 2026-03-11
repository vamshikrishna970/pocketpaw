import struct
import zlib

from pocketpaw.search.chunkers.media import MediaChunker


def test_image_chunk(tmp_path):
    # Create a tiny 1x1 PNG
    def make_png():
        sig = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        ihdr = b"IHDR" + ihdr_data
        ihdr_chunk = struct.pack(">I", 13) + ihdr + struct.pack(">I", zlib.crc32(ihdr) & 0xFFFFFFFF)
        raw = b"\x00\xff\x00\x00"
        idat_data = zlib.compress(raw)
        idat = b"IDAT" + idat_data
        idat_chunk = (
            struct.pack(">I", len(idat_data))
            + idat
            + struct.pack(">I", zlib.crc32(idat) & 0xFFFFFFFF)
        )
        iend = b"IEND"
        iend_chunk = struct.pack(">I", 0) + iend + struct.pack(">I", zlib.crc32(iend) & 0xFFFFFFFF)
        return sig + ihdr_chunk + idat_chunk + iend_chunk

    img = tmp_path / "test.png"
    img.write_bytes(make_png())
    chunker = MediaChunker()
    chunks = chunker.chunk(img.read_bytes(), str(img))
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "image"
    assert chunks[0].mime_type == "image/png"
    assert isinstance(chunks[0].content, bytes)


def test_audio_chunk(tmp_path):
    audio = tmp_path / "test.mp3"
    audio.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 100)
    chunker = MediaChunker()
    chunks = chunker.chunk(audio.read_bytes(), str(audio))
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "audio"


def test_unsupported_format():
    chunker = MediaChunker()
    chunks = chunker.chunk(b"data", "/file.xyz")
    assert chunks == []
