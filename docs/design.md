# Design Document

## UI/UX
- **Chat Interface:** Standard conversational view (left/center).
- **Artifact Viewer:** A side-by-side or collapsible pane (right) to view generated essays or UI components.
- **Source Citations:** Links in the chat should visually indicate they are sources (e.g., small pill badges).

## Backend Design Patterns
- **Repository Pattern:** For database access (`SessionRepo`, `MessageRepo`), making unit testing easier.
- **Dependency Injection:** FastAPI `Depends()` for injecting DB sessions and LLM providers into routes.
- **Streaming:** Server-Sent Events (SSE) for streaming LLM responses to the frontend.
