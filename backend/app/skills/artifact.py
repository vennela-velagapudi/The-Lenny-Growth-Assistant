import json
from typing import List, Dict, Any
from sqlmodel import Session
from app.services.retriever import TranscriptRetriever
from pi_agent.agent import Agent, AgentConfig
from pi_agent.llm import LLMProvider

class ArtifactSkill:
    def __init__(self, db_session: Session, provider: LLMProvider):
        self.db = db_session
        self.provider = provider
        self.retriever = TranscriptRetriever(db_session, top_k=5, similarity_threshold=0.5)

    async def execute(self, query: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Executes general artifact generation (Markdown or HTML).
        """
        if not history:
            history = []

        # Determine type (HTML vs Markdown)
        artifact_type = "markdown"
        if "html" in query.lower() or "landing page" in query.lower() or "css" in query.lower():
            artifact_type = "html"

        # 1. Retrieve explicitly
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

        system_prompt = (
            f"You are a specialized generation assistant. The user wants an artifact of type '{artifact_type}'.\n"
            "If HTML, output ONLY raw HTML/CSS (no markdown blocks around it, no explanations). Include styling within <style> tags.\n"
            "If Markdown, output standard markdown.\n"
            "Base your content STRICTLY on the provided evidence. Do not invent facts."
        )

        # Include chat history context
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-3:]])
        user_prompt = f"Recent History:\n{history_text}\n\nUser Request: {query}\n\nEvidence:\n{context_text}"

        config = AgentConfig(system_prompt=system_prompt, stream=False)
        agent = Agent(provider=self.provider, config=config)

        final_answer = agent.run(user_prompt)

        # Clean up markdown codeblocks if it's HTML
        if artifact_type == "html":
            if final_answer.startswith("```html"):
                final_answer = final_answer[7:]
            if final_answer.startswith("```"):
                final_answer = final_answer[3:]
            if final_answer.endswith("```"):
                final_answer = final_answer[:-3]
            final_answer = final_answer.strip()

        return {
            "answer": f"I have generated the {artifact_type} artifact you requested. You can view it in the Artifact Viewer.",
            "grounded": True,
            "sources": sources,
            "artifact": {
                "type": artifact_type,
                "title": "Generated Artifact",
                "content": final_answer
            }
        }
