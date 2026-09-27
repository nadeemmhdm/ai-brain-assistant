import { create } from "zustand";
import type { Message, ReasoningLevel, ModelChoice } from "@/lib/api";

interface AppState {
  theme: "dark" | "light";
  setTheme: (t: "dark" | "light") => void;

  reasoningLevel: ReasoningLevel;
  setReasoningLevel: (r: ReasoningLevel) => void;

  model: ModelChoice;
  setModel: (m: ModelChoice) => void;

  searchMode: boolean;
  setSearchMode: (b: boolean) => void;

  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;

  messagesByConversation: Record<string, Message[]>;
  setMessages: (conversationId: string, messages: Message[]) => void;
  appendMessage: (conversationId: string, message: Message) => void;
  updateMessage: (conversationId: string, id: string, patch: Partial<Message>) => void;
  removeMessage: (conversationId: string, id: string) => void;

  settingsOpen: boolean;
  setSettingsOpen: (b: boolean) => void;

  sidebarOpen: boolean;
  setSidebarOpen: (b: boolean) => void;

  streaming: boolean;
  setStreaming: (b: boolean) => void;
}

const savedTheme = (localStorage.getItem("theme") as "dark" | "light") || "dark";
document.documentElement.setAttribute("data-theme", savedTheme);

export const useAppStore = create<AppState>((set, get) => ({
  theme: savedTheme,
  setTheme: (t) => {
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem("theme", t);
    set({ theme: t });
  },

  reasoningLevel: (localStorage.getItem("reasoningLevel") as ReasoningLevel) || "medium",
  setReasoningLevel: (r) => { localStorage.setItem("reasoningLevel", r); set({ reasoningLevel: r }); },

  model: (localStorage.getItem("model") as ModelChoice) || "main",
  setModel: (m) => { localStorage.setItem("model", m); set({ model: m }); },

  searchMode: localStorage.getItem("searchMode") === "true",
  setSearchMode: (b) => { localStorage.setItem("searchMode", String(b)); set({ searchMode: b }); },

  activeConversationId: null,
  setActiveConversationId: (id) => set({ activeConversationId: id }),

  messagesByConversation: {},
  setMessages: (cid, messages) =>
    set((s) => ({ messagesByConversation: { ...s.messagesByConversation, [cid]: messages } })),
  appendMessage: (cid, message) =>
    set((s) => ({
      messagesByConversation: {
        ...s.messagesByConversation,
        [cid]: [...(s.messagesByConversation[cid] || []), message],
      },
    })),
  updateMessage: (cid, id, patch) =>
    set((s) => ({
      messagesByConversation: {
        ...s.messagesByConversation,
        [cid]: (s.messagesByConversation[cid] || []).map((m) => (m.id === id ? { ...m, ...patch } : m)),
      },
    })),
  removeMessage: (cid, id) =>
    set((s) => ({
      messagesByConversation: {
        ...s.messagesByConversation,
        [cid]: (s.messagesByConversation[cid] || []).filter((m) => m.id !== id),
      },
    })),

  settingsOpen: false,
  setSettingsOpen: (b) => set({ settingsOpen: b }),

  sidebarOpen: true,
  setSidebarOpen: (b) => set({ sidebarOpen: b }),

  streaming: false,
  setStreaming: (b) => set({ streaming: b }),
}));
