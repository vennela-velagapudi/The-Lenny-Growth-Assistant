import json
from typing import List, Dict, Any
from sqlmodel import Session
from app.services.retriever import TranscriptRetriever
from pi_agent.agent import Agent, AgentConfig
from pi_agent.llm import LLMProvider
from app.services.agent import InsufficientEvidenceException

class Ship30Skill:
    def __init__(self, db_session: Session, provider: LLMProvider):
        self.db = db_session
        self.provider = provider
        self.retriever = TranscriptRetriever(db_session, top_k=8, similarity_threshold=0.5)

    async def execute(self, query: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Executes the Ship 30 for 30 skill deterministically.
        1. Retrieves transcripts based on the query.
        2. If weak/no evidence, deterministically returns ungrounded error.
        3. Invokes an agent/LLM explicitly prompted to write a Ship 30 format artifact.
        """
        if not history:
            history = []

        # 1. Retrieve explicitly
        # We use a broad retrieval step combining history context and the specific query
        search_query = query
        if history:
            search_query = f"{history[-1]['content']} {query}"
            
        result = self.retriever.retrieve(search_query)
        if not result.has_relevant_context:
            return {
                "answer": "I couldn't find sufficient evidence in the available Lenny transcript knowledge base to answer that confidently.",
                "grounded": False,
                "sources": [],
                "artifact": None
            }

        sources = []
        context_text = ""
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
            context_text += f"\n\nSource: {r.episode_title} (Guest: {r.guest_name})\nText: {r.text}"

        # 2. Invoke LLM for Ship30 generation
        system_prompt = (
            "You are a Ship 30 for 30 writing expert. Your task is to write a highly engaging, ~1250-word piece "
            "based strictly on the provided transcript evidence from Lenny's Podcast. "
            "Do not invent facts, quotes, or principles not found in the evidence.\n\n"
            "Format the piece in Markdown with the following structure:\n"
            "- A strong, curiosity-inducing hook/narrative opening\n"
            "- Core idea (explain the principle)\n"
            "- Why it matters (grounded explanation)\n"
            "- What the source teaches (specific evidence)\n"
            "- Practical takeaway (actionable advice)\n"
            "- Memorable closing\n\n"
            "Only output the Markdown content, nothing else."
        )

        user_prompt = f"User Request: {query}\n\nEvidence:\n{context_text}"

        config = AgentConfig(system_prompt=system_prompt, stream=False)
        agent = Agent(provider=self.provider, config=config)

        # Ship30 doesn't need to recursively tool-call here because we already pre-fetched context. 
        # But we use the Pi Agent for consistency.
        final_answer = agent.run(user_prompt)

        return {
            "answer": "I have generated the Ship 30 for 30 piece you requested. You can view it in the Artifact Viewer.",
            "grounded": True,
            "sources": sources,
            "artifact": {
                "type": "markdown",
                "title": "Ship 30 for 30: " + query[:30] + "...",
                "content": final_answer
            }
        }
