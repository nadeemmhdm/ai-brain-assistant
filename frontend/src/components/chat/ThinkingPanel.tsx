import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Brain, Search, BookOpen, PenLine, Sparkles, Check, WifiOff, Globe } from "lucide-react";
import type { LiveState } from "@/store/useAppStore";

const ICON: Record<string, any> = {
  recall: BookOpen, recalled: BookOpen, searching: Search, reading: Globe, ranking: Sparkles,
  thinking: Brain, writing: PenLine, offline: WifiOff, notice: Sparkles,
};

/** The animated "Nila is thinking…" message: live steps + the model's reasoning as it streams. */
export function ThinkingPanel({ live, name }: { live?: LiveState; name: string }) {
  const [secs, setSecs] = useState(0);
  const [showReasoning, setShowReasoning] = useState(false);
  useEffect(() => {
    const t = setInterval(() => setSecs(Math.floor((Date.now() - (live?.startedAt || Date.now())) / 1000)), 500);
    return () => clearInterval(t);
  }, [live?.startedAt]);

  // keep only the latest entry per stage so the list reads as a timeline
  const stages = (live?.stages || []).reduce<typeof live extends undefined ? never[] : any[]>((acc, s) => {
    const i = acc.findIndex((x: any) => x.stage === s.stage);
    if (i >= 0) acc[i] = s; else acc.push(s);
    return acc;
  }, []);
  const current = stages[stages.length - 1];

  return (
    <div className="min-w-[240px] rounded-xl bg-surface/50 p-1">
      <div className="flex items-center gap-2 text-sm">
        <motion.span animate={{ rotate: [0, 8, -8, 0], scale: [1, 1.12, 1] }} transition={{ repeat: Infinity, duration: 2.2 }}>
          <Brain className="h-4 w-4 text-accent" />
        </motion.span>
        <span className="think-shimmer font-medium">{current?.stage === "writing" ? `${name} is composing` : `${name} is working on it`}</span>
        <span className="flex items-center gap-0.5">
          {[0, 1, 2].map((i) => <span key={i} className="think-dot h-1 w-1 rounded-full bg-accent inline-block" />)}
        </span>
        <span className="ml-auto text-[11px] text-muted tabular-nums">{secs}s</span>
      </div>

      <ul className="mt-2 space-y-1">
        <AnimatePresence initial={false}>
          {stages.filter((s: any) => s.detail).map((s: any, i: number) => {
            const Icon = ICON[s.stage] || Sparkles;
            const active = i === stages.length - 1;
            return (
              <motion.li key={s.stage} layout initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                className={`flex items-center gap-2 text-xs ${active ? "text-ink" : "text-muted"}`}>
                {active ? <Icon className="h-3.5 w-3.5 text-accent" /> : <Check className="h-3.5 w-3.5 text-emerald-500" />}
                <span>{s.detail}</span>
                {s.total ? <span className="text-[10px] text-muted">({s.done ?? 0}/{s.total})</span> : null}
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ul>

      {live?.thinking ? (
        <div className="mt-2">
          <button onClick={() => setShowReasoning((v) => !v)} className="text-[11px] text-muted hover:text-ink">
            {showReasoning ? "Hide" : "Show"} reasoning
          </button>
          <AnimatePresence initial={false}>
            {showReasoning && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden">
                <div className="mt-1 max-h-32 overflow-y-auto rounded-md border border-border bg-surface p-2 text-[11px] text-muted whitespace-pre-wrap">
                  {live.thinking}<motion.span animate={{ opacity: [1, 0, 1] }} transition={{ repeat: Infinity, duration: 1 }}>▍</motion.span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ) : null}
    </div>
  );
}
