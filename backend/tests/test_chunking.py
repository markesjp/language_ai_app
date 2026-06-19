from app.services.rag.chunking import chunk_text


def test_chunk_text_keeps_short_text_in_single_chunk():
    assert chunk_text("hello world", chunk_size=50) == ["hello world"]


def test_chunk_text_uses_overlap_for_long_text():
    chunks = chunk_text("a" * 120, chunk_size=50, overlap=10)

    assert len(chunks) == 3
    assert chunks[0] == "a" * 50
    assert chunks[1] == "a" * 50
    assert chunks[2] == "a" * 40
