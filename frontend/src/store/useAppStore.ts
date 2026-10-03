import { create } from "zustand";
import type { Message, ReasoningLevel, ModelChoice, SearchMode } from "@/lib/api";

const ls = (k: string, d: string) => localStorage.getItem(k) ?? d;

export interface StageInfo { stage: string; detail?: string; done?: number; total?: number }
export interface LiveState { stages: StageInfo[]; thinking: string; startedAt: number }
export type TeacherTurn={actor:"student"|"teacher";label:string;content?:string;thinking?:string};
export type TeacherLesson={id:string;subtopic:string;question:string;turns:TeacherTurn[];verified?:boolean};
export interface TeacherSession {
  topic:string; busy:boolean; error:string; plan:any|null; lessons:TeacherLesson[]; summary:any|null; startedAt:number|null;
}

interface AppState {
  theme: "dark" | "light" | "system";
  setTheme: (t: "dark" | "light" | "system") => void;

  reasoningLevel: ReasoningLevel;
  setReasoningLevel: (r: ReasoningLevel) => void;
  model: ModelChoice;
  setModel: (m: ModelChoice) => void;

  searchMode: SearchMode;
  setSearchMode: (m: SearchMode) => void;
  offlineMode: boolean;               // user-forced offline: no web, use only local knowledge
  setOfflineMode: (b: boolean) => void;

  // identity (mirrors backend settings)
  aiName: string;
  userName: string;
  onboarded: boolean;
  setProfile: (p: Partial<{ aiName: string; userName: string; onboarded: boolean }>) => void;

  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;

  messagesByConversation: Record<string, Message[]>;
  setMessages: (conversationId: string, messages: Message[]) => void;
  appendMessage: (conversationId: string, message: Message) => void;
  updateMessage: (conversationId: string, id: string, patch: Partial<Message>) => void;
  removeMessage: (conversationId: string, id: string) => void;

  live: Record<string, LiveState>;                       // in-progress "thinking" info per pending message id
  setLive: (id: string, fn: (l: LiveState) => LiveState) => void;
  clearLive: (id: string) => void;

  settingsOpen: boolean;
  setSettingsOpen: (b: boolean) => void;
  sidebarOpen: boolean;
  setSidebarOpen: (b: boolean) => void;
  voiceOpen: boolean;
  setVoiceOpen: (b: boolean) => void;

  streaming: boolean;
  setStreaming: (b: boolean) => void;

  teacherSession: TeacherSession;
  patchTeacherSession: (patch: Partial<TeacherSession>) => void;
  updateTeacherLesson: (id:string, fn:(lesson:TeacherLesson)=>TeacherLesson) => void;

  messageQueue: string[];              // waiting list -- messages typed while a reply is still generating
  enqueueMessage: (text: string) => boolean;   // false if the queue is already full (max 5)
  dequeueMessage: () => string | undefined;
  removeQueuedMessage: (index: number) => void;
  editQueuedMessage: (index: number, text: string) => void;
  clearQueue: () => void;
}
export const MAX_QUEUED_MESSAGES = 5;

const savedTheme = (ls("theme", "system") as "dark" | "light" | "system");
const systemTheme = () => window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
const applyTheme = (t: "dark" | "light" | "system") => document.documentElement.setAttribute("data-theme", t === "system" ? systemTheme() : t);
applyTheme(savedTheme);
if (savedTheme === "system") window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => applyTheme("system"));
const legacySearch = localStorage.getItem("searchMode");
const initialSearch: SearchMode = legacySearch === "true" ? "quick" : (["off", "quick", "deep"].includes(legacySearch || "") ? (legacySearch as SearchMode) : "off");

export const useAppStore = create<AppState>((set) => ({
  theme: savedTheme,
  setTheme: (t) => { applyTheme(t); localStorage.setItem("theme", t); set({ theme: t }); },

  reasoningLevel: ls("reasoningLevel", "medium") as ReasoningLevel,
  setReasoningLevel: (r) => { localStorage.setItem("reasoningLevel", r); set({ reasoningLevel: r }); },
  model: ls("model", "main") as ModelChoice,
  setModel: (m) => { localStorage.setItem("model", m); set({ model: m }); },

  searchMode: initialSearch,
  setSearchMode: (m) => { localStorage.setItem("searchMode", m); set({ searchMode: m }); },
  offlineMode: ls("offlineMode", "false") === "true",
  setOfflineMode: (b) => { localStorage.setItem("offlineMode", String(b)); set({ offlineMode: b }); },

  aiName: "Nila", userName: "", onboarded: true,
  setProfile: (p) => set(p),

  activeConversationId: null,
  setActiveConversationId: (id) => set({ activeConversationId: id }),

  messagesByConversation: {},
  setMessages: (cid, messages) => set((s) => ({ messagesByConversation: { ...s.messagesByConversation, [cid]: messages } })),
  appendMessage: (cid, message) => set((s) => ({ messagesByConversation: { ...s.messagesByConversation, [cid]: [...(s.messagesByConversation[cid] || []), message] } })),
  updateMessage: (cid, id, patch) => set((s) => ({ messagesByConversation: { ...s.messagesByConversation, [cid]: (s.messagesByConversation[cid] || []).map((m) => (m.id === id ? { ...m, ...patch } : m)) } })),
  removeMessage: (cid, id) => set((s) => ({ messagesByConversation: { ...s.messagesByConversation, [cid]: (s.messagesByConversation[cid] || []).filter((m) => m.id !== id) } })),

  live: {},
  setLive: (id, fn) => set((s) => ({ live: { ...s.live, [id]: fn(s.live[id] || { stages: [], thinking: "", startedAt: Date.now() }) } })),
  clearLive: (id) => set((s) => { const { [id]: _, ...rest } = s.live; return { live: rest }; }),

  settingsOpen: false,
  setSettingsOpen: (b) => set({ settingsOpen: b }),
  sidebarOpen: ls("sidebarOpen", "true") === "true",
  setSidebarOpen: (b) => { localStorage.setItem("sidebarOpen", String(b)); set({ sidebarOpen: b }); },
  voiceOpen: false,
  setVoiceOpen: (b) => set({ voiceOpen: b }),

  streaming: false,
  setStreaming: (b) => set({ streaming: b }),

  teacherSession: {topic:"",busy:false,error:"",plan:null,lessons:[],summary:null,startedAt:null},
  patchTeacherSession: (patch) => set((s)=>({teacherSession:{...s.teacherSession,...patch}})),
  updateTeacherLesson: (id,fn) => set((s)=>({teacherSession:{...s.teacherSession,lessons:s.teacherSession.lessons.map(l=>l.id===id?fn(l):l)}})),

  messageQueue: [],
  enqueueMessage: (text) => {
    let ok = false;
    set((s) => {
      if (s.messageQueue.length >= MAX_QUEUED_MESSAGES) return s;
      ok = true;
      return { messageQueue: [...s.messageQueue, text] };
    });
    return ok;
  },
  dequeueMessage: () => {
    let next: string | undefined;
    set((s) => {
      if (!s.messageQueue.length) return s;
      next = s.messageQueue[0];
      return { messageQueue: s.messageQueue.slice(1) };
    });
    return next;
  },
  removeQueuedMessage: (index) => set((s) => ({ messageQueue: s.messageQueue.filter((_, i) => i !== index) })),
  editQueuedMessage: (index, text) => set((s) => ({ messageQueue: s.messageQueue.map((m, i) => (i === index ? text : m)) })),
  clearQueue: () => set({ messageQueue: [] }),
}));
