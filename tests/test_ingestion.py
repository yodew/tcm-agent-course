from tcm_agent.ingestion import chunk_text


def test_chunks_when_document_long_preserves_overlap_and_end() -> None:
    # Given
    text = "前" * 650 + "后" * 150
    # When
    chunks = chunk_text(text)
    # Then
    assert len(chunks) == 2
    assert chunks[0][-80:] == chunks[1][:80]
    assert chunks[1].endswith("后" * 150)
    assert all(len(chunk) <= 600 for chunk in chunks)
