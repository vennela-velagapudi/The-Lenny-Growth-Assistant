import json
from typing import List, Dict, Any, Callable
from sqlmodel import Session
from app.services.retriever import TranscriptRetriever
from pi_agent.tools.base import Tool
from pi_agent.sandbox import Sandbox
from pi_agent.llm import LLMProvider
from app.services.agent import InsufficientEvidenceException

# We document the inability to locate the exact Ship30 source as required by the audit
SHIP30_SOURCE_NOTE = (
    "Note: The exact Ship 30 for 30 framework principles source document was not provided in the assignment repository. "
    "Therefore, this essay strictly utilizes Lenny's podcast transcript evidence and follows a general Ship 30 formatting "
    "structure. It does not cite or claim principles from the official Ship 30 framework."
)

class Ship30Skill:
    def __init__(self, db_session: Session, provider: LLMProvider, set_artifact_callback: Callable):
        self.db = db_session
        self.provider = provider
        self.set_artifact_callback = set_artifact_callback
        self.retriever = TranscriptRetriever(db_session, top_k=8, similarity_threshold=0.5)

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
            "based STRICTLY on the provided transcript evidence from Lenny's Podcast.\n"
            f"{SHIP30_SOURCE_NOTE}\n\n"
            "Format the piece in Markdown with the following structure:\n"
            "- A strong, curiosity-inducing hook/narrative opening\n"
            "- Core idea (explain the principle)\n"
            "- Why it matters (grounded explanation)\n"
            "- What the source teaches (specific evidence)\n"
            "- Practical takeaway (actionable advice)\n"
            "- Memorable closing\n\n"
            "Only output the Markdown content, nothing else."
        )

        from pi_agent.messages import NeutralMessage
        messages = [NeutralMessage(role="user", content=f"User Request: {topic}\n\nEvidence:\n{context_text}")]
        
        assistant_response = self.provider.complete(system=system_prompt, messages=messages)
        final_answer = assistant_response.content

        # Add the disclaimer to the bottom of the artifact
        final_answer += f"\n\n---\n*{SHIP30_SOURCE_NOTE}*"

        # 3. Store artifact and sources in the agent's state
        self.set_artifact_callback(
            artifact={
                "type": "markdown",
                "title": f"Ship 30 for 30: {topic[:30]}",
                "content": final_answer
            },
            sources=sources
        )

        return f"Ship 30 artifact successfully generated based on {len(sources)} transcript chunks. The user can view it in the Artifact Viewer."
