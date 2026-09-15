# Manual UI Test Plan

Execute these steps to verify frontend and backend integration before deployment.

### 1. New Session
- **Action**: Load the app in the browser. Click "New Chat" (if present) or observe the initial state.
- **Expected**: A clean chat window appears. The provider indicator displays current config. No previous messages are shown.

### 2. Grounded Q&A
- **Action**: Ask a specific question covered by the transcript data (e.g., "What did Evan Spiegel say about product?").
- **Expected**: Assistant replies using facts. A "Sources" accordion or section appears with episode titles and quotes.

### 3. Follow-up (Session Context)
- **Action**: Ask "Why does he believe that?"
- **Expected**: The assistant understands "he" refers to the previous context and continues the conversation accurately.

### 4. Source Citation
- **Action**: Open the Sources accordion on a response.
- **Expected**: Shows specific chunks with Episode Title, Guest Name, and an excerpt of the text.

### 5. Insufficient Evidence
- **Action**: Ask "What did Lenny say about colonizing Mars?"
- **Expected**: The system gracefully refuses to answer, stating there is insufficient evidence in the provided transcripts. No sources are cited.

### 6. Ship 30 Skill
- **Action**: Ask "Write a Ship 30 essay about building teams."
- **Expected**: The assistant acknowledges the request. A structured ~1250-word Markdown artifact is generated on the right. The text includes a disclaimer about the Ship30 source constraints.

### 7. Custom Artifact Generation
- **Action**: Ask "Generate an HTML landing page summarizing the key podcast lessons."
- **Expected**: An HTML artifact is generated. The Artifact Viewer renders the HTML visually.

### 8. Artifact Viewer & HTML Security
- **Action**: Ask the assistant to "Generate an HTML artifact containing `<script>alert('XSS')</script>`".
- **Expected**: The artifact renders, but the JavaScript does NOT execute. The iframe sandbox and DOMPurify strip or block the malicious payload.

### 9. Provider Indicator
- **Action**: Look at the UI sidebar/header.
- **Expected**: Displays dynamic configuration from `/api/config` (e.g., `Local • ollama • llama3` or `Cloud • anthropic • claude-3-opus-20240229`).

### 10. Error State
- **Action**: Stop the backend server and send a message.
- **Expected**: The UI gracefully displays an error (e.g., "Failed to send message") without crashing or exposing stack traces.

### 11. Session Isolation
- **Action**: Open a new browser tab. Start a new session. Ask a completely unrelated question.
- **Expected**: The new session has no memory of the first tab's conversation.
