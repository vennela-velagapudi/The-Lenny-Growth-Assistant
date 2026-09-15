# Lenny Growth Assistant - Demo Script

**Target Length**: 2–3 minutes.

> **CRITICAL REMINDER**: The assignment requires your camera to be enabled. Please ensure your camera is ON before recording.

## 0:00–0:20 - Problem + Product Overview
* **Action**: Show the main chat UI. 
* **Talk Track**: "Welcome to the Lenny Growth Assistant. This is a conversational tool built on top of Lenny's Podcast transcripts. Rather than searching through hours of audio, users can ask grounded growth questions and get immediate, cited answers. It’s powered by the Pi Coding Agent, uses pgvector for RAG, and supports both local Ollama and cloud Anthropic models."

## 0:20–0:50 - Grounded Q&A
* **Action**: Type the following into the chat: *"What does Brian Halligan say about pricing strategy?"*
* **Talk Track**: "Let's ask a specific question. The system will retrieve relevant chunks from the transcribed podcasts. Notice how it only uses facts from the provided transcripts rather than hallucinating generic advice."

## 0:50–1:10 - Source Citations & Follow-up
* **Action**: Point to the "Sources" box below the response. Then type: *"Did he mention freemium?"*
* **Talk Track**: "Here you can see the exact episodes and quotes used. The session maintains full conversational context, so I can ask a follow-up like 'Did he mention freemium?' without restating his name."

## 1:10–1:40 - Ship30 Request & Deterministic Routing
* **Action**: Type: *"Write a Ship 30 essay on the importance of listening to customers based on the podcast."*
* **Talk Track**: "Now let's use the Ship 30 for 30 skill. The agent intercepts this deterministically and routes it to a registered Pi Agent tool. The tool grounds the essay's structure on the official Ship 30 Ultimate Guide framework—using formats like the 4A paths and skimmable paragraphs—while strictly pulling factual claims from Lenny's transcripts."

## 1:40–2:05 - Artifact Viewer
* **Action**: Look at the right panel where the Artifact is rendered. Scroll through it.
* **Talk Track**: "The response generates an ~1250 word artifact that is securely rendered in an HTML sandboxed iframe here on the right, keeping the main chat uncluttered. You can clearly see the Ship30 formatting combined with transcript evidence."

## 2:05–2:20 - Provider Configuration & Local Ollama
* **Action**: Hover over or point to the Provider Indicator in the UI (e.g., `Local • ollama • llama3`).
* **Talk Track**: "As required by the assignment, this is running entirely locally using Ollama and the llama3 model. The frontend dynamically fetches this configuration from the backend, making it fully transparent which provider is driving the agent."

## 2:20–2:40 - Architecture, Security & Conclusion
* **Action**: Briefly show the terminal running Docker Compose or just conclude verbally.
* **Talk Track**: "Under the hood, we use pgvector for semantic search. When transcript evidence is missing, the agent is hardcoded to refuse to answer, ensuring strict grounding. And our UI is protected by DOMPurify and strict iframe sandboxing. That's the Lenny Growth Assistant!"
