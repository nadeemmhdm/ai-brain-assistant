import { useState } from "react";
import { motion } from "motion/react";
import { ShieldQuestion, Mail, Video, Table, Presentation, Check, X, Loader2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ActionProposal } from "@/lib/api";

const ICON = (a: string) => a.startsWith("gmail") ? Mail : a.startsWith("meet") ? Video : a.startsWith("sheets") ? Table : Presentation;
const RISK: Record<string, { text: string; cls: string }> = {
  read: { text: "Reads your data", cls: "text-sky-500" },
  write: { text: "Creates something in your Google account", cls: "text-amber-500" },
  external: { text: "Visible to other people", cls: "text-orange-500" },
  destructive: { text: "Removes data", cls: "text-red-500" },
};

/** Permission prompt: Allow this time · Allow this chat · Always allow · Deny */
export function ActionCard({ action, onDecide }: {
  action: ActionProposal;
  onDecide: (grant: "once" | "chat" | "always" | "deny", editedParams: Record<string, any>) => Promise<void> | void;
}) {
  const [params, setParams] = useState<Record<string, any>>(action.params || {});
  const [busy, setBusy] = useState(false);
  const Icon = ICON(action.action);
  const risk = RISK[action.risk];
  const pending = action.status === "pending";
  const set = (k: string, v: any) => setParams((p) => ({ ...p, [k]: v }));
  const decide = async (g: "once" | "chat" | "always" | "deny") => { setBusy(true); try { await onDecide(g, params); } finally { setBusy(false); } };

  const field = "w-full rounded-md bg-surface border border-border px-2 py-1.5 text-xs focus:outline-none focus:border-accent";
  return (
    <motion.div initial={{ opacity: 0, y: 8, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
      className="mt-2 rounded-xl border border-accent/40 bg-surface p-3 text-xs w-full max-w-md">
      <div className="flex items-center gap-2 mb-2">
        <ShieldQuestion className="h-4 w-4 text-accent" />
        <span className="font-medium text-sm">{action.label}</span>
        <Icon className="h-4 w-4 text-muted ml-auto" />
      </div>
      <p className={`flex items-center gap-1 mb-2 ${risk.cls}`}>
        {action.risk !== "read" && <AlertTriangle className="h-3 w-3" />}{risk.text}
      </p>

      {pending && (
        <div className="space-y-1.5 mb-3">
          {"to" in params && <input className={field} value={Array.isArray(params.to) ? params.to.join(", ") : params.to || ""} onChange={(e) => set("to", e.target.value)} placeholder="To" />}
          {"subject" in params && <input className={field} value={params.subject || ""} onChange={(e) => set("subject", e.target.value)} placeholder="Subject" />}
          {"body" in params && <textarea className={field + " min-h-[90px]"} value={params.body || ""} onChange={(e) => set("body", e.target.value)} />}
          {"summary" in params && <input className={field} value={params.summary || ""} onChange={(e) => set("summary", e.target.value)} placeholder="Meeting title" />}
          {"start" in params && <p className="text-muted">When: {params.start ? new Date(params.start).toLocaleString() : "right now"} · {params.minutes || 60} min</p>}
          {Array.isArray(params.attendees) && params.attendees.length > 0 && <p className="text-muted">Invites: {params.attendees.join(", ")}</p>}
          {"title" in params && !("slides" in params) && <input className={field} value={params.title || ""} onChange={(e) => set("title", e.target.value)} placeholder="Title" />}
          {Array.isArray(params.slides) && params.slides.length > 0 && (
            <ul className="list-disc pl-4 text-muted">{params.slides.map((s: any, i: number) => <li key={i}>{s.title}</li>)}</ul>
          )}
        </div>
      )}

      {pending ? (
        <div className="grid grid-cols-2 gap-1.5">
          <Button size="sm" disabled={busy} onClick={() => decide("once")}>{busy ? <Loader2 className="h-3 w-3 animate-spin" /> : "Allow this time"}</Button>
          <Button size="sm" variant="outline" disabled={busy} onClick={() => decide("chat")}>Allow this chat</Button>
          <Button size="sm" variant="outline" disabled={busy} onClick={() => decide("always")}>Always allow</Button>
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => decide("deny")}>Deny</Button>
        </div>
      ) : (
        <p className={`flex items-center gap-1 font-medium ${action.status === "done" ? "text-emerald-500" : action.status === "denied" ? "text-muted" : "text-red-500"}`}>
          {action.status === "done" ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}
          {action.status === "done" ? "Done" : action.status === "denied" ? "Denied" : `Failed${action.note ? `: ${action.note}` : ""}`}
        </p>
      )}
    </motion.div>
  );
}
