import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.agent import LennyAgent, AgentResponse
from app.core.config import settings
from sqlmodel import Session
import json
import anyio

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_retriever():
    retriever = MagicMock()
    return retriever

def test_ollama_provider_selection(mock_db_session):
    async def run_test():
        with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
            agent = LennyAgent(mock_db_session)
            # Mock _run_ollama
            agent._run_ollama = AsyncMock(return_value=AgentResponse(answer="ollama response", grounded=True, sources=[]))
            
            resp = await agent.run("test", [])
            assert resp.answer == "ollama response"
            agent._run_ollama.assert_called_once()
    anyio.run(run_test)

def test_anthropic_provider_selection(mock_db_session):
    async def run_test():
        with patch("app.core.config.settings.LLM_PROVIDER", "anthropic"):
            agent = LennyAgent(mock_db_session)
            agent._run_anthropic = AsyncMock(return_value=AgentResponse(answer="anthropic response", grounded=True, sources=[]))
            
            resp = await agent.run("test", [])
            assert resp.answer == "anthropic response"
            agent._run_anthropic.assert_called_once()
    anyio.run(run_test)

def test_anthropic_missing_key(mock_db_session):
    async def run_test():
        with patch("app.core.config.settings.LLM_PROVIDER", "anthropic"):
            with patch("app.core.config.settings.ANTHROPIC_API_KEY", ""):
                agent = LennyAgent(mock_db_session)
                with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is missing"):
                    await agent.run("test", [])
    anyio.run(run_test)

def test_agent_insufficient_evidence_deterministic(mock_db_session):
    async def run_test():
        agent = LennyAgent(mock_db_session)
        # If the tool is executed and returns has_relevant_context=False, it should return deterministic fallback
        mock_tool_result = {
            "has_relevant_context": False,
            "sources": []
        }
        
        with patch.object(agent, 'execute_tool', new_callable=AsyncMock) as mock_exec_tool:
            mock_exec_tool.return_value = mock_tool_result
            # We mock anthropic call to simulate returning a tool use
            with patch("app.core.config.settings.LLM_PROVIDER", "anthropic"):
                with patch("app.core.config.settings.ANTHROPIC_API_KEY", "dummy"):
                    # Mock the anthropic client
                    mock_client = MagicMock()
                    mock_messages_create = AsyncMock()
                    
                    # Setup the first response to use the tool
                    class MockContent:
                        def __init__(self, type, name, input, id):
                            self.type = type
                            self.name = name
                            self.input = input
                            self.id = id
                            
                    class MockResponse:
                        def __init__(self):
                            self.stop_reason = "tool_use"
                            self.content = [MockContent("tool_use", "search_transcripts", {"query": "test"}, "call_1")]
                            
                    mock_messages_create.return_value = MockResponse()
                    mock_client.messages.create = mock_messages_create
                    
                    with patch("app.services.agent.AsyncAnthropic", return_value=mock_client):
                        resp = await agent.run("tell me about X", [])
                        assert resp.grounded is False
                        assert "sufficient evidence" in resp.answer.lower()
                        # The tool was called, but the second LLM call was skipped deterministically
                        assert mock_messages_create.call_count == 1
    anyio.run(run_test)
