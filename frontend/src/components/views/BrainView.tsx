import { useEffect, useState } from "react";
import { motion, AnimatePresence, type Variants } from "motion/react";
import { Database, Search, Trash2, ShieldCheck, AlertTriangle, BookOpen, Link2, Layers } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "@/store/useToast";

const container: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.06 } } };
const item: Variants = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 26 } } };

export function BrainView({ onOpenAutoLearn }: { onOpenAutoLearn: () => void }) {
  const [stats, setStats] = useState<any>(null);
  const [topics, setTopics] = useState<any[]>([]);
  const [topic, setTopic] = useState<string>("");
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);

  const load = () => {
    api.brainStats().then(setStats).catch(() => {});
    api.brainTopics().then(setTopics).catch(() => {});
    api.brainSessions().then(setSessions).catch(() => {});
  };
  useEffect(() => {
    load();
    const refresh = () => {
      load();
      api.brainKnowledge(query, topic || undefined).then(setItems).catch(() => {});
    };
    window.addEventListener("ai-brain:learning-finished", refresh);
    return () => window.removeEventListener("ai-brain:learning-finished", refresh);
  }, []);
  useEffect(() => {
    const t = setTimeout(() => api.brainKnowledge(query, topic || undefined).then(setItems).catch(() => {}), 200);
    return () => clearTimeout(t);
  }, [query, topic]);

  const del = async (id: string) => {
    await api.deleteKnowledge(id);
    setItems((p) => p.filter((i) => i.id !== id));
    toast.success("Knowledge item deleted");
    load();
  };

  const cards = stats ? [
    { label: "Topics", value: stats.total_topics, icon: Layers },
    { label: "Knowledge items", value: stats.total_knowledge_items, icon: BookOpen },
    { label: "Verified", value: stats.verified_knowledge, icon: ShieldCheck },
    { label: "Conflicts", value: stats.conflicting_knowledge, icon: AlertTriangle },
    { label: "Sources", value: stats.total_sources, icon: Link2 },
  ] : [];

  return (
    <div className="flex-1 overflow-y-auto">
      <motion.div variants={container} initial="hidden" animate="show" className="max-w-4xl mx-auto p-6 space-y-6">
        <motion.div variants={item} className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold flex items-center gap-2"><Database className="h-5 w-5 text-accent" /> AI Brain</h1>
            <p className="text-xs text-muted mt-1">
              Everything learned lives here, on your machine. Embeddings: {stats?.embedding_backend ?? "…"}
            </p>
          </div>
          <motion.button whileTap={{ scale: 0.96 }} whileHover={{ scale: 1.02 }} onClick={onOpenAutoLearn}
            className="h-9 px-3 rounded-lg bg-accent text-white text-sm font-medium">Learn a topic</motion.button>
        </motion.div>

        <motion.div variants={item} className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {cards.map((c) => (
            <motion.div key={c.label} whileHover={{ y: -2 }} className="rounded-xl border border-border bg-surface p-3">
              <c.icon className="h-4 w-4 text-accent mb-2" />
              <div className="text-2xl font-semibold tabular-nums">{c.value}</div>
              <div className="text-[11px] text-muted">{c.label}</div>
            </motion.div>
          ))}
        </motion.div>

        <motion.div variants={item} className="flex gap-2 flex-wrap">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="h-4 w-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search what the AI has learned…"
              className="w-full h-10 pl-9 pr-3 rounded-lg bg-surface border border-border text-sm focus:outline-none focus:border-accent" />
          </div>
          <select value={topic} onChange={(e) => setTopic(e.target.value)}
            className="h-10 px-3 rounded-lg bg-surface border border-border text-sm">
            <option value="">All topics</option>
            {topics.map((t) => <option key={t.topic} value={t.topic}>{t.topic} ({t.items})</option>)}
          </select>
        </motion.div>

        <motion.div variants={item} className="space-y-2">
          <AnimatePresence initial={false}>
            {items.map((k) => (
              <motion.div key={k.id} layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0, marginTop: 0 }} className="group rounded-xl border border-border bg-surface p-3">
                <div className="flex items-start gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-2 text-muted">{k.topic}{k.subtopic ? ` › ${k.subtopic}` : ""}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        k.verification_status === "verified" ? "bg-emerald-500/15 text-emerald-500"
                        : k.verification_status === "conflict" ? "bg-amber-500/15 text-amber-500" : "bg-surface-2 text-muted"}`}>
                        {k.verification_status}
                      </span>
                    </div>
                    <p className="text-sm font-medium">{k.question}</p>
                    <p className="text-xs text-muted mt-1 line-clamp-3">{k.answer || k.summary}</p>
                  </div>
                  <button onClick={() => del(k.id)} title="Delete"
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-muted hover:text-red-500">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {items.length === 0 && (
            <div className="text-center py-12 text-sm text-muted">
              Nothing learned yet. Hit “Learn a topic” to build the AI Brain from trusted sources.
            </div>
          )}
        </motion.div>

        {sessions.length > 0 && (
          <motion.div variants={item}>
            <h2 className="text-sm font-medium mb-2">Learning history</h2>
            <div className="space-y-1.5">
              {sessions.slice(0, 8).map((s) => (
                <div key={s.id} className="flex items-center justify-between text-xs rounded-lg border border-border bg-surface px-3 py-2">
                  <span className="font-medium">{s.topic}</span>
                  <span className="text-muted">{s.stats?.knowledge_items ?? 0} items · {s.status} · {new Date(s.started_at * 1000).toLocaleDateString()}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}
