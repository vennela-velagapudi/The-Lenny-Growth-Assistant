import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import DOMPurify from 'dompurify';
import './App.css';
import { createSession, sendMessage } from './api';
import type { Session, Message, Artifact } from './api';

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Right side Artifact Viewer state
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleNewSession = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const newSession = await createSession();
      setSession(newSession);
      setMessages([]);
      setActiveArtifact(null);
    } catch (err: any) {
      setError(err.message || 'Failed to create session');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !session) return;
    
    const userMsg = input.trim();
    setInput('');
    setError(null);
    
    // Optimistic UI
    const tempId = Date.now().toString();
    setMessages(prev => [...prev, {
      id: tempId,
      role: 'user',
      content: userMsg,
      created_at: new Date().toISOString()
    }]);

    setIsLoading(true);
    try {
      const responseMsg = await sendMessage(session.id, userMsg);
      setMessages(prev => [...prev, responseMsg]);
      
      // Auto-open artifact if generated
      if (responseMsg.artifact) {
        setActiveArtifact(responseMsg.artifact);
      }
    } catch (err: any) {
      setError(err.message || 'Error communicating with agent.');
      // Remove optimistic message on error or show error state
      setMessages(prev => prev.filter(m => m.id !== tempId));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Left Sidebar */}
      <div className="sidebar">
        <h1>Lenny Growth Assistant</h1>
        <button className="new-session-btn" onClick={handleNewSession} disabled={isLoading}>
          + New Chat
        </button>
        
        {/* Environment / Provider Visibility */}
        <div className="provider-indicator">
          <strong>Provider:</strong> Local &bull; Ollama &bull; llama3
          <br/><br/>
          <small>Model settings configured via backend .env</small>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="main-content">
        {error && <div className="error-banner">{error}</div>}
        
        {!session ? (
          <div className="chat-area" style={{ justifyContent: 'center', alignItems: 'center' }}>
            <h2 style={{ color: '#9ca3af' }}>Start a new session to begin</h2>
          </div>
        ) : (
          <>
            <div className="chat-area">
              {messages.length === 0 && (
                <div style={{ textAlign: 'center', color: '#6b7280', marginTop: '20px' }}>
                  Ask a question about growth, or try: <br/>
                  <strong>"Write a Ship 30 about..."</strong>
                </div>
              )}
              {messages.map((msg) => (
                <div key={msg.id} className={`message ${msg.role} ${msg.grounded === false ? 'ungrounded' : ''}`}>
                  <div className="message-content">
                    {msg.role === 'assistant' ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : (
                      msg.content
                    )}
                  </div>
                  
                  {msg.artifact && (
                    <button className="artifact-link-btn" onClick={() => setActiveArtifact(msg.artifact!)}>
                      View {msg.artifact.type === 'html' ? 'Landing Page' : 'Document'} Artifact
                    </button>
                  )}

                  {msg.sources && msg.sources.length > 0 && (
                    <div className="sources-container">
                      <h4>Sources:</h4>
                      {msg.sources.map((src, idx) => (
                        <div key={idx} className="source-item">
                          <strong>{src.episode_title}</strong> {src.guest_name ? `(with ${src.guest_name})` : ''}
                          <br />
                          {src.source_url ? (
                            <a href={src.source_url} target="_blank" rel="noreferrer">Listen to Episode</a>
                          ) : 'No URL available'}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="message assistant" style={{ fontStyle: 'italic', color: '#6b7280' }}>
                  Agent is thinking...
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="input-area">
              <input 
                type="text" 
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                placeholder="Ask Lenny..."
                disabled={isLoading}
              />
              <button onClick={handleSend} disabled={isLoading || !input.trim()}>
                Send
              </button>
            </div>
          </>
        )}
      </div>

      {/* Right Artifact Viewer */}
      <div className="artifact-viewer">
        <div className="artifact-header">
          <h2>Artifact Viewer</h2>
          {activeArtifact && <div className="artifact-type">{activeArtifact.type}</div>}
        </div>
        <div className="artifact-content">
          {!activeArtifact ? (
            <div className="artifact-empty">No artifact selected</div>
          ) : (
            <>
              <h3 style={{ marginBottom: '15px' }}>{activeArtifact.title}</h3>
              {activeArtifact.type === 'html' ? (
                <iframe 
                  className="html-preview"
                  srcDoc={DOMPurify.sanitize(activeArtifact.content)} 
                  sandbox="" // strict sandbox, no scripts allowed
                  title="HTML Artifact Preview"
                />
              ) : (
                <div className="markdown-preview">
                  <ReactMarkdown>{activeArtifact.content}</ReactMarkdown>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
