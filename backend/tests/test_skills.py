import pytest
from unittest.mock import MagicMock, patch
from app.services.agent import LennyAgent, InsufficientEvidenceException
from app.skills.ship30 import Ship30Skill
from app.skills.artifact import ArtifactSkill
from sqlmodel import Session
import anyio

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

def test_ship30_tool_registration(mock_db_session):
    with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
        skill = Ship30Skill(mock_db_session, MagicMock(), MagicMock())
        tool = skill.get_tool()
        
        assert tool.name == "generate_ship30_artifact"
        assert "topic" in tool.input_schema["properties"]

def test_artifact_tool_registration(mock_db_session):
    with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
        skill = ArtifactSkill(mock_db_session, MagicMock(), MagicMock(), MagicMock())
        tool = skill.get_tool()
        
        assert tool.name == "generate_custom_artifact"
        assert "artifact_type" in tool.input_schema["properties"]

def test_ship30_insufficient_evidence(mock_db_session):
    with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
        skill = Ship30Skill(mock_db_session, MagicMock(), MagicMock())
        
        mock_result = MagicMock()
        mock_result.has_relevant_context = False
        skill.retriever.retrieve = MagicMock(return_value=mock_result)
        
        with pytest.raises(InsufficientEvidenceException):
            skill.handler({"topic": "aliens"}, MagicMock())

def test_artifact_insufficient_evidence(mock_db_session):
    with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
        skill = ArtifactSkill(mock_db_session, MagicMock(), MagicMock(), MagicMock(return_value=[]))
        
        mock_result = MagicMock()
        mock_result.has_relevant_context = False
        skill.retriever.retrieve = MagicMock(return_value=mock_result)
        
        with pytest.raises(InsufficientEvidenceException):
            skill.handler({"topic": "ghosts", "artifact_type": "markdown"}, MagicMock())

def test_agent_uses_pi_agent_for_ship30(mock_db_session):
    async def run_test():
        with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
            agent = LennyAgent(mock_db_session)
            
            with patch("pi_agent.agent.Agent.run") as mock_pi_run:
                mock_pi_run.return_value = "Ship30 piece"
                
                resp = await agent.run("Please write a Ship 30 about growth", [])
                
                # Check that pi agent run was called with the directive
                mock_pi_run.assert_called_once()
                call_arg = mock_pi_run.call_args[0][0]
                assert "SYSTEM DIRECTIVE" in call_arg
                assert "generate_ship30_artifact" in call_arg
                
    anyio.run(run_test)
