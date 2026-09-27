import { useEffect, useRef, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { AutoLearnModal } from "@/components/layout/AutoLearnModal";
import { SettingsPanel } from "@/components/settings/SettingsPanel";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { GeneratingIndicator } from "@/components/chat/ThinkingIndicator";
import { useAppStore } from "@/store/useAppStore";
import { api, streamChat, type Conversation, type Message } from "@/lib/api";

export default function App() {
  const {
    activeConversationId, setActiveConversationId,
    messagesByConversation, setMessages, appendMessage, updateMessage, removeMessage,
    model, setModel, reasoningLevel, setReasoningLevel, searchMode, setSearchMode,
    streaming, setStreaming,
  } = useAppStore();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [autoLearnOpen, setAutoLearnOpen] = useState(false);
  const [offline, setOffline] = useState(!navigator.onLine);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const messages: Message[] = activeConversationId ? messagesByConversation[activeConversationId] || [] : [];

  useEffect(() => {
    const on = () => setOffline(false), off = () => setOffline(true);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);

  useEffect(() => { refreshConversations(); }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, messages[messages.length - 1]?.content]);

  async function refreshConversations() {
    const list = await api.listConversations().catch(() => []);
    setConversations(list);
    if (!activeConversationId && list.length > 0) selectConversation(list[0].id);
  }

  async function newConversation() {
    const c = await api.createConversation();
    setConversations((prev) => [c, ...prev]);
    setActiveConversationId(c.id);
    setMessages(c.id, []);
  }

  async function selectConversation(id: string) {
    setActiveConversationId(id);
    if (!messagesByConversation[id]) {
      const msgs = await api.getMessages(id).catch(() => []);
      setMessages(id, msgs);
    }
  }

  async function renameConversation(id: string, title: string) {
    await api.renameConversation(id, title);
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
  }

  async function deleteConversation(id: string) {
    await api.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConversationId === id) {
      const remaining = conversations.filter((c) => c.id !== id);
      if (remaining.length) selectConversation(remaining[0].id);
      else setActiveConversationId(null);
    }
  }

  async function ensureConversation(): Promise<string> {
    if (activeConversationId) return activeConversationId;
    const c = await api.createConversation();
    setConversations((prev) => [c, ...prev]);
    setActiveConversationId(c.id);
    setMessages(c.id, []);
    return c.id;
  }

  async function send(text: string, opts?: { parentId?: string | null; regenerateOf?: string | null; skipUserAppend?: boolean }) {
    const cid = await ensureConversation();
    const assistantId = "pending-" + Date.now();
    setStreaming(true);
    abortRef.current = new AbortController();
    let accumulated = "";

    appendMessage(cid, {
      id: assistantId, conversation_id: cid, parent_id: opts?.parentId ?? null,
      role: "assistant", content: "", reasoning_level: reasoningLevel, model, created_at: Date.now() / 1000,
    });

    try {
      await streamChat(
        {
          conversation_id: cid, message: text, parent_id: opts?.parentId ?? null,
          model, reasoning_level: reasoningLevel, search_mode: searchMode,
          regenerate_of: opts?.regenerateOf ?? null,
        },
        {
          onUserMessage: (m) => {
            if (!opts?.skipUserAppend) {
              appendMessage(cid, {
                id: m.id, conversation_id: cid, parent_id: opts?.parentId ?? null,
                role: "user", content: m.content, created_at: Date.now() / 1000,
              });
            }
          },
          onSources: (s) => updateMessage(cid, assistantId, { sources: s.sources }),
          onDelta: (delta) => {
            accumulated += delta;
            updateMessage(cid, assistantId, { content: accumulated });
          },
          onDone: (d) => updateMessage(cid, assistantId, {
            id: d.id, content: d.content, thinking: d.thinking, sources: d.sources,
          }),
          onError: (message) => updateMessage(cid, assistantId, { content: `⚠️ ${message}` }),
        },
        abortRef.current.signal,
      );
    } catch (e) {
      // aborted or network error -- leave partial content in place
    } finally {
      setStreaming(false);
      refreshConversations();
    }
  }

  function stop() {
    abortRef.current?.abort();
    setStreaming(false);
  }

  function copy(text: string) { navigator.clipboard.writeText(text); }

  function regenerate(m: Message) {
    if (!activeConversationId) return;
    const list = messagesByConversation[activeConversationId] || [];
    const idx = list.findIndex((x) => x.id === m.id);
    const priorUser = [...list.slice(0, idx)].reverse().find((x) => x.role === "user");
    if (!priorUser) return;
    removeMessage(activeConversationId, m.id);
    send(priorUser.content, { parentId: priorUser.id, regenerateOf: priorUser.id, skipUserAppend: true });
  }

  function fork(m: Message) {
    // Forking = start replying from this message's point without altering the original thread.
    if (!activeConversationId) return;
    send("Continue from here.", { parentId: m.id });
  }

  async function del(m: Message) {
    if (!activeConversationId) return;
    await api.deleteMessage(m.id);
    removeMessage(activeConversationId, m.id);
  }

  function editResend(m: Message, newText: string) {
    if (!activeConversationId) return;
    removeMessage(activeConversationId, m.id);
    send(newText, { parentId: m.parent_id, skipUserAppend: false });
  }

  const activeTitle = conversations.find((c) => c.id === activeConversationId)?.title || "New chat";

  return (
    <div className="h-screen w-screen flex bg-canvas text-ink">
      <Sidebar
        conversations={conversations}
        onNew={newConversation}
        onSelect={selectConversation}
        onRename={renameConversation}
        onDelete={deleteConversation}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={activeTitle} onOpenAutoLearn={() => setAutoLearnOpen(true)} offline={offline} />

        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto w-full py-4">
            {messages.length === 0 && (
              <div className="text-center py-24 px-4">
                <h2 className="text-2xl font-serif font-light text-muted">
                  What would you like to know?
                </h2>
                <p className="text-xs text-muted mt-2">
                  Turn on Search for cited, trust-ranked answers, or run Auto Learn to build up the offline AI Brain.
                </p>
              </div>
            )}
            {messages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                isStreaming={streaming && m.role === "assistant" && m.id.startsWith("pending-")}
                onCopy={copy}
                onRegenerate={regenerate}
                onFork={fork}
                onDelete={del}
                onEditResend={editResend}
              />
            ))}
            {streaming && messages[messages.length - 1]?.role === "user" && (
              <div className="px-2 py-1"><GeneratingIndicator /></div>
            )}
          </div>
        </div>

        <div className="px-4 pb-4 pt-2 border-t border-border">
          <ChatComposer
            onSend={(text) => send(text)}
            disabled={streaming}
            streaming={streaming}
            onStop={stop}
            model={model} setModel={setModel}
            reasoningLevel={reasoningLevel} setReasoningLevel={setReasoningLevel}
            searchMode={searchMode} setSearchMode={setSearchMode}
          />
        </div>
      </div>

      <SettingsPanel />
      {autoLearnOpen && <AutoLearnModal onClose={() => setAutoLearnOpen(false)} />}
    </div>
  );
}
