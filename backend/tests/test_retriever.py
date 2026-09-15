from app.services.retriever import RetrievalResult, RetrievedChunk

def test_retrieval_result_contract():
    result = RetrievalResult(
        results=[],
        has_relevant_context=False
    )
    assert result.has_relevant_context is False
    assert len(result.results) == 0

    chunk = RetrievedChunk(
        source_id="file1.md",
        episode_title="Ep 1",
        guest_name=None,
        source_url="local://file1.md",
        transcript_url=None,
        chunk_index=0,
        text="Hello",
        similarity=0.9
    )
    result_with_context = RetrievalResult(
        results=[chunk],
        has_relevant_context=True
    )
    assert result_with_context.has_relevant_context is True
    assert result_with_context.results[0].similarity == 0.9
