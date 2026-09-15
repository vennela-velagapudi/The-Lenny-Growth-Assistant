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
            
            # Mock the OpenAIProvider.complete to simulate the LLM choosing to use the tool
            from pi_agent.llm import AssistantResponse, ToolCall
            
            def mock_complete(*args, **kwargs):
                return AssistantResponse(
                    text="",
                    tool_calls=[ToolCall(id="test_call", name="search_transcripts", args={"query": "test"})]
                )
            
            with patch("pi_agent.llm.OpenAIProvider.complete", side_effect=mock_complete):
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
            
            from pi_agent.llm import AssistantResponse, ToolCall
            
            # 1. LLM requests tool
            # 2. Tool handler runs, stores sources, returns JSON
            # 3. LLM returns final string text
            
            call_count = [0]
            def mock_complete(*args, **kwargs):
                if call_count[0] == 0:
                    call_count[0] += 1
                    return AssistantResponse(
                        text="",
                        tool_calls=[ToolCall(id="test_call", name="search_transcripts", args={"query": "test"})]
                    )
                else:
                    return AssistantResponse(text="Final answer based on transcripts", tool_calls=[])
                    
            with patch("pi_agent.llm.OpenAIProvider.complete", side_effect=mock_complete):
                resp = await agent.run("tell me about X", [])
                
                assert resp.grounded is True
                assert resp.answer == "Final answer based on transcripts"
                
                assert len(resp.sources) == 1
                assert resp.sources[0]["episode_title"] == "Ep 1"
                assert resp.sources[0]["guest_name"] == "Guest"
                assert resp.sources[0]["source_url"] == "http://example.com"
                assert resp.sources[0]["transcript_url"] == "http://example.com/t"
                assert resp.sources[0]["chunk_index"] == 0
                assert resp.sources[0]["similarity"] == 0.9
                
    anyio.run(run_test)
