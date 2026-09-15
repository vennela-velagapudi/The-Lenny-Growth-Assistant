import pytest
from app.services.embeddings import OllamaEmbeddingProvider
import httpx

def test_ollama_provider_init():
    provider = OllamaEmbeddingProvider("http://localhost:11434", "nomic-embed-text")
    assert provider.base_url == "http://localhost:11434"
    assert provider.model == "nomic-embed-text"

def test_ollama_generate_embedding_success(monkeypatch):
    class MockResponse:
        def raise_for_status(self): pass
        def json(self): return {"embedding": [0.1] * 768}
        
    def mock_post(*args, **kwargs):
        return MockResponse()
        
    monkeypatch.setattr(httpx, "post", mock_post)
    provider = OllamaEmbeddingProvider("http://localhost", "nomic-embed-text")
    embedding = provider.generate_embedding("hello")
    assert len(embedding) == 768

def test_ollama_generate_embedding_wrong_dimension(monkeypatch):
    class MockResponse:
        def raise_for_status(self): pass
        def json(self): return {"embedding": [0.1, 0.2, 0.3]}
        
    def mock_post(*args, **kwargs):
        return MockResponse()
        
    monkeypatch.setattr(httpx, "post", mock_post)
    provider = OllamaEmbeddingProvider("http://localhost", "nomic-embed-text")
    with pytest.raises(ValueError, match="Expected embedding dimension 768"):
        provider.generate_embedding("hello")

def test_ollama_generate_embedding_error(monkeypatch):
    def mock_post(*args, **kwargs):
        raise httpx.HTTPError("Network error")
        
    monkeypatch.setattr(httpx, "post", mock_post)
    provider = OllamaEmbeddingProvider("http://localhost", "nomic-embed-text")
    with pytest.raises(RuntimeError, match="unavailable or failed"):
        provider.generate_embedding("hello")
