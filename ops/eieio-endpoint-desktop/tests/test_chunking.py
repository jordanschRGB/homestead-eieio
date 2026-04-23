from app.chunking import split_text


def test_split_text_creates_multiple_chunks_with_overlap():
    text = "A" * 1200 + "\n" + "B" * 1200 + "\n" + "C" * 1200
    chunks = split_text(text, "script.md", chunk_chars=1500, overlap_chars=100)

    assert len(chunks) >= 2
    assert chunks[0].source_name == "script.md"
    assert chunks[1].start_char < chunks[0].end_char


def test_split_text_rejects_invalid_overlap():
    try:
        split_text("hello", "x.md", chunk_chars=100, overlap_chars=100)
    except ValueError as exc:
        assert "smaller than chunk_chars" in str(exc)
    else:
        raise AssertionError("expected ValueError")
