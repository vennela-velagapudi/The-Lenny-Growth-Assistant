import json
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.services.retriever import TranscriptRetriever
from sqlmodel import Session
from pydantic import BaseModel
import structlog

# Pi Coding Agent SDK imports
from pi_agent.agent import Agent, AgentConfig
from pi_agent.tools.registry import ToolRegistry
from pi_agent.tools.base import Tool
from pi_agent.sandbox import Sandbox
from pi_agent.llm import AnthropicProvider, OpenAIProvider

logger = structlog.get_logger()

class AgentResponse(BaseModel):
    answer: str
    grounded: bool
    sources: List[Dict[str, Any]]
    artifact: Optional[Dict[str, Any]] = None

class InsufficientEvidenceException(BaseException):
    """
    Inherits from BaseException to bypass ToolRegistry's Exception catching.
    This guarantees a deterministic halt of the LLM tool loop.
    """
    pass

class LennyAgent:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.retriever = TranscriptRetriever(db_session, top_k=5, similarity_threshold=0.5)
        
        self.system_prompt = (
            "You are The Lenny Growth Assistant. Your sole purpose is to answer questions about growth, "
            "product management, and career development using ONLY the provided transcript evidence from Lenny's Podcast. "
            "NEVER invent or fabricate information, quotes, URLs, episode details, or guest statements. "
            "If the provided evidence is insufficient to answer the user's question, you MUST state that "
            "there is insufficient evidence in the transcripts and refrain from answering."
        )
        
        # State used during a single run
        self.current_sources = []
        self.current_grounded = False

    def search_transcripts_handler(self, args: dict[str, Any], sandbox: Sandbox) -> str:
        """Handler for the search_transcripts tool."""
        query = args.get("query", "")
        if not query:
            return "Error: missing query."
            
        result = self.retriever.retrieve(query)
        self.current_grounded = result.has_relevant_context
        
        sources = []
        for r in result.results:
            sources.append({
                "source_id": r.source_id,
                "episode_title": r.episode_title,
                "guest_name": r.guest_name,
                "source_url": r.source_url,
                "transcript_url": r.transcript_url,
                "chunk_index": r.chunk_index,
                "text": r.text,
                "similarity": r.similarity
            })
        self.current_sources = sources
        
        if not self.current_grounded:
            # Deterministically short-circuit the agent loop immediately.
            raise InsufficientEvidenceException()
            
        return json.dumps(sources)

    def _get_provider(self):
        if settings.LLM_PROVIDER.lower() == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY is missing.")
            return AnthropicProvider(model=settings.ANTHROPIC_MODEL, api_key=settings.ANTHROPIC_API_KEY)
        elif settings.LLM_PROVIDER.lower() == "ollama":
            # Pi Agent supports OpenAI protocol, which Ollama fully implements.
            return OpenAIProvider(
                model=settings.OLLAMA_MODEL, 
                api_key="ollama", 
                base_url=f"{settings.OLLAMA_URL}/v1"
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

    async def run(self, user_message: str, conversation_history: List[Dict[str, str]] = None) -> AgentResponse:
        """Runs the agent loop with deterministic intent routing feeding into the Pi Agent."""
        import re
        if not conversation_history:
            conversation_history = []
            
        provider = self._get_provider()
        
        # State used during a single run
        self.current_sources = []
        self.current_grounded = False
        self.current_artifact = None
        self.history_context = conversation_history

        def set_artifact(artifact: dict, sources: list):
            self.current_artifact = artifact
            self.current_sources = sources
            self.current_grounded = True

        def get_history():
            return self.history_context
            
        from app.skills.ship30 import Ship30Skill
        from app.skills.artifact import ArtifactSkill
        
        ship30_skill = Ship30Skill(self.db, provider, set_artifact)
        artifact_skill = ArtifactSkill(self.db, provider, set_artifact, get_history)

        # Lightweight Deterministic Routing mapping to Tools
        is_ship30 = re.search(r'(?i)\bship\s?30\b', user_message)
        is_artifact = re.search(r'(?i)\b(landing page|product brief|html|markdown|generate an? artifact)\b', user_message)
        
        if is_ship30:
            logger.info("routing_to_ship30_tool")
            user_message += "\n\n[SYSTEM DIRECTIVE: The user wants a Ship 30 essay. You MUST use the `generate_ship30_artifact` tool to fulfill this request. Call the tool and summarize the success.]"
        elif is_artifact:
            logger.info("routing_to_artifact_tool")
            user_message += "\n\n[SYSTEM DIRECTIVE: The user wants a custom artifact. You MUST use the `generate_custom_artifact` tool to fulfill this request. Call the tool and summarize the success.]"

        search_tool = Tool(
            name="search_transcripts",
            description="Searches the transcript knowledge base for relevant chunks. Use this to find evidence before answering.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant podcast discussions."
                    }
                },
                "required": ["query"]
            },
            handler=self.search_transcripts_handler
        )
        
        registry = ToolRegistry([
            search_tool,
            ship30_skill.get_tool(),
            artifact_skill.get_tool()
        ])
        
        sandbox = Sandbox(root=".")
        
        config = AgentConfig(
            system_prompt=self.system_prompt,
            stream=False,
            enable_shell=False,
            auto_approve=True,
            max_iterations=5
        )
        
        pi_messages = []
        for msg in conversation_history:
            pi_messages.append({"role": msg["role"], "content": msg["content"]})
            
        agent = Agent(
            provider=provider,
            registry=registry,
            sandbox=sandbox,
            config=config,
            messages=pi_messages
        )

        logger.info("calling_agent_loop", provider=settings.LLM_PROVIDER)
        
        try:
            final_answer = agent.run(user_message)
            return AgentResponse(
                answer=final_answer,
                grounded=self.current_grounded,
                sources=self.current_sources,
                artifact=self.current_artifact
            )
            
        except InsufficientEvidenceException:
            logger.info("insufficient_evidence_triggered")
            return AgentResponse(
                answer="I couldn't find sufficient evidence in the available Lenny transcript knowledge base to answer that confidently.",
                grounded=False,
                sources=self.current_sources,
                artifact=None
            )
        except Exception as e:
            logger.error("agent_loop_error", error=str(e))
            raise
