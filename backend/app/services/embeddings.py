import httpx
from typing import List
from abc import ABC, abstractmethod
from app.core.config import settings
import structlog

logger = structlog.get_logger()

class EmbeddingProvider(ABC):
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        pass

class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    def _validate_dimension(self, embedding: List[float]) -> List[float]:
        if not embedding:
            raise ValueError("Ollama returned empty embedding.")
        if len(embedding) != 768:
            raise ValueError(f"Expected embedding dimension 768, got {len(embedding)}")
        return embedding

    def generate_embedding(self, text: str) -> List[float]:
        try:
            response = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding", [])
            return self._validate_dimension(embedding)
        except httpx.HTTPError as e:
            logger.error("ollama_embedding_failed", error=str(e), model=self.model)
            raise RuntimeError(f"Ollama embedding model '{self.model}' is unavailable or failed: {str(e)}")

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            response = httpx.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": texts},
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [])
            if not embeddings:
                raise ValueError("Ollama returned empty embeddings array.")
            return [self._validate_dimension(emb) for emb in embeddings]
        except httpx.HTTPError as e:
            logger.error("ollama_batch_embedding_failed", error=str(e), model=self.model)
            raise RuntimeError(f"Ollama embedding model '{self.model}' is unavailable or failed: {str(e)}")

def get_embedding_provider() -> EmbeddingProvider:
    # We can use settings to switch providers later if needed
    if settings.EMBEDDING_PROVIDER.lower() == "ollama":
        return OllamaEmbeddingProvider(base_url=settings.OLLAMA_URL, model=settings.EMBEDDING_MODEL)
    else:
        raise ValueError(f"Unsupported embedding provider: {settings.EMBEDDING_PROVIDER}")
