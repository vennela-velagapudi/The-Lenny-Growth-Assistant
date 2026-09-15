from app.services.chunker import DocumentChunker

def test_chunker_small_text():
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=10)
    text = "Hello world. " * 10
    chunks = chunker.chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text.strip()

def test_chunker_long_text():
    chunker = DocumentChunker(chunk_size=10, chunk_overlap=2)
    # 1 token = approx 1 word here. Let's make 20 words
    text = "word " * 20
    chunks = chunker.chunk_text(text)
    assert len(chunks) > 1
    # Check overlap
    assert "word" in chunks[1]

def test_chunker_empty_text():
    chunker = DocumentChunker()
    assert chunker.chunk_text("") == []

def test_chunker_paragraphs():
    chunker = DocumentChunker(chunk_size=20, chunk_overlap=5)
    text = "Para 1 is short.\n\nPara 2 is also short."
    chunks = chunker.chunk_text(text)
    assert len(chunks) == 1
    assert "Para 1" in chunks[0]
    assert "Para 2" in chunks[0]
