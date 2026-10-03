import { useState } from "react";
import { motion } from "motion/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Copy, RotateCcw, GitFork, Trash2, Pencil, ChevronDown, ChevronUp, Eye, Check, Volume2, ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { SourcesDrawer } from "./SourcesDrawer";
import { ThinkingPanel } from "./ThinkingPanel";
import { ActionCard } from "./ActionCard";
import { useAppStore } from "@/store/useAppStore";
import type { Message } from "@/lib/api";
import { cn } from "@/lib/utils";

export function MessageBubble({
  message,
  isStreaming,
  onCopy,
  onRegenerate,
  onFork,
  onDelete,
  onEditResend,
  onSpeak,
  onDecideAction,
}: {
  message: Message;
  isStreaming?: boolean;
  onCopy: (text: string) => void;
  onRegenerate: (m: Message) => void;
  onFork: (m: Message) => void;
  onDelete: (m: Message) => void;
  onEditResend: (m: Message, newText: string) => void;
  onSpeak?: (m: Message) => void;
  onDecideAction?: (m: Message, grant: "once" | "chat" | "always" | "deny", params: Record<string, any>) => Promise<void> | void;
}) {
  const live = useAppStore((st) => st.live[message.id]);
  const aiName = useAppStore((st) => st.aiName);
  const [showThinking, setShowThinking] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.content);
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const copy = () => {
    onCopy(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: .985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 320, damping: 28 }}
      className={cn("group flex w-full gap-3 px-3 sm:px-4 py-3.5", isUser ? "justify-end" : "justify-start")}
    >
      <div className={cn("max-w-[92%] sm:max-w-[78%]", isUser && "flex flex-col items-end")}>
        {!isUser && isStreaming && message.content && live?.thinking && (
          <div className="mb-1 text-[11px] text-muted italic">{aiName} has been working for {Math.max(1, Math.round((Date.now() - live.startedAt) / 1000))}s…</div>
        )}
        {!isUser && message.thinking && (
          <div className="mb-1.5">
            <button
              onClick={() => setShowThinking((v) => !v)}
              className="flex items-center gap-1 text-xs text-muted hover:text-ink"
            >
              {showThinking ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              Model activity
            </button>
            {showThinking && (
              <div className="mt-1 rounded-md border border-border bg-surface-2 p-2.5 text-xs text-muted whitespace-pre-wrap">
                {message.thinking}
              </div>
            )}
          </div>
        )}

        {editing ? (
          <div className="w-full rounded-xl border border-border bg-surface-2 p-2">
            <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} className="text-sm" />
            <div className="flex justify-end gap-2 mt-1">
              <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
              <Button size="sm" onClick={() => { setEditing(false); onEditResend(message, draft); }}>
                Save &amp; resend
              </Button>
            </div>
          </div>
        ) : (
          <div
            className={cn(
              "message-surface rounded-2xl px-4 py-3 text-sm leading-relaxed",
              isUser ? "user-message bg-accent text-white" : "assistant-message bg-surface-2 text-ink border border-border"
            )}
          >
            {isStreaming && !message.content ? (
              <ThinkingPanel live={live} name={aiName} />
            ) : !message.content?.trim() ? (
              <div className="text-muted text-xs italic py-1">No visible response was received. Regenerate this message to retry.</div>
            ) : (
              <div className="prose-chat text-ink">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                  a: ({ href, children }) => (
                    <a href={href} target="_blank" rel="noopener noreferrer" className="text-accent underline underline-offset-2 hover:opacity-80 break-all">{children}</a>
                  ),
                }}>{message.content}</ReactMarkdown>
              </div>
            )}
          </div>
        )}

        {!isUser && message.confidence && (
          <span title={`${message.confidence.sources} source(s) from ${message.confidence.domains} site(s). ${message.confidence.basis || "Evidence-based estimate; not a guarantee of correctness."}`}
            className="mt-1.5 mr-2 inline-flex items-center gap-1 text-[11px] rounded-full px-2 py-0.5 border border-border text-muted">
            <ShieldCheck className="h-3 w-3" /> {Math.max(0, Math.min(100, message.confidence.percent ?? 0))}% · {confidenceGrade(message.confidence.percent ?? 0)}
          </span>
        )}
        {!isUser && message.action && onDecideAction && (
          <ActionCard action={message.action} onDecide={(g, p) => onDecideAction(message, g, p)} />
        )}
        {!isUser && message.sources && message.sources.length > 0 && (
          <button
            onClick={() => setShowSources(true)}
            className="mt-1.5 inline-flex items-center gap-1 text-xs text-muted hover:text-accent"
          >
            <Eye className="h-3.5 w-3.5" /> View sources ({message.sources.length})
          </button>
        )}

        <div className={cn(
          "flex items-center gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity",
          isUser && "flex-row-reverse"
        )}>
          <IconBtn title="Copy" onClick={copy}>
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
          </IconBtn>
          {!isUser && onSpeak && (
            <IconBtn title="Read aloud" onClick={() => onSpeak(message)}>
              <Volume2 className="h-3.5 w-3.5" />
            </IconBtn>
          )}
          {!isUser && (
            <IconBtn title="Regenerate" onClick={() => onRegenerate(message)}>
              <RotateCcw className="h-3.5 w-3.5" />
            </IconBtn>
          )}
          <IconBtn title="Fork from here" onClick={() => onFork(message)}>
            <GitFork className="h-3.5 w-3.5" />
          </IconBtn>
          {isUser && (
            <IconBtn title="Edit &amp; resend" onClick={() => setEditing(true)}>
              <Pencil className="h-3.5 w-3.5" />
            </IconBtn>
          )}
          <IconBtn title="Delete" onClick={() => onDelete(message)}>
            <Trash2 className="h-3.5 w-3.5" />
          </IconBtn>
        </div>
      </div>

      {showSources && message.sources && (
        <SourcesDrawer sources={message.sources} onClose={() => setShowSources(false)} />
      )}
    </motion.div>
  );
}

function IconBtn({ children, onClick, title }: { children: React.ReactNode; onClick: () => void; title: string }) {
  return (
    <motion.button
      whileTap={{ scale: 0.85 }} whileHover={{ scale: 1.1 }}
      onClick={onClick}
      title={title}
      className="h-6 w-6 flex items-center justify-center rounded-md text-muted hover:text-ink hover:bg-surface-2"
    >
      {children}
    </motion.button>
  );
}
\nfunction confidenceGrade(p:number){return p>=85?"A":p>=70?"B":p>=50?"C":"D"}\n