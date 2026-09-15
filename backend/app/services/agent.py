import json
from typing import List, Dict, Any, Optional
from anthropic import AsyncAnthropic
from app.core.config import settings
from app.services.retriever import TranscriptRetriever
from sqlmodel import Session
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

class AgentResponse(BaseModel):
    answer: str
    grounded: bool
    sources: List[Dict[str, Any]]

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

        self.retrieval_tool = {
            "name": "search_transcripts",
            "description": "Searches the transcript knowledge base for relevant chunks. Use this to find evidence before answering.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant podcast discussions."
                    }
                },
                "required": ["query"]
            }
        }

    async def execute_tool(self, query: str) -> Dict[str, Any]:
        """Executes the retriever and formats the results for the LLM."""
        result = self.retriever.retrieve(query)
        
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
            
        return {
            "has_relevant_context": result.has_relevant_context,
            "sources": sources
        }

    async def run(self, user_message: str, conversation_history: List[Dict[str, str]] = None) -> AgentResponse:
        """Runs the agent loop with the configured provider."""
        if not conversation_history:
            conversation_history = []

        if settings.LLM_PROVIDER.lower() == "anthropic":
            return await self._run_anthropic(user_message, conversation_history)
        elif settings.LLM_PROVIDER.lower() == "ollama":
            return await self._run_ollama(user_message, conversation_history)
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

    async def _run_anthropic(self, user_message: str, conversation_history: List[Dict[str, str]]) -> AgentResponse:
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is missing.")
            
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        messages = conversation_history.copy()
        messages.append({"role": "user", "content": user_message})

        logger.info("calling_anthropic_agent")
        
        try:
            # Step 1: Initial LLM call
            response = await client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=1024,
                system=self.system_prompt,
                messages=messages,
                tools=[self.retrieval_tool]
            )
            
            # Step 2: Handle tool calls
            final_answer = ""
            grounded = False
            used_sources = []
            
            if response.stop_reason == "tool_use":
                # Extract tool call
                tool_call = next((c for c in response.content if c.type == "tool_use"), None)
                if tool_call and tool_call.name == "search_transcripts":
                    query = tool_call.input.get("query", "")
                    
                    # Execute deterministic tool
                    tool_result = await self.execute_tool(query)
                    
                    # Track context observability
                    grounded = tool_result["has_relevant_context"]
                    used_sources = tool_result["sources"]
                    
                    # If not grounded, intercept deterministically (Application-level boundary)
                    if not grounded:
                        final_answer = "I could not find sufficient evidence in the transcripts to answer your question."
                        return AgentResponse(answer=final_answer, grounded=False, sources=[])

                    # Step 3: Append tool result and get final response
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_call.id,
                                "content": json.dumps(tool_result["sources"])
                            }
                        ]
                    })
                    
                    final_response = await client.messages.create(
                        model=settings.ANTHROPIC_MODEL,
                        max_tokens=1024,
                        system=self.system_prompt,
                        messages=messages
                    )
                    final_answer = final_response.content[0].text
            else:
                # Agent decided not to use tools (e.g. conversational greeting)
                final_answer = next((c.text for c in response.content if c.type == "text"), "")
                grounded = False # Not grounded if no search was performed
                
            return AgentResponse(
                answer=final_answer,
                grounded=grounded,
                sources=used_sources
            )
            
        except Exception as e:
            logger.error("anthropic_agent_error", error=str(e))
            raise

    async def _run_ollama(self, user_message: str, conversation_history: List[Dict[str, str]]) -> AgentResponse:
        import httpx
        # We use httpx to call Ollama directly to handle native tool calling structure
        
        messages = conversation_history.copy()
        messages.append({"role": "user", "content": user_message})

        logger.info("calling_ollama_agent")
        
        # Ollama supports a subset of OpenAI-like tool calling format
        ollama_tool = {
            "type": "function",
            "function": {
                "name": "search_transcripts",
                "description": "Searches the transcript knowledge base for relevant chunks.",
                "parameters": self.retrieval_tool["input_schema"]
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.OLLAMA_URL}/api/chat",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "messages": [{"role": "system", "content": self.system_prompt}] + messages,
                        "tools": [ollama_tool],
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                
            message_data = data.get("message", {})
            tool_calls = message_data.get("tool_calls", [])
            
            grounded = False
            used_sources = []
            final_answer = ""
            
            if tool_calls:
                tool_call = tool_calls[0]
                if tool_call["function"]["name"] == "search_transcripts":
                    query = tool_call["function"]["arguments"].get("query", "")
                    
                    # Execute tool
                    tool_result = await self.execute_tool(query)
                    grounded = tool_result["has_relevant_context"]
                    used_sources = tool_result["sources"]
                    
                    if not grounded:
                        final_answer = "I could not find sufficient evidence in the transcripts to answer your question."
                        return AgentResponse(answer=final_answer, grounded=False, sources=[])
                        
                    # Append tool response
                    messages.append(message_data)
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(tool_result["sources"])
                    })
                    
                    # Second call
                    async with httpx.AsyncClient(timeout=120.0) as client2:
                        response2 = await client2.post(
                            f"{settings.OLLAMA_URL}/api/chat",
                            json={
                                "model": settings.OLLAMA_MODEL,
                                "messages": [{"role": "system", "content": self.system_prompt}] + messages,
                                "stream": False
                            }
                        )
                        response2.raise_for_status()
                        data2 = response2.json()
                        final_answer = data2.get("message", {}).get("content", "")
            else:
                final_answer = message_data.get("content", "")
                grounded = False
                
            return AgentResponse(
                answer=final_answer,
                grounded=grounded,
                sources=used_sources
            )
            
        except httpx.HTTPError as e:
            logger.error("ollama_agent_error", error=str(e))
            raise RuntimeError("Ollama provider is unavailable or failed.")
