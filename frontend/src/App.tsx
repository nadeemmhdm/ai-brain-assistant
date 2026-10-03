import { useEffect, useRef, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { AutoLearnModal } from "@/components/layout/AutoLearnModal";
import { SettingsPanel } from "@/components/settings/SettingsPanel";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { QueueStrip } from "@/components/chat/QueueStrip";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { GeneratingIndicator } from "@/components/chat/ThinkingIndicator";
import { NavRail, type View } from "@/components/layout/NavRail";
import { LockScreen } from "@/components/layout/LockScreen";
import { BrainView } from "@/components/views/BrainView";
import { TrainingView } from "@/components/views/TrainingView";
import { ModelsView } from "@/components/views/ModelsView";
import { GoogleView } from "@/components/views/GoogleView";
import { McpView } from "@/components/views/McpView";
import { TeacherView } from "@/components/views/TeacherView";
import { Toaster } from "@/components/ui/Toaster";
import { toast } from "@/store/useToast";
import { motion, AnimatePresence } from "motion/react";
import { Sparkles, Brain, Search, GraduationCap } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { api, streamChat, getSessionToken, setUnauthorizedHandler, type Conversation, type Message } from "@/lib/api";
import { api2 } from "@/lib/api2";
import { resolveEngine, listen, liveConversation, stopSpeaking } from "@/lib/voice";

export default function App() {
  const {
    activeConversationId, setActiveConversationId,
    messagesByConversation, setMessages, appendMessage, updateMessage, removeMessage,
    model, setModel, reasoningLevel, setReasoningLevel, searchMode, setSearchMode,
    offlineMode, aiName, live, setLive, clearLive,
    streaming, setStreaming,
    messageQueue, enqueueMessage, dequeueMessage, removeQueuedMessage, editQueuedMessage,
    sidebarOpen, setSidebarOpen,
  } = useAppStore();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [autoLearnOpen, setAutoLearnOpen] = useState(false);
  const [view, setView] = useState<View>("chat");
  const [skillId, setSkillId] = useState<string | null>(null);
  const [skillName, setSkillName] = useState<string | null>(null);
  const [locked, setLocked] = useState<boolean | null>(null); // null = still checking
  const [offline, setOffline] = useState(!navigator.onLine);
  const [voiceListening, setVoiceListening] = useState(false);
  const [liveVoiceState, setLiveVoiceState] = useState<"off"|"listening"|"thinking"|"speaking">("off");
  const liveVoiceAbort = useRef<AbortController | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const skipAutoDequeueRef = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const messages: Message[] = activeConversationId ? messagesByConversation[activeConversationId] || [] : [];

  useEffect(() => {
    const on = () => setOffline(false), off = () => setOffline(true);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => setLocked(true));
    api.authStatus()
      .then((s) => setLocked(s.configured && !getSessionToken()))
      .catch(() => setLocked(false));
  }, []);

  useEffect(() => { if (locked === false) refreshConversations(); }, [locked]);

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

  async function send(text: string, opts?: { parentId?: string | null; regenerateOf?: string | null; editOf?: string | null; skipUserAppend?: boolean }) {
    const cid = await ensureConversation();
    setStreaming(true);
    abortRef.current = new AbortController();
    let accumulated = "";
    let assistantId = "pending-" + Date.now();

    // The user's own message must land in the list immediately -- otherwise, until the
    // server echoes it back over the stream, the empty assistant bubble appears ABOVE it.
    const tempUserId = "temp-user-" + Date.now();
    if (!opts?.skipUserAppend) {
      appendMessage(cid, {
        id: tempUserId, conversation_id: cid, parent_id: opts?.parentId ?? null,
        role: "user", content: text, created_at: Date.now() / 1000,
      });
    }
    appendMessage(cid, {
      id: assistantId, conversation_id: cid, parent_id: opts?.parentId ?? null,
      role: "assistant", content: "", reasoning_level: reasoningLevel, model, created_at: Date.now() / 1000 + 0.001,
    });

    try {
      await streamChat(
        {
          conversation_id: cid, message: text, parent_id: opts?.parentId ?? null,
          model, reasoning_level: reasoningLevel, search_mode: searchMode, offline: offlineMode,
          tz_offset_min: new Date().getTimezoneOffset(), skill_id: opts?.skipUserAppend ? undefined : skillId,
          regenerate_of: opts?.regenerateOf ?? null, edit_of: opts?.editOf ?? null,
        },
        {
          onUserMessage: (m) => {
            if (!opts?.skipUserAppend) updateMessage(cid, tempUserId, { id: m.id });
          },
          onStatus: (s) => setLive(assistantId, (l) => ({ ...l, stages: [...l.stages, s] })),
          onThinkingDelta: (t) => setLive(assistantId, (l) => ({ ...l, thinking: l.thinking + t })),
          onSources: (s) => updateMessage(cid, assistantId, { sources: s.sources, confidence: s.confidence ?? null }),
          onDelta: (delta) => {
            accumulated += delta;
            updateMessage(cid, assistantId, { content: accumulated });
          },
          onTitle: (title) => setConversations((prev) => prev.map((c) => (c.id === cid ? { ...c, title } : c))),
          onMemorySaved: (m) => toast.info(m.kind === "research" ? m.content : `Remembered: ${m.content}`),
          onDone: (d) => {
            updateMessage(cid, assistantId, {
              id: d.id, content: d.content, thinking: d.thinking, sources: d.sources,
              confidence: d.confidence ?? null, action: d.action ?? null,
            });
            clearLive(assistantId);
          },
          onError: (message) => {
            updateMessage(cid, assistantId, { content: accumulated || `⚠️ ${message}` });
            clearLive(assistantId);
            toast.error(message.length > 80 ? "Something went wrong generating a reply" : message);
          },
        },
        abortRef.current.signal,
      );
    } catch (e: any) {
      if (e?.name !== "AbortError") {
        updateMessage(cid, assistantId, { content: accumulated || "⚠️ Connection to the backend was lost." });
        toast.error("Connection lost");
      }
      clearLive(assistantId);
    } finally {
      setStreaming(false);
      // Re-sync the finished conversation from SQLite. This repairs UI state if a
      // browser/proxy dropped the final SSE event after the backend saved the reply.
      try {
        const persisted = await api.getMessages(cid);
        if (persisted.length) setMessages(cid, persisted);
      } catch {
        // Keep the streamed local state when the backend is temporarily unreachable.
      }
      refreshConversations();
      if (skipAutoDequeueRef.current) {
        skipAutoDequeueRef.current = false;
      } else {
        const next = dequeueMessage();
        if (next) send(next);
      }
    }
  }

  async function liveVoice() {
    if (liveVoiceState !== "off") {
      liveVoiceAbort.current?.abort(); stopSpeaking(); setLiveVoiceState("off"); return;
    }
    if (streaming) return toast.info("Finish the current reply before starting Live Voice.");
    const ac = new AbortController(); liveVoiceAbort.current = ac;
    try {
      const { engine, note } = await resolveEngine("auto"); if (note) toast.info(note);
      if (offline && engine !== "local") throw new Error("Offline Live Voice needs local STT + TTS in Models & Voice.");
      await liveConversation({
        engine, signal: ac.signal, onState:setLiveVoiceState,
        onTranscript:(t)=>toast.info(`Heard: ${t.slice(0,80)}`),
        onTurn: async (text) => {
          const cid = await ensureConversation();
          let answer = "";
          await streamChat({conversation_id:cid,message:text,model,reasoning_level:reasoningLevel,search_mode:searchMode,offline:offlineMode,tz_offset_min:new Date().getTimezoneOffset(),voice:true},
            {onDelta:(d)=>{answer+=d},onError:(m)=>{throw new Error(m)}}, ac.signal);
          const persisted=await api.getMessages(cid).catch(()=>[]); if(persisted.length) setMessages(cid,persisted);
          return answer;
        }
      });
    } catch(e:any) { if(e?.name!=="AbortError") toast.error(e?.message||"Live Voice failed"); }
    finally { if(liveVoiceAbort.current===ac) liveVoiceAbort.current=null; setLiveVoiceState("off"); }
  }

  async function voiceInput() {
    if (voiceListening || streaming) return;
    setVoiceListening(true);
    try {
      const { engine, note } = await resolveEngine("auto");
      if (offline && engine !== "local") {
        toast.error("Offline speech recognition needs a local STT model. Install one in Models & Voice.");
        return;
      }
      if (note) toast.info(note);
      toast.info(engine === "local" ? "Listening offline…" : "Listening…");
      const text = await listen({ engine, maxMs: 20000, silenceMs: 1000, startTimeoutMs: 8000 });
      if (text.trim()) await send(text.trim());
      else toast.info("No speech detected");
    } catch (e: any) {
      toast.error(e?.message || "Speech recognition failed");
    } finally {
      setVoiceListening(false);
    }
  }

  function stop() {
    abortRef.current?.abort();
    setStreaming(false);
  }

  function forceSendQueued(index: number) {
    const text = messageQueue[index];
    if (!text) return;
    removeQueuedMessage(index);
    if (streaming) {
      skipAutoDequeueRef.current = true;
      stop();
    }
    send(text);
  }

  function copy(text: string) { navigator.clipboard.writeText(text); toast.success("Copied to clipboard"); }

  function regenerate(m: Message) {
    if (!activeConversationId) return;
    const list = messagesByConversation[activeConversationId] || [];
    const idx = list.findIndex((x) => x.id === m.id);
    const priorUser = [...list.slice(0, idx)].reverse().find((x) => x.role === "user");
    if (!priorUser) return;
    removeMessage(activeConversationId, m.id);
    send(priorUser.content, { parentId: priorUser.parent_id ?? null, regenerateOf: priorUser.id, skipUserAppend: true });
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
    send(newText, { parentId: m.parent_id, editOf: m.id, skipUserAppend: false });
  }

  function speak(m: Message) {
    import("@/lib/voice").then(({ speak, stopSpeaking }) => { stopSpeaking(); speak(m.content, "browser"); });
  }

  async function decideAction(m: Message, grant: "once" | "chat" | "always" | "deny", params: Record<string, any>) {
    if (!activeConversationId || !m.action) return;
    if (grant === "deny") {
      await api2.setActionStatus(m.id, "denied");
      updateMessage(activeConversationId, m.id, { action: { ...m.action, status: "denied" } });
      return;
    }
    try {
      const { result } = await api2.googleExecute(m.action.action, params, grant, activeConversationId);
      const text = await formatActionResult(m.action.action, result);
      await api2.setActionStatus(m.id, "done", undefined, text);
      updateMessage(activeConversationId, m.id, { content: text, action: { ...m.action, status: "done", params } });
    } catch (e: any) {
      await api2.setActionStatus(m.id, "failed", e.message);
      updateMessage(activeConversationId, m.id, { action: { ...m.action, status: "failed", note: e.message } });
      toast.error(e.message);
    }
  }

  async function formatActionResult(action: string, result: any): Promise<string> {
    // Small, local formatter mirroring the backend's actions.format_result, for results approved client-side.
    if (action === "meet.create" || action === "meet.invite") return `✅ Meeting **${result.summary}** is set for ${result.start}.` + (result.meet_link ? `

Meet link: [${result.meet_link}](${result.meet_link})` : "");
    if (action === "sheets.create") return `✅ Created your sheet: [${result.url}](${result.url})`;
    if (action === "slides.create") return `✅ Created your presentation: [${result.url}](${result.url})`;
    if (action === "gmail.send") return "✅ Email sent.";
    if (action === "gmail.draft") return "✅ Draft saved in your Gmail drafts.";
    return "✅ Done.";
  }

  const activeTitle = conversations.find((c) => c.id === activeConversationId)?.title || "New chat";

  if (locked === null) return null;
  if (locked) return <LockScreen onUnlocked={() => setLocked(false)} />;

  return (
    <div className="h-screen w-screen flex bg-canvas text-ink">
      <NavRail view={view} onChange={setView} />
      {view === "brain" && <BrainView onOpenAutoLearn={() => setAutoLearnOpen(true)} />}
      {view === "training" && <TrainingView />}
      {view === "models" && <ModelsView />}
      {view === "google" && <GoogleView />}
      {view === "mcp" && <McpView />}
      {view === "teacher" && <TeacherView />}
      {view === "chat" && (
        <AnimatePresence initial={false}>
          {sidebarOpen && (
            <motion.div
              initial={{ width: 0, opacity: 0, x: -18 }} animate={{ width: 256, opacity: 1, x: 0 }} exit={{ width: 0, opacity: 0, x: -18 }}
              transition={{ type: "spring", stiffness: 300, damping: 30, mass: .75 }}
              className="overflow-hidden flex-shrink-0 sidebar-shell"
            >
              <div className="w-64 h-full">
                <Sidebar
                  conversations={conversations}
                  onNew={newConversation}
                  onSelect={selectConversation}
                  onRename={renameConversation}
                  onDelete={deleteConversation}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      )}
      {view === "chat" && <div className="flex-1 flex flex-col min-w-0">
        <TopBar
          title={activeTitle} onOpenAutoLearn={() => setAutoLearnOpen(true)} offline={offline}
          sidebarOpen={sidebarOpen} onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        />

        <div ref={scrollRef} className="flex-1 overflow-y-auto chat-scroll">
          <div className="max-w-3xl mx-auto w-full py-4">
            {messages.length === 0 && (
              <motion.div initial={{opacity:0,y:14}} animate={{opacity:1,y:0}} className="welcome-state text-center py-16 sm:py-24 px-5">
                <motion.div animate={{y:[0,-5,0],rotate:[0,2,-2,0]}} transition={{repeat:Infinity,duration:4,ease:"easeInOut"}} className="welcome-orb"><Sparkles className="h-6 w-6"/></motion.div>
                <p className="text-xs uppercase tracking-[.22em] text-accent mb-3">Local personal intelligence</p>
                <h2 className="text-3xl sm:text-4xl font-serif font-light text-ink">Hello. I’m {aiName}.</h2>
                <p className="text-sm text-muted mt-3 max-w-xl mx-auto">Ask naturally. I can use your local Brain offline, reason with your selected model, or research the web when you explicitly enable Search.</p>
                <div className="welcome-pills">
                  <span><Brain className="h-3.5 w-3.5"/>Offline Brain</span><span><Search className="h-3.5 w-3.5"/>Optional research</span><span><GraduationCap className="h-3.5 w-3.5"/>Trusted learning</span>
                </div>
              </motion.div>
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
                onSpeak={speak}
                onDecideAction={decideAction}
              />
            ))}
            {streaming && messages[messages.length - 1]?.role === "user" && (
              <div className="px-2 py-1"><GeneratingIndicator /></div>
            )}
          </div>
        </div>

        <div className="composer-dock px-3 sm:px-4 pb-3 sm:pb-4 pt-2 border-t border-border">
          <QueueStrip queue={messageQueue} onRemove={removeQueuedMessage} onEdit={editQueuedMessage} onForceSend={forceSendQueued} />
          <ChatComposer
            onSend={(text) => {
              if (streaming) {
                if (!enqueueMessage(text)) toast.error("Waiting list is full (5 messages) — remove one first.");
              } else {
                send(text);
              }
            }}
            disabled={false}
            streaming={streaming}
            queueFull={messageQueue.length >= 5}
            onStop={stop}
            model={model} setModel={setModel}
            reasoningLevel={reasoningLevel} setReasoningLevel={setReasoningLevel}
            searchMode={searchMode} setSearchMode={setSearchMode}
            offline={offlineMode}
            onVoice={voiceInput}
            onLiveVoice={liveVoice}
            liveVoiceState={liveVoiceState}
            aiName={voiceListening ? `${aiName} · listening` : aiName}
            skillId={skillId}
            skillName={skillName}
            onSkillChange={(id, name) => { setSkillId(id); setSkillName(name); }}
          />
        </div>
      </div>}

      <SettingsPanel />
      <Toaster />
      {autoLearnOpen && <AutoLearnModal onClose={() => setAutoLearnOpen(false)} />}
    </div>
  );
}
