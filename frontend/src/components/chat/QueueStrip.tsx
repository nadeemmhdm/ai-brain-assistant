import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { X, Clock, Pencil, Check, SendHorizonal } from "lucide-react";
import { MAX_QUEUED_MESSAGES } from "@/store/useAppStore";

/** The "waiting list": messages typed while a reply is still generating, sent automatically once it's done.
 * Each item can be edited, sent right now (force-send, jumping the queue), or removed. */
export function QueueStrip({
  queue, onRemove, onEdit, onForceSend,
}: {
  queue: string[];
  onRemove: (index: number) => void;
  onEdit: (index: number, text: string) => void;
  onForceSend: (index: number) => void;
}) {
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");

  if (!queue.length) return null;

  const startEdit = (i: number, text: string) => { setEditing(i); setDraft(text); };
  const saveEdit = (i: number) => { onEdit(i, draft); setEditing(null); };

  return (
    <div className="max-w-2xl mx-auto w-full px-1 pb-2">
      <div className="flex items-center gap-1.5 mb-1.5 text-[11px] text-muted">
        <Clock className="h-3 w-3" /> Waiting to send ({queue.length}/{MAX_QUEUED_MESSAGES})
      </div>
      <div className="flex flex-col gap-1.5">
        <AnimatePresence initial={false}>
          {queue.map((text, i) => (
            <motion.div
              key={i + text.slice(0, 10)}
              layout
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 12, height: 0, marginBottom: 0 }}
              transition={{ type: "spring", stiffness: 380, damping: 32 }}
              className="rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs text-muted"
            >
              {editing === i ? (
                <div className="flex items-center gap-2">
                  <span className="h-4 w-4 flex-shrink-0 rounded-full bg-surface flex items-center justify-center text-[10px] tabular-nums">{i + 1}</span>
                  <input
                    autoFocus
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") saveEdit(i);
                      if (e.key === "Escape") setEditing(null);
                    }}
                    className="flex-1 bg-transparent border-b border-border text-ink focus:outline-none py-0.5"
                  />
                  <button onClick={() => saveEdit(i)} className="text-emerald-500 hover:text-emerald-400 flex-shrink-0" title="Save">
                    <Check className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="h-4 w-4 flex-shrink-0 rounded-full bg-surface flex items-center justify-center text-[10px] tabular-nums">{i + 1}</span>
                  <span className="flex-1 truncate">{text}</span>
                  <button onClick={() => onForceSend(i)} className="text-muted hover:text-accent flex-shrink-0" title="Send now (skip the wait)">
                    <SendHorizonal className="h-3 w-3" />
                  </button>
                  <button onClick={() => startEdit(i, text)} className="text-muted hover:text-ink flex-shrink-0" title="Edit">
                    <Pencil className="h-3 w-3" />
                  </button>
                  <button onClick={() => onRemove(i)} className="text-muted hover:text-red-400 flex-shrink-0" title="Remove from waiting list">
                    <X className="h-3 w-3" />
                  </button>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
