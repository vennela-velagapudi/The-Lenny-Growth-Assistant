import pytest
from unittest.mock import MagicMock, patch
from app.services.agent import LennyAgent, InsufficientEvidenceException
from pi_agent.llm import AnthropicProvider, OpenAIProvider
from sqlmodel import Session
import anyio

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

def test_ollama_provider_selection(mock_db_session):
    async def run_test():
        with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
            agent = LennyAgent(mock_db_session)
            provider = agent._get_provider()
            assert isinstance(provider, OpenAIProvider)
            assert provider.model == "llama3"
            assert "localhost" in provider.base_url
    anyio.run(run_test)

def test_anthropic_provider_selection(mock_db_session):
    async def run_test():
        with patch("app.core.config.settings.LLM_PROVIDER", "anthropic"):
            with patch("app.core.config.settings.ANTHROPIC_API_KEY", "dummy"):
                agent = LennyAgent(mock_db_session)
                provider = agent._get_provider()
                assert isinstance(provider, AnthropicProvider)
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
        with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
            agent = LennyAgent(mock_db_session)
            
            # Mock the retriever to return has_relevant_context=False
            mock_result = MagicMock()
            mock_result.has_relevant_context = False
            mock_result.results = []
            
            agent.retriever.retrieve = MagicMock(return_value=mock_result)
            
            # Since the provider is mocked, we need to mock the agent loop 
            # to just call our handler directly to simulate LLM tool usage
            with patch("pi_agent.agent.Agent.run") as mock_run:
                # The LLM "calls" the tool which raises the exception
                mock_run.side_effect = InsufficientEvidenceException()
                
                resp = await agent.run("tell me about X", [])
                
                # Check deterministic short circuit
                assert resp.grounded is False
                assert "sufficient evidence" in resp.answer.lower()
                assert len(resp.sources) == 0
                
    anyio.run(run_test)

def test_agent_tool_handler_success(mock_db_session):
    async def run_test():
        with patch("app.core.config.settings.LLM_PROVIDER", "ollama"):
            agent = LennyAgent(mock_db_session)
            
            # Mock the retriever to return has_relevant_context=True
            mock_result = MagicMock()
            mock_result.has_relevant_context = True
            
            mock_source = MagicMock()
            mock_source.source_id = "test-123"
            mock_source.episode_title = "Ep 1"
            mock_source.guest_name = "Guest"
            mock_source.source_url = "http://example.com"
            mock_source.transcript_url = "http://example.com/t"
            mock_source.chunk_index = 0
            mock_source.text = "test text"
            mock_source.similarity = 0.9
            
            mock_result.results = [mock_source]
            agent.retriever.retrieve = MagicMock(return_value=mock_result)
            
            # Verify tool handler behavior directly
            import json
            output = agent.search_transcripts_handler({"query": "test"}, None)
            parsed = json.loads(output)
            
            assert agent.current_grounded is True
            assert len(parsed) == 1
            assert parsed[0]["source_id"] == "test-123"
            
    anyio.run(run_test)
