import json
from typing import List, Dict, Any, Callable
from sqlmodel import Session
from app.services.retriever import TranscriptRetriever
from pi_agent.tools.base import Tool
from pi_agent.sandbox import Sandbox
from pi_agent.llm import LLMProvider
from app.services.agent import InsufficientEvidenceException

class ArtifactSkill:
    def __init__(self, db_session: Session, provider: LLMProvider, set_artifact_callback: Callable, get_history_callback: Callable):
        self.db = db_session
        self.provider = provider
        self.set_artifact_callback = set_artifact_callback
        self.get_history_callback = get_history_callback
        self.retriever = TranscriptRetriever(db_session, top_k=5, similarity_threshold=0.5)

    def get_tool(self) -> Tool:
        return Tool(
            name="generate_custom_artifact",
            description="Generates a Markdown or HTML artifact based on transcript evidence for a given topic.",
            input_schema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The specific topic to generate an artifact about."
                    },
                    "artifact_type": {
                        "type": "string",
                        "enum": ["markdown", "html"],
                        "description": "The format of the artifact."
                    }
                },
                "required": ["topic", "artifact_type"]
            },
            handler=self.handler
        )

    def handler(self, args: dict[str, Any], sandbox: Sandbox) -> str:
        topic = args.get("topic", "")
        artifact_type = args.get("artifact_type", "markdown")
        if not topic:
            return "Error: missing topic."

        # Fetch recent history
        history = self.get_history_callback()
        
        search_query = topic
        if history:
            search_query = f"{history[-1].get('content', '')} {topic}"

        # 1. Retrieve explicitly
        result = self.retriever.retrieve(search_query)
        if not result.has_relevant_context:
            raise InsufficientEvidenceException()

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

        history_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in history[-3:]])
        user_prompt = f"Recent History:\n{history_text}\n\nUser Request: {topic}\n\nEvidence:\n{context_text}"

        from pi_agent.messages import NeutralMessage
        messages = [NeutralMessage(role="user", content=user_prompt)]
        
        assistant_response = self.provider.complete(system=system_prompt, messages=messages)
        final_answer = assistant_response.content

        # Clean up markdown codeblocks if it's HTML
        if artifact_type == "html":
            if final_answer.startswith("```html"):
                final_answer = final_answer[7:]
            if final_answer.startswith("```"):
                final_answer = final_answer[3:]
            if final_answer.endswith("```"):
                final_answer = final_answer[:-3]
            final_answer = final_answer.strip()

        # 3. Store artifact and sources in the agent's state
        self.set_artifact_callback(
            artifact={
                "type": artifact_type,
                "title": f"{artifact_type.upper()} Artifact: {topic[:20]}",
                "content": final_answer
            },
            sources=sources
        )

        return f"{artifact_type} artifact successfully generated based on {len(sources)} transcript chunks. The user can view it in the Artifact Viewer."
