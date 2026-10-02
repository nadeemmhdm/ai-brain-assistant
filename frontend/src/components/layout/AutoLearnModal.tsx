import { useEffect, useRef, useState } from "react";
import { GraduationCap, Pause, Play, Ban, ShieldCheck, BookOpenCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/Modal";
import { toast } from "@/store/useToast";
import { api } from "@/lib/api";

export function AutoLearnModal({ onClose }: { onClose: () => void }) {
  const [topic, setTopic] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const poll = useRef<number | null>(null);

  useEffect(() => {
    api.learnActive().then((active) => { if (active) { setSessionId(active.session_id); setStatus(active); } }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    let misses = 0;
    poll.current = window.setInterval(async () => {
      try {
        const s = await api.learnStatus(sessionId);
        misses = 0; setStatus(s);
        if (["completed", "cancelled", "error"].includes(s.status) && poll.current) {
          clearInterval(poll.current);
          window.dispatchEvent(new CustomEvent("ai-brain:learning-finished", { detail: s }));
          if (s.status === "completed") toast.success(`Saved ${s.knowledge_items} knowledge item(s) to AI Brain`);
        }
      } catch {
        if (++misses >= 3 && poll.current) { clearInterval(poll.current); setError("Lost contact with the learning session. Is the backend still running?"); }
      }
    }, 1000);
    return () => { if (poll.current) clearInterval(poll.current); };
  }, [sessionId]);

  const start = async () => {
    if (!topic.trim() || starting) return;
    setStarting(true); setError(null);
    try {
      const { session_id } = await api.startLearn(topic.trim());
      setSessionId(session_id);
    } catch (e: any) {
      const msg = e.message || "Couldn't start learning.";
      setError(msg); toast.error(msg);
    } finally {
      setStarting(false);
    }
  };

  return (
    <Modal open onClose={onClose} title="Trusted Topic Learning" maxWidth="max-w-md"
      icon={<GraduationCap className="h-4 w-4 text-accent" />}>
      <div>
        {!sessionId ? (
          <>
            <p className="text-xs text-muted mb-3">
              Give AI a topic. It researches authoritative web and scholarly sources, cross-checks
              independent evidence, and stores provenance-backed knowledge in the local AI Brain.
              Once learned, that knowledge remains available for fast offline retrieval.
            </p>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Cybersecurity"
              className="w-full rounded-md bg-surface-2 border border-border px-3 py-2 text-sm mb-3 focus:outline-none focus:border-accent"
            />
            <Button onClick={start} disabled={!topic.trim() || starting} className="w-full">
              {starting ? "Starting…" : "Research & learn"}
            </Button>
            {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
          </>
        ) : (
          <div className="space-y-3">
            <p className="text-sm font-medium">{status?.topic}</p>
            <div className="w-full h-2 rounded-full bg-surface-2 overflow-hidden">
              <div className="h-full bg-accent transition-all" style={{ width: `${status?.progress_pct ?? 0}%` }} />
            </div>
            <p className={`text-xs ${status?.status === "error" ? "text-red-500" : "text-muted"}`}>{status?.current_task}</p>
            {error && <p className="text-xs text-red-500">{error}</p>}
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <MiniStat label="Sources" value={status?.sources_found} />
              <MiniStat label="Trusted" value={status?.authoritative_sources} />
              <MiniStat label="Scholarly" value={status?.scholarly_sources} />
              <MiniStat label="Pages" value={status?.pages_processed} />
              <MiniStat label="Knowledge" value={status?.knowledge_items} />
              <MiniStat label="Verified" value={status?.verified_items} />
              <MiniStat label="Conflicts" value={status?.conflicts} />
              <MiniStat label="Fallbacks" value={status?.synthesis_fallbacks} />
              <MiniStat label="Status" value={status?.status} />
            </div>
            {status?.status === "running" && (
              <div className="flex gap-2">
                <Button size="sm" variant="outline" className="flex-1 gap-1"
                  onClick={() => api.learnControl(sessionId, "pause")}>
                  <Pause className="h-3.5 w-3.5" /> Pause
                </Button>
                <Button size="sm" variant="destructive" className="flex-1 gap-1"
                  onClick={() => api.learnControl(sessionId, "cancel")}>
                  <Ban className="h-3.5 w-3.5" /> Cancel
                </Button>
              </div>
            )}
            {status?.status === "paused" && (
              <Button size="sm" className="w-full gap-1" onClick={() => api.learnControl(sessionId, "resume")}>
                <Play className="h-3.5 w-3.5" /> Resume
              </Button>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

function MiniStat({ label, value }: { label: string; value: any }) {
  return (
    <div className="rounded-md bg-surface-2 border border-border py-1.5">
      <div className="font-medium">{value ?? "—"}</div>
      <div className="text-muted text-[10px]">{label}</div>
    </div>
  );
}
