from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional, Any
from uuid import UUID
from app.db.database import get_session
from app.db.models import User, Session as ChatSession, Message
from app.services.agent import LennyAgent
import json
from pydantic import BaseModel

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Request/Response Models
class SessionCreate(BaseModel):
    title: Optional[str] = "New Conversation"

class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

class MessageRequest(BaseModel):
    content: str

class SourceResponse(BaseModel):
    source_id: str
    episode_title: str
    guest_name: Optional[str]
    source_url: Optional[str]
    transcript_url: Optional[str]
    chunk_index: int
    text: str
    similarity: float

class ArtifactResponse(BaseModel):
    id: UUID
    type: str
    title: str
    content: str

class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    grounded: Optional[bool] = None
    sources: Optional[List[SourceResponse]] = None
    artifact: Optional[ArtifactResponse] = None
    created_at: str

    class Config:
        from_attributes = True

@router.post("", response_model=SessionResponse)
def create_session(request: SessionCreate, db: Session = Depends(get_session)):
    user = User(metadata_json="{}")
    db.add(user)
    db.commit()
    db.refresh(user)
    
    session = ChatSession(user_id=user.id, title=request.title)
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
        "created_at": session.created_at.isoformat()
    }

@router.get("/{session_id}", response_model=SessionResponse)
def get_session_by_id(session_id: UUID, db: Session = Depends(get_session)):
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
        "created_at": session.created_at.isoformat()
    }

@router.post("/{session_id}/messages", response_model=MessageResponse)
async def send_message(session_id: UUID, request: MessageRequest, db: Session = Depends(get_session)):
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty")
        
    chat_session = db.get(ChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    user_msg = Message(session_id=session_id, role="user", content=request.content)
    db.add(user_msg)
    db.commit()
    
    history = db.exec(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    ).all()
    
    formatted_history = []
    for msg in history[:-1]:
        content_text = msg.content
        if msg.role == "assistant":
            try:
                parsed = json.loads(msg.content)
                content_text = parsed.get("answer", msg.content)
            except json.JSONDecodeError:
                pass
        formatted_history.append({"role": msg.role, "content": content_text})

    agent = LennyAgent(db)
    try:
        response = await agent.run(request.content, formatted_history)
    except Exception as e:
        raise HTTPException(status_code=503, detail={
            "code": "LLM_UNAVAILABLE",
            "message": str(e)
        })
        
    # Handle generated artifact
    artifact_data = None
    if response.artifact:
        from app.db.models import Artifact
        db_artifact = Artifact(
            session_id=session_id,
            artifact_type=response.artifact.get("type", "markdown"),
            title=response.artifact.get("title", "Generated Artifact"),
            content=response.artifact.get("content", "")
        )
        db.add(db_artifact)
        db.commit()
        db.refresh(db_artifact)
        
        artifact_data = {
            "id": db_artifact.id,
            "type": db_artifact.artifact_type,
            "title": db_artifact.title,
            "content": db_artifact.content
        }

    content_json = json.dumps({
        "answer": response.answer,
        "grounded": response.grounded,
        "sources": response.sources,
        "artifact": {"id": str(artifact_data["id"]), "type": artifact_data["type"], "title": artifact_data["title"], "content": artifact_data["content"]} if artifact_data else None
    })
    
    assistant_msg = Message(session_id=session_id, role="assistant", content=content_json)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    
    return {
        "id": assistant_msg.id,
        "role": assistant_msg.role,
        "content": response.answer,
        "grounded": response.grounded,
        "sources": response.sources,
        "artifact": artifact_data,
        "created_at": assistant_msg.created_at.isoformat()
    }

@router.get("/{session_id}/messages", response_model=List[MessageResponse])
def get_messages(session_id: UUID, db: Session = Depends(get_session)):
    chat_session = db.get(ChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    history = db.exec(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    ).all()
    
    responses = []
    for msg in history:
        if msg.role == "assistant":
            try:
                parsed = json.loads(msg.content)
                responses.append({
                    "id": msg.id,
                    "role": msg.role,
                    "content": parsed.get("answer", ""),
                    "grounded": parsed.get("grounded", False),
                    "sources": parsed.get("sources", []),
                    "artifact": parsed.get("artifact", None),
                    "created_at": msg.created_at.isoformat()
                })
            except json.JSONDecodeError:
                responses.append({
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat()
                })
        else:
            responses.append({
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat()
            })
            
    return responses

@router.get("/{session_id}/artifacts")
def get_artifacts(session_id: UUID, db: Session = Depends(get_session)):
    chat_session = db.get(ChatSession, session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    from app.db.models import Artifact
    artifacts = db.exec(
        select(Artifact).where(Artifact.session_id == session_id).order_by(Artifact.created_at)
    ).all()
    
    return [
        {
            "id": a.id,
            "type": a.artifact_type,
            "title": a.title,
            "content": a.content,
            "created_at": a.created_at.isoformat(),
            "updated_at": a.updated_at.isoformat()
        } for a in artifacts
    ]

