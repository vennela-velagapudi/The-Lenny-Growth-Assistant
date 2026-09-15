# Product Requirements Document (PRD)

## Forward Deployment Brief
**User/Problem:** Users want a conversational AI assistant that can answer growth, product, and career questions specifically grounded in the high-quality insights from Lenny's Podcast, without hallucinations or generic advice.

**Success Metrics:**
- High accuracy of answers grounded *only* in the provided transcripts.
- Successful rendering of requested artifacts (e.g., Ship 30 essays, HTML).
- Complete local execution capability using Ollama.
- Seamless provider switching.

**Assumptions:**
- Local deployment environments can support Docker, PostgreSQL, and an 8B class LLM via Ollama.
- Transcripts are available in text/markdown format.

**Scope Choices:**
- Minimal user authentication (anonymous session-based identity).
- Single, specific "Ship 30 for 30" writing skill.
- No complex multi-agent workflows; a single agent loop handles intent routing.

**Risks/Trade-offs:**
- Running Ollama locally may be slower and less capable of strict tool-calling adherence compared to Claude. Mitigation: Provide very clear system prompts and robust fallback parsing.
- HTML artifact generation poses XSS risks. Mitigation: Strict iframe sandboxing and content security policies.
