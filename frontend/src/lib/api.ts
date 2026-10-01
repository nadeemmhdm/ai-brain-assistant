export const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

// --- session token (app-lock) -------------------------------------------
let sessionToken: string | null = sessionStorage.getItem("session_token");
export function setSessionToken(t: string | null) {
  sessionToken = t;
  if (t) sessionStorage.setItem("session_token", t);
  else sessionStorage.removeItem("session_token");
}
export function getSessionToken() { return sessionToken; }

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) { onUnauthorized = fn; }

export async function authFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {});
  if (sessionToken) headers.set("Authorization", `Bearer ${sessionToken}`);
  const res = await fetch(url, { ...init, headers });
  if (res.status === 401 && sessionToken) { setSessionToken(null); onUnauthorized?.(); }
  return res;
}

export async function jAuth(res: Response): Promise<any> {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `${res.status} ${res.statusText}`);
  return body;
}

export async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `${res.status} ${res.statusText}`);
  }
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
  action?: ActionProposal | null;
  confidence?: Confidence | null;
}

export interface Confidence { label: "high" | "medium" | "low"; sources: number; domains: number; best_tier?: string | null; from_memory?: boolean; flagged?: string[] }
export interface ActionProposal {
  action: string; label: string; risk: "read" | "write" | "external" | "destructive";
  params: Record<string, any>; status: "pending" | "approved" | "denied" | "done" | "failed"; note?: string | null;
}
export type SearchMode = "off" | "quick" | "deep";

export interface Source {
  id: string;
  index?: number;
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
  listConversations: () => authFetch(`${BASE}/api/conversations`).then(j<Conversation[]>),
  createConversation: (title = "New chat") =>
    authFetch(`${BASE}/api/conversations`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }).then(j<Conversation>),
  renameConversation: (id: string, title: string) =>
    authFetch(`${BASE}/api/conversations/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }),
  deleteConversation: (id: string) => authFetch(`${BASE}/api/conversations/${id}`, { method: "DELETE" }),
  getMessages: (id: string) => authFetch(`${BASE}/api/conversations/${id}/messages`).then(j<Message[]>),
  deleteMessage: (id: string) => authFetch(`${BASE}/api/messages/${id}`, { method: "DELETE" }),

  // model / settings
  getModelStatus: () => authFetch(`${BASE}/api/model/status`).then(j<any>),
  getSettings: () => authFetch(`${BASE}/api/settings`).then(j<Record<string, string>>),
  setSetting: (key: string, value: string) =>
    authFetch(`${BASE}/api/settings`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value }),
    }),

  // brain
  brainStats: () => authFetch(`${BASE}/api/brain`).then(j<any>),
  brainTopics: () => authFetch(`${BASE}/api/brain/topics`).then(j<any[]>),
  brainKnowledge: (query = "", topic?: string) =>
    authFetch(`${BASE}/api/brain/knowledge?query=${encodeURIComponent(query)}${topic ? `&topic=${encodeURIComponent(topic)}` : ""}`).then(j<any[]>),
  brainSources: () => authFetch(`${BASE}/api/brain/sources`).then(j<any[]>),
  deleteKnowledge: (id: string) => authFetch(`${BASE}/api/brain/knowledge/${id}`, { method: "DELETE" }),
  brainSessions: () => authFetch(`${BASE}/api/brain/sessions`).then(j<any[]>),

  // auto learn
  startLearn: (topic: string) =>
    authFetch(`${BASE}/api/learn`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    }).then(j<{ session_id: string }>),
  learnStatus: (session_id: string) => authFetch(`${BASE}/api/learn/status?session_id=${session_id}`).then(j<any>),
  learnActive: () => authFetch(`${BASE}/api/learn/active`).then((r) => (r.ok ? r.json() : null)),
  learnControl: (session_id: string, action: "pause" | "resume" | "cancel") =>
    authFetch(`${BASE}/api/learn/${action}?session_id=${session_id}`, { method: "POST" }),


  // auth
  authStatus: () => fetch(`${BASE}/api/auth/status`).then(j<{ configured: boolean }>),
  authSetup: (password: string) =>
    fetch(`${BASE}/api/auth/setup`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) }).then(jAuth),
  authLogin: (password: string) =>
    fetch(`${BASE}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) }).then(jAuth),
  authChange: (current: string, next: string) =>
    authFetch(`${BASE}/api/auth/change`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ current, new: next }) }).then(jAuth),
  authRemove: (password: string) =>
    authFetch(`${BASE}/api/auth/remove`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) }).then(jAuth),

  // datasets
  listDatasets: () => authFetch(`${BASE}/api/dataset`).then(j<any[]>),
  createDataset: (name: string, topic?: string, only_verified = true) =>
    authFetch(`${BASE}/api/dataset`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, topic: topic || null, only_verified }) }).then(jAuth),
  datasetItems: (id: string) => authFetch(`${BASE}/api/dataset/${id}/items`).then(j<any[]>),
  approveItem: (id: string, approved: boolean) =>
    authFetch(`${BASE}/api/dataset/item/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ approved }) }),
  deleteDataset: (id: string) => authFetch(`${BASE}/api/dataset/${id}`, { method: "DELETE" }),

  // training
  startTraining: (body: any) =>
    authFetch(`${BASE}/api/training/start`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(jAuth),
  trainingStatus: (job_id: string) => authFetch(`${BASE}/api/training/status?job_id=${job_id}`).then(j<any>),
  listTraining: () => authFetch(`${BASE}/api/training`).then(j<any[]>),

  // mcp
  mcpConnectors: () => authFetch(`${BASE}/api/mcp/connectors`).then(j<any>),
};

export interface ChatStreamHandlers {
  onUserMessage?: (m: { id: string; content: string }) => void;
  onStatus?: (s: { stage: string; detail?: string; done?: number; total?: number }) => void;
  onSources?: (s: { sources: Source[]; confidence?: Confidence | null }) => void;
  onDelta?: (text: string) => void;
  onThinkingDelta?: (text: string) => void;
  onTitle?: (title: string) => void;
  onMemorySaved?: (m: { content: string; kind?: string }) => void;
  onDone?: (m: { id: string; content: string; thinking?: string | null; sources: Source[]; confidence?: Confidence | null; action?: ActionProposal | null }) => void;
  onError?: (message: string) => void;
}

export async function streamChat(
  body: {
    conversation_id: string;
    message: string;
    parent_id?: string | null;
    model: ModelChoice;
    reasoning_level: ReasoningLevel;
    search_mode: SearchMode;
    offline?: boolean;
    voice?: boolean;
    tz_offset_min?: number;
    regenerate_of?: string | null;
    edit_of?: string | null;
    skill_id?: string | null;
  },
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
) {
  const res = await authFetch(`${BASE}/api/chat`, {
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
        case "thinking_delta": handlers.onThinkingDelta?.(data.text); break;
        case "title": handlers.onTitle?.(data.title); break;
        case "memory_saved": handlers.onMemorySaved?.(data); break;
        case "done": handlers.onDone?.(data); break;
        case "error": handlers.onError?.(data.message); break;
      }
    }
  }
}
