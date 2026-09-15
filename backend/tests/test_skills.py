import pytest
from unittest.mock import MagicMock, patch
from app.services.agent import LennyAgent
from app.skills.ship30 import Ship30Skill
from app.skills.artifact import ArtifactSkill
from sqlmodel import Session
import anyio

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

def test_intent_routing_ship30(mock_db_session):
    async def run_test():
        with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
            agent = LennyAgent(mock_db_session)
            
            with patch.object(Ship30Skill, "execute", new_callable=MagicMock) as mock_execute:
                # Async mock
                async def fake_execute(*args, **kwargs):
                    return {
                        "answer": "Ship30 piece",
                        "grounded": True,
                        "sources": [],
                        "artifact": {"type": "markdown", "title": "Ship30", "content": "..."}
                    }
                mock_execute.side_effect = fake_execute
                
                resp = await agent.run("Please write a Ship 30 about growth", [])
                
                assert resp.artifact is not None
                assert resp.artifact["type"] == "markdown"
                mock_execute.assert_called_once()
                
    anyio.run(run_test)

def test_intent_routing_artifact(mock_db_session):
    async def run_test():
        with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
            agent = LennyAgent(mock_db_session)
            
            with patch.object(ArtifactSkill, "execute", new_callable=MagicMock) as mock_execute:
                async def fake_execute(*args, **kwargs):
                    return {
                        "answer": "HTML page",
                        "grounded": True,
                        "sources": [],
                        "artifact": {"type": "html", "title": "Landing Page", "content": "<h1>Hi</h1>"}
                    }
                mock_execute.side_effect = fake_execute
                
                resp = await agent.run("Create a landing page", [])
                
                assert resp.artifact is not None
                assert resp.artifact["type"] == "html"
                mock_execute.assert_called_once()
                
    anyio.run(run_test)

def test_ship30_insufficient_evidence(mock_db_session):
    async def run_test():
        with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
            skill = Ship30Skill(mock_db_session, MagicMock())
            
            mock_result = MagicMock()
            mock_result.has_relevant_context = False
            skill.retriever.retrieve = MagicMock(return_value=mock_result)
            
            resp = await skill.execute("Write Ship 30 about aliens")
            
            assert resp["grounded"] is False
            assert "sufficient evidence" in resp["answer"]
            assert resp["artifact"] is None
            
    anyio.run(run_test)

def test_artifact_insufficient_evidence(mock_db_session):
    async def run_test():
        with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
            skill = ArtifactSkill(mock_db_session, MagicMock())
            
            mock_result = MagicMock()
            mock_result.has_relevant_context = False
            skill.retriever.retrieve = MagicMock(return_value=mock_result)
            
            resp = await skill.execute("Create HTML about ghosts")
            
            assert resp["grounded"] is False
            assert "sufficient evidence" in resp["answer"]
            assert resp["artifact"] is None
            
    anyio.run(run_test)
