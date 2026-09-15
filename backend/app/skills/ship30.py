import json
import os
from typing import List, Dict, Any, Callable
from sqlmodel import Session
from app.services.retriever import TranscriptRetriever
from pi_agent.tools.base import Tool
from pi_agent.sandbox import Sandbox
from pi_agent.llm import LLMProvider
from app.services.agent import InsufficientEvidenceException

class Ship30Skill:
    def __init__(self, db_session: Session, provider: LLMProvider, set_artifact_callback: Callable):
        self.db = db_session
        self.provider = provider
        self.set_artifact_callback = set_artifact_callback
        self.retriever = TranscriptRetriever(db_session, top_k=8, similarity_threshold=0.5)
        
        # Load verified Ship30 principles
        source_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "ship30", "ship30_ultimate_guide.md")
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                self.ship30_framework_content = f.read()
        except FileNotFoundError:
            self.ship30_framework_content = "Ship 30 Framework principles could not be loaded."

    def get_tool(self) -> Tool:
        return Tool(
            name="generate_ship30_artifact",
            description="Generates a ~1250 word Ship 30 for 30 essay based on transcript evidence for a given topic.",
            input_schema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The specific topic to write the Ship 30 essay about."
                    }
                },
                "required": ["topic"]
            },
            handler=self.handler
        )

    def handler(self, args: dict[str, Any], sandbox: Sandbox) -> str:
        topic = args.get("topic", "")
        if not topic:
            return "Error: missing topic."

        # 1. Retrieve explicitly
        result = self.retriever.retrieve(topic)
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

        # 2. Generate artifact directly inside the tool
        system_prompt = (
            "You are a Ship 30 for 30 writing expert. Your task is to write a highly engaging, ~1250-word piece "
            "based STRICTLY on the provided transcript evidence from Lenny's Podcast for facts, while using the "
            "provided Ship 30 for 30 framework for structural and stylistic guidance.\n\n"
            "--- SHIP 30 FOR 30 FRAMEWORK GUIDANCE ---\n"
            f"{self.ship30_framework_content}\n\n"
            "--- INSTRUCTIONS ---\n"
            "Format the piece in Markdown with the following structure:\n"
            "- A strong, curiosity-inducing hook/narrative opening\n"
            "- Core idea (explain the principle)\n"
            "- Why it matters (grounded explanation)\n"
            "- What the source teaches (specific evidence from Lenny transcripts)\n"
            "- Practical takeaway (actionable advice)\n"
            "- Memorable closing\n\n"
            "CRITICAL: Do NOT claim that a writing principle came from a Lenny podcast guest if it actually came from the Ship 30 framework. "
            "Likewise, do NOT fabricate facts or quotes. Only output the Markdown content."
        )

        from pi_agent.messages import NeutralMessage
        messages = [NeutralMessage(role="user", content=f"User Request: {topic}\n\nLenny Transcript Evidence:\n{context_text}")]
        
        assistant_response = self.provider.complete(system=system_prompt, messages=messages)
        final_answer = assistant_response.content
        
        # Add Ship 30 as a distinct source for the frontend citations
        sources.insert(0, {
            "source_id": "ship30-ultimate-guide",
            "episode_title": "Ship 30 for 30 Ultimate Guide",
            "guest_name": "Dickie Bush & Nicolas Cole",
            "source_url": "https://www.ship30for30.com/post/how-to-start-writing-online-the-ship-30-for-30-ultimate-guide",
            "transcript_url": None,
            "chunk_index": 0,
            "text": "Official Ship 30 writing framework and principles.",
            "similarity": 1.0
        })

        # 3. Store artifact and sources in the agent's state
        self.set_artifact_callback(
            artifact={
                "type": "markdown",
                "title": f"Ship 30 for 30: {topic[:30]}",
                "content": final_answer
            },
            sources=sources
        )

        return f"Ship 30 artifact successfully generated based on {len(sources)-1} transcript chunks and the Ship 30 framework. The user can view it in the Artifact Viewer."
