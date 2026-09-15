from typing import Optional, List
from sqlmodel import Field, SQLModel
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
import uuid

class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    metadata_json: Optional[str] = Field(default="{}")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Session(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    title: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
class Message(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="session.id")
    role: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
class Artifact(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    message_id: uuid.UUID = Field(foreign_key="message.id")
    artifact_type: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TranscriptChunk(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_id: str
    episode_title: str
    guest_name: Optional[str] = None
    source_url: Optional[str] = None
    transcript_url: Optional[str] = None
    chunk_index: int
    text: str
    embedding: List[float] = Field(sa_column=Column(Vector(768)))
    ingestion_timestamp: datetime = Field(default_factory=datetime.utcnow)
    content_hash: str
