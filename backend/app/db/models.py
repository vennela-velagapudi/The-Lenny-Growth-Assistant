from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
import uuid

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    metadata_json: Optional[str] = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)
    sessions: List["Session"] = Relationship(back_populates="user")

class Session(SQLModel, table=True):
    __tablename__ = "sessions"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id")
    title: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    user: User = Relationship(back_populates="sessions")
    messages: List["Message"] = Relationship(back_populates="session")
    
class Message(SQLModel, table=True):
    __tablename__ = "messages"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="sessions.id")
    role: str
    content: str
    created_at: datetime = Field(default_factory=utc_now)
    session: Session = Relationship(back_populates="messages")
    artifacts: List["Artifact"] = Relationship(back_populates="message")
    
class Artifact(SQLModel, table=True):
    __tablename__ = "artifacts"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    message_id: uuid.UUID = Field(foreign_key="messages.id")
    artifact_type: str
    content: str
    created_at: datetime = Field(default_factory=utc_now)
    message: Message = Relationship(back_populates="artifacts")

class TranscriptSource(SQLModel, table=True):
    __tablename__ = "transcript_sources"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_id: str = Field(index=True, unique=True, description="External ID or filename")
    episode_title: str
    guest_name: Optional[str] = None
    source_url: Optional[str] = None
    transcript_url: Optional[str] = None
    content_hash: str = Field(index=True, description="Hash of the raw content for idempotency")
    metadata_json: Optional[str] = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    chunks: List["TranscriptChunk"] = Relationship(back_populates="source", sa_relationship_kwargs={"cascade": "all, delete"})

class TranscriptChunk(SQLModel, table=True):
    __tablename__ = "transcript_chunks"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    transcript_source_id: uuid.UUID = Field(foreign_key="transcript_sources.id")
    chunk_index: int
    text: str
    embedding: List[float] = Field(sa_column=Column(Vector(768)))
    token_count: Optional[int] = None
    created_at: datetime = Field(default_factory=utc_now)
    source: TranscriptSource = Relationship(back_populates="chunks")
