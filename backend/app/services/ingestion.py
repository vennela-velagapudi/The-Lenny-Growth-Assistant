import os
import hashlib
from typing import List, Tuple
from sqlmodel import Session, select
from app.db.models import TranscriptSource, TranscriptChunk
from app.services.chunker import DocumentChunker
from app.services.embeddings import get_embedding_provider
import structlog

logger = structlog.get_logger()

class IngestionService:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.chunker = DocumentChunker(chunk_size=600, chunk_overlap=100)
        self.embedding_provider = get_embedding_provider()

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def process_file(self, file_path: str) -> Tuple[bool, int]:
        """Processes a single markdown/text file. Returns (is_new_or_updated, chunks_created)"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        filename = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if not content.strip():
            logger.warning("empty_file", file=filename)
            return False, 0

        content_hash = self._compute_hash(content)
        
        # Check idempotency
        stmt = select(TranscriptSource).where(TranscriptSource.source_id == filename)
        existing = self.db.exec(stmt).first()

        if existing:
            if existing.content_hash == content_hash:
                logger.info("skip_unchanged_file", file=filename)
                return False, 0
            
            # If changed, delete old chunks (handled by cascade)
            logger.info("updating_file", file=filename)
            existing.content_hash = content_hash
            source_record = existing
        else:
            logger.info("ingesting_new_file", file=filename)
            # Basic metadata extraction from filename or content
            episode_title = filename.replace("_", " ").replace(".md", "").strip()
            source_record = TranscriptSource(
                source_id=filename,
                episode_title=episode_title,
                content_hash=content_hash,
                source_url=f"local://{filename}"
            )
            self.db.add(source_record)

        self.db.commit()
        self.db.refresh(source_record)
        
        # Clear existing chunks if updating
        if existing:
            self.db.query(TranscriptChunk).filter(TranscriptChunk.transcript_source_id == source_record.id).delete()
            self.db.commit()

        chunks = self.chunker.chunk_text(content)
        if not chunks:
            return True, 0

        logger.info("generating_embeddings", file=filename, count=len(chunks))
        embeddings = self.embedding_provider.generate_embeddings(chunks)

        db_chunks = []
        for i, (text, emb) in enumerate(zip(chunks, embeddings)):
            db_chunks.append(TranscriptChunk(
                transcript_source_id=source_record.id,
                chunk_index=i,
                text=text,
                embedding=emb,
                token_count=len(self.chunker.encoder.encode(text))
            ))
            
        self.db.add_all(db_chunks)
        self.db.commit()
        
        return True, len(db_chunks)
