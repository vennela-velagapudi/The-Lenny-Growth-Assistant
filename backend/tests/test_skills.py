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
            
            with patch("pi_agent.tools.registry.ToolRegistry.run") as mock_run:
                mock_run.return_value = "Ship30 tool successfully executed"
                
                resp = await agent.run("Please write a Ship 30 about growth", [])
                
                from unittest.mock import ANY
                # Check that pi agent ToolRegistry was called deterministically
                mock_run.assert_called_once_with("generate_ship30_artifact", {"topic": "Please write a Ship 30 about growth"}, ANY)
                assert resp.answer == "Ship30 tool successfully executed"
                
    anyio.run(run_test)

def test_agent_uses_pi_agent_for_artifact(mock_db_session):
    async def run_test():
        with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
            agent = LennyAgent(mock_db_session)
            
            with patch("pi_agent.tools.registry.ToolRegistry.run") as mock_run:
                mock_run.return_value = "HTML artifact executed"
                
                resp = await agent.run("Please generate a landing page artifact", [])
                
                from unittest.mock import ANY
                mock_run.assert_called_once_with("generate_custom_artifact", {"topic": "Please generate a landing page artifact", "artifact_type": "html"}, ANY)
                
    anyio.run(run_test)

def test_ship30_source_loaded(mock_db_session):
    with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
        skill = Ship30Skill(mock_db_session, MagicMock(), MagicMock())
        assert "Digital Writer Mindset" in skill.ship30_framework_content
        assert "4A Paths" in skill.ship30_framework_content
