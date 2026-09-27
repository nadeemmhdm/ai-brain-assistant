import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Copy, RotateCcw, GitFork, Trash2, Pencil, ChevronDown, ChevronUp, Eye, Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { SourcesDrawer } from "./SourcesDrawer";
import { ThinkingIndicator } from "./ThinkingIndicator";
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
}: {
  message: Message;
  isStreaming?: boolean;
  onCopy: (text: string) => void;
  onRegenerate: (m: Message) => void;
  onFork: (m: Message) => void;
  onDelete: (m: Message) => void;
  onEditResend: (m: Message, newText: string) => void;
}) {
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
    <div className={cn("group flex w-full gap-3 px-2 py-3", isUser ? "justify-end" : "justify-start")}>
      <div className={cn("max-w-[85%] sm:max-w-[70%]", isUser && "flex flex-col items-end")}>
        {!isUser && message.thinking && (
          <div className="mb-1.5">
            <button
              onClick={() => setShowThinking((v) => !v)}
              className="flex items-center gap-1 text-xs text-muted hover:text-ink"
            >
              {showThinking ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              Thought process
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
              "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
              isUser ? "bg-accent text-white" : "bg-surface-2 text-ink border border-border"
            )}
          >
            {isStreaming && !message.content ? (
              <ThinkingIndicator label={message.reasoning_level === "off" ? "Generating" : "Thinking"} />
            ) : (
              <div className="prose-chat">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              </div>
            )}
          </div>
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
    </div>
  );
}

function IconBtn({ children, onClick, title }: { children: React.ReactNode; onClick: () => void; title: string }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="h-6 w-6 flex items-center justify-center rounded-md text-muted hover:text-ink hover:bg-surface-2"
    >
      {children}
    </button>
  );
}
