import pytest
from fastapi.testclient import TestClient
from app.main import app
from sqlmodel import Session, create_engine, SQLModel
from app.db.database import get_session
from sqlalchemy.pool import StaticPool
import uuid

# Setup in-memory sqlite for testing APIs
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

def get_session_override():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = get_session_override

@pytest.fixture(autouse=True)
def setup_db():
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)

client = TestClient(app)

def test_create_session():
    response = client.post("/api/sessions", json={"title": "Test Chat"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "user_id" in data
    assert data["title"] == "Test Chat"

def test_get_session():
    # create first
    create_resp = client.post("/api/sessions", json={})
    session_id = create_resp.json()["id"]
    
    # get
    get_resp = client.get(f"/api/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == session_id

def test_session_isolation():
    s1 = client.post("/api/sessions", json={}).json()["id"]
    s2 = client.post("/api/sessions", json={}).json()["id"]
    
    # Mock the LennyAgent so it doesn't actually call LLM
    from unittest.mock import patch, AsyncMock
    from app.services.agent import AgentResponse
    
    with patch("app.api.sessions.LennyAgent.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = AgentResponse(answer="Mock answer", grounded=True, sources=[])
        
        # Send msg to s1
        client.post(f"/api/sessions/{s1}/messages", json={"content": "Msg 1"})
        
        # Send msg to s2
        client.post(f"/api/sessions/{s2}/messages", json={"content": "Msg 2"})
        
        # Check messages for s1
        m1 = client.get(f"/api/sessions/{s1}/messages").json()
        assert len(m1) == 2 # 1 user, 1 assistant
        assert m1[0]["content"] == "Msg 1"
        
        # Check messages for s2
        m2 = client.get(f"/api/sessions/{s2}/messages").json()
        assert len(m2) == 2
        assert m2[0]["content"] == "Msg 2"

def test_empty_message():
    s1 = client.post("/api/sessions", json={}).json()["id"]
    resp = client.post(f"/api/sessions/{s1}/messages", json={"content": "   "})
    assert resp.status_code == 400
    assert "cannot be empty" in resp.json()["detail"]
