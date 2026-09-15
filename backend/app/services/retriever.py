from typing import List, Optional
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db.models import TranscriptChunk, TranscriptSource
from app.services.embeddings import get_embedding_provider
import structlog

logger = structlog.get_logger()

class RetrievedChunk(BaseModel):
    source_id: str
    episode_title: str
    guest_name: Optional[str]
    source_url: Optional[str]
    transcript_url: Optional[str]
    chunk_index: int
    text: str
    similarity: float

class RetrievalResult(BaseModel):
    results: List[RetrievedChunk]
    has_relevant_context: bool

class TranscriptRetriever:
    def __init__(self, db_session: Session, top_k: int = 5, similarity_threshold: float = 0.5):
        self.db = db_session
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.embedding_provider = get_embedding_provider()

    def retrieve(self, query: str) -> RetrievalResult:
        logger.info("retrieving_context", query=query)
        
        try:
            query_embedding = self.embedding_provider.generate_embedding(query)
        except Exception as e:
            logger.error("retrieval_embedding_failed", error=str(e))
            return RetrievalResult(results=[], has_relevant_context=False)

        # pgvector cosine similarity is `<=>` operator (returns distance, so similarity is 1 - distance)
        # Using SQLAlchemy/SQLModel l2_distance or cosine_distance
        # Vector.cosine_distance(query_embedding)
        
        distance_expr = TranscriptChunk.embedding.cosine_distance(query_embedding)
        
        stmt = (
            select(TranscriptChunk, TranscriptSource, distance_expr.label("distance"))
            .join(TranscriptSource)
            .order_by(distance_expr)
            .limit(self.top_k)
        )
        
        db_results = self.db.exec(stmt).all()
        
        retrieved_chunks = []
        has_relevant = False
        
        for chunk, source, distance in db_results:
            similarity = 1.0 - float(distance)
            if similarity >= self.similarity_threshold:
                has_relevant = True
                
            retrieved_chunks.append(RetrievedChunk(
                source_id=source.source_id,
                episode_title=source.episode_title,
                guest_name=source.guest_name,
                source_url=source.source_url,
                transcript_url=source.transcript_url,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                similarity=similarity
            ))
            
        logger.info("retrieval_complete", count=len(retrieved_chunks), has_relevant=has_relevant)
        
        # If the best result is below threshold, we still return the results but flag it
        return RetrievalResult(
            results=retrieved_chunks,
            has_relevant_context=has_relevant
        )
