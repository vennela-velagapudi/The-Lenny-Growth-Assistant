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

class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    grounded: Optional[bool] = None
    sources: Optional[List[SourceResponse]] = None
    created_at: str

    class Config:
        from_attributes = True

@router.post("", response_model=SessionResponse)
def create_session(request: SessionCreate, db: Session = Depends(get_session)):
    # Create an anonymous user for now (since no auth is required in this phase)
    # Ideally, we would track this via session cookie, but creating a generic user works for the API.
    # We will just create a new user per session to fulfill the User/Session relationship easily,
    # or find a default "anonymous" user. Let's just create a new user.
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
        
    # Store user message
    user_msg = Message(session_id=session_id, role="user", content=request.content)
    db.add(user_msg)
    db.commit()
    
    # Retrieve conversation history (only simple text messages)
    history = db.exec(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    ).all()
    
    formatted_history = []
    # Exclude the current message we just added
    for msg in history[:-1]:
        # Strip metadata from assistant content if we stored it as JSON
        # For simplicity, we just pass the raw text to LLM
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
        # Structured error
        raise HTTPException(status_code=503, detail={
            "code": "LLM_UNAVAILABLE",
            "message": str(e)
        })
        
    # Store assistant message
    # We store the structured response as JSON in the content field so we can parse it easily
    content_json = json.dumps({
        "answer": response.answer,
        "grounded": response.grounded,
        "sources": response.sources
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
