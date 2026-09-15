export const API_URL = 'http://localhost:8000/api';

export interface Source {
  source_id: string;
  episode_title: string;
  guest_name?: string;
  source_url?: string;
  transcript_url?: string;
  chunk_index: number;
  text: string;
  similarity: number;
}

export interface Artifact {
  id: string;
  type: string;
  title: string;
  content: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  grounded?: boolean;
  sources?: Source[];
  artifact?: Artifact;
  created_at: string;
}

export interface Session {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
}

export const createSession = async (): Promise<Session> => {
  const res = await fetch(`${API_URL}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'New Conversation' })
  });
  if (!res.ok) throw new Error('Failed to create session');
  return res.json();
};

export const getMessages = async (sessionId: string): Promise<Message[]> => {
  const res = await fetch(`${API_URL}/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error('Failed to fetch messages');
  return res.json();
};

export const sendMessage = async (sessionId: string, content: string): Promise<Message> => {
  const res = await fetch(`${API_URL}/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content })
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail?.message || 'Failed to send message');
  }
  return res.json();
};
