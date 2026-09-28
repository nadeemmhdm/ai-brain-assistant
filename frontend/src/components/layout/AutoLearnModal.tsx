import { useEffect, useRef, useState } from "react";
import { GraduationCap, Pause, Play, Ban } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";

export function AutoLearnModal({ onClose }: { onClose: () => void }) {
  const [topic, setTopic] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<any>(null);
  const poll = useRef<number | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    poll.current = window.setInterval(async () => {
      const s = await api.learnStatus(sessionId).catch(() => null);
      if (s) setStatus(s);
      if (s && ["completed", "cancelled", "error"].includes(s.status) && poll.current) {
        clearInterval(poll.current);
      }
    }, 1000);
    return () => { if (poll.current) clearInterval(poll.current); };
  }, [sessionId]);

  const start = async () => {
    if (!topic.trim()) return;
    const { session_id } = await api.startLearn(topic.trim());
    setSessionId(session_id);
  };

  return (
    <Modal open onClose={onClose} title="Auto Learn" maxWidth="max-w-md"
      icon={<GraduationCap className="h-4 w-4 text-accent" />}>
      <div>
        {!sessionId ? (
          <>
            <p className="text-xs text-muted mb-3">
              Give the AI a topic. It will plan subtopics, research trusted sources online,
              cross-check facts, and add verified knowledge to the local AI Brain for offline use.
            </p>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Cybersecurity"
              className="w-full rounded-md bg-surface-2 border border-border px-3 py-2 text-sm mb-3 focus:outline-none focus:border-accent"
            />
            <Button onClick={start} disabled={!topic.trim()} className="w-full">Start learning</Button>
          </>
        ) : (
          <div className="space-y-3">
            <p className="text-sm font-medium">{status?.topic}</p>
            <div className="w-full h-2 rounded-full bg-surface-2 overflow-hidden">
              <div className="h-full bg-accent transition-all" style={{ width: `${status?.progress_pct ?? 0}%` }} />
            </div>
            <p className="text-xs text-muted">{status?.current_task}</p>
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <MiniStat label="Sources" value={status?.sources_found} />
              <MiniStat label="Pages" value={status?.pages_processed} />
              <MiniStat label="Knowledge" value={status?.knowledge_items} />
              <MiniStat label="Verified" value={status?.verified_items} />
              <MiniStat label="Conflicts" value={status?.conflicts} />
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
