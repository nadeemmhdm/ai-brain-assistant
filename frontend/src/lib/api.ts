const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export type ReasoningLevel = "off" | "low" | "medium" | "high" | "max";
export type ModelChoice = "main" | "agent";

export interface Message {
  id: string;
  conversation_id: string;
  parent_id: string | null;
  role: "user" | "assistant" | "system";
  content: string;
  thinking?: string | null;
  sources?: Source[] | null;
  model?: string;
  reasoning_level?: string;
  created_at: number;
}

export interface Source {
  id: string;
  url: string;
  title: string;
  trust_tier: "A" | "B" | "C" | "D";
  source_type: string;
  fetched_at: number;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
}

export const api = {
  // conversations
  listConversations: () => fetch(`${BASE}/api/conversations`).then(j<Conversation[]>),
  createConversation: (title = "New chat") =>
    fetch(`${BASE}/api/conversations`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }).then(j<Conversation>),
  renameConversation: (id: string, title: string) =>
    fetch(`${BASE}/api/conversations/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }),
  deleteConversation: (id: string) => fetch(`${BASE}/api/conversations/${id}`, { method: "DELETE" }),
  getMessages: (id: string) => fetch(`${BASE}/api/conversations/${id}/messages`).then(j<Message[]>),
  deleteMessage: (id: string) => fetch(`${BASE}/api/messages/${id}`, { method: "DELETE" }),

  // model / settings
  getModelStatus: () => fetch(`${BASE}/api/model/status`).then(j<any>),
  getSettings: () => fetch(`${BASE}/api/settings`).then(j<Record<string, string>>),
  setSetting: (key: string, value: string) =>
    fetch(`${BASE}/api/settings`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value }),
    }),

  // brain
  brainStats: () => fetch(`${BASE}/api/brain`).then(j<any>),
  brainTopics: () => fetch(`${BASE}/api/brain/topics`).then(j<any[]>),
  brainKnowledge: (query = "", topic?: string) =>
    fetch(`${BASE}/api/brain/knowledge?query=${encodeURIComponent(query)}${topic ? `&topic=${encodeURIComponent(topic)}` : ""}`).then(j<any[]>),
  brainSources: () => fetch(`${BASE}/api/brain/sources`).then(j<any[]>),
  brainSessions: () => fetch(`${BASE}/api/brain/sessions`).then(j<any[]>),

  // auto learn
  startLearn: (topic: string) =>
    fetch(`${BASE}/api/learn`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    }).then(j<{ session_id: string }>),
  learnStatus: (session_id: string) => fetch(`${BASE}/api/learn/status?session_id=${session_id}`).then(j<any>),
  learnControl: (session_id: string, action: "pause" | "resume" | "cancel") =>
    fetch(`${BASE}/api/learn/${action}?session_id=${session_id}`, { method: "POST" }),

  // mcp
  mcpConnectors: () => fetch(`${BASE}/api/mcp/connectors`).then(j<any>),
};

export interface ChatStreamHandlers {
  onUserMessage?: (m: { id: string; content: string }) => void;
  onStatus?: (s: { stage: string }) => void;
  onSources?: (s: { sources: Source[] }) => void;
  onDelta?: (text: string) => void;
  onDone?: (m: { id: string; content: string; thinking?: string; sources: Source[] }) => void;
  onError?: (message: string) => void;
}

export async function streamChat(
  body: {
    conversation_id: string;
    message: string;
    parent_id?: string | null;
    model: ModelChoice;
    reasoning_level: ReasoningLevel;
    search_mode: boolean;
    regenerate_of?: string | null;
  },
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
) {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.body) throw new Error("No stream body");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const chunk of events) {
      const lines = chunk.split("\n");
      const eventLine = lines.find((l) => l.startsWith("event:"));
      const dataLine = lines.find((l) => l.startsWith("data:"));
      if (!eventLine || !dataLine) continue;
      const event = eventLine.slice(6).trim();
      const data = JSON.parse(dataLine.slice(5).trim());
      switch (event) {
        case "user_message": handlers.onUserMessage?.(data); break;
        case "status": handlers.onStatus?.(data); break;
        case "sources": handlers.onSources?.(data); break;
        case "delta": handlers.onDelta?.(data.text); break;
        case "done": handlers.onDone?.(data); break;
        case "error": handlers.onError?.(data.message); break;
      }
    }
  }
}
