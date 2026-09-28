import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Cpu, FileJson, Check, X, Trash2, Play, Info, Loader2, ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "@/store/useToast";

const inputCls = "w-full h-9 px-3 rounded-lg bg-surface-2 border border-border text-sm focus:outline-none focus:border-accent";

export function TrainingView() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");
  const [onlyVerified, setOnlyVerified] = useState(true);
  const [form, setForm] = useState({ dataset_id: "", base_model_path: "", output_dir: "", epochs: 3, learning_rate: 0.0002, lora_r: 8 });
  const poll = useRef<number | null>(null);

  const loadDatasets = () => api.listDatasets().then(setDatasets).catch(() => {});
  const loadJobs = () => api.listTraining().then(setJobs).catch(() => {});
  useEffect(() => { loadDatasets(); loadJobs(); }, []);

  // poll while any job is active
  useEffect(() => {
    const active = jobs.some((j) => j.status === "queued" || j.status === "running");
    if (active && !poll.current) poll.current = window.setInterval(loadJobs, 1500);
    if (!active && poll.current) { clearInterval(poll.current); poll.current = null; }
    return () => { if (poll.current) { clearInterval(poll.current); poll.current = null; } };
  }, [jobs]);

  const create = async () => {
    try {
      const r = await api.createDataset(name.trim() || `dataset-${Date.now()}`, topic.trim() || undefined, onlyVerified);
      toast.success(`Dataset created with ${r.item_count} examples`);
      setName(""); setTopic(""); loadDatasets();
    } catch (e: any) { toast.error(e.message); }
  };

  const toggleOpen = async (id: string) => {
    if (openId === id) { setOpenId(null); return; }
    setOpenId(id); setItems(await api.datasetItems(id));
  };

  const approve = async (it: any, approved: boolean) => {
    await api.approveItem(it.id, approved);
    setItems((p) => p.map((x) => (x.id === it.id ? { ...x, approved: approved ? 1 : 0 } : x)));
    loadDatasets();
  };

  const start = async () => {
    try {
      await api.startTraining(form);
      toast.info("Training job started");
      loadJobs();
    } catch (e: any) { toast.error(e.message); }
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2"><Cpu className="h-5 w-5 text-accent" /> Training</h1>
          <div className="mt-3 flex gap-2 rounded-xl border border-sky-500/30 bg-sky-500/10 p-3 text-xs">
            <Info className="h-4 w-4 text-sky-500 flex-shrink-0 mt-0.5" />
            <p>
              <b>Auto Learn does not train the model</b> — it only fills the AI Brain. This tab is the separate, explicit step
              that changes model weights (LoRA). It needs a <b>HuggingFace-format</b> base model folder (not the .gguf file) and the
              optional packages in <code>requirements-training.txt</code>. Afterwards, convert the adapter with llama.cpp to use it.
            </p>
          </div>
        </div>

        <Card title="1 · Create a dataset from the AI Brain">
          <div className="grid sm:grid-cols-3 gap-2">
            <input className={inputCls} placeholder="Dataset name" value={name} onChange={(e) => setName(e.target.value)} />
            <input className={inputCls} placeholder="Topic (optional)" value={topic} onChange={(e) => setTopic(e.target.value)} />
            <label className="flex items-center gap-2 text-xs text-muted">
              <input type="checkbox" checked={onlyVerified} onChange={(e) => setOnlyVerified(e.target.checked)} /> Verified knowledge only
            </label>
          </div>
          <Btn onClick={create} className="mt-3"><FileJson className="h-4 w-4" /> Create dataset</Btn>
        </Card>

        <Card title="2 · Review & approve examples">
          {datasets.length === 0 && <p className="text-xs text-muted">No datasets yet.</p>}
          <div className="space-y-2">
            {datasets.map((d) => (
              <div key={d.id} className="rounded-lg border border-border">
                <div className="flex items-center gap-2 px-3 py-2">
                  <button onClick={() => toggleOpen(d.id)} className="flex-1 flex items-center gap-2 text-left text-sm">
                    <motion.span animate={{ rotate: openId === d.id ? 180 : 0 }}><ChevronDown className="h-4 w-4 text-muted" /></motion.span>
                    <span className="font-medium">{d.name}</span>
                    <span className="text-xs text-muted">{d.approved_count}/{d.item_count} approved</span>
                  </button>
                  <button onClick={async () => { await api.deleteDataset(d.id); toast.success("Dataset deleted"); loadDatasets(); }}
                    className="text-muted hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
                </div>
                <AnimatePresence initial={false}>
                  {openId === d.id && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden border-t border-border">
                      <div className="max-h-72 overflow-y-auto divide-y divide-border">
                        {items.map((it) => (
                          <div key={it.id} className="flex gap-2 p-3 text-xs">
                            <div className="flex-1 min-w-0">
                              <p className="font-medium">{it.instruction}</p>
                              <p className="text-muted line-clamp-2 mt-0.5">{it.output}</p>
                            </div>
                            <button onClick={() => approve(it, !it.approved)}
                              className={`h-7 w-7 rounded-md flex items-center justify-center border ${it.approved ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-500" : "border-border text-muted"}`}>
                              {it.approved ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
                            </button>
                          </div>
                        ))}
                      </div>
                      <div className="p-2 border-t border-border text-right">
                        <a className="text-xs text-accent hover:underline" href={`${import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000"}/api/dataset/${d.id}/export.jsonl`} target="_blank" rel="noreferrer">
                          Export approved as JSONL
                        </a>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        </Card>

        <Card title="3 · Start LoRA training (explicit, optional)">
          <div className="grid sm:grid-cols-2 gap-2">
            <select className={inputCls} value={form.dataset_id} onChange={(e) => setForm({ ...form, dataset_id: e.target.value })}>
              <option value="">Select dataset…</option>
              {datasets.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.approved_count} approved)</option>)}
            </select>
            <input className={inputCls} placeholder="Base model folder (HF format)" value={form.base_model_path} onChange={(e) => setForm({ ...form, base_model_path: e.target.value })} />
            <input className={inputCls} placeholder="Output folder for adapter" value={form.output_dir} onChange={(e) => setForm({ ...form, output_dir: e.target.value })} />
            <div className="flex gap-2">
              <input className={inputCls} type="number" title="Epochs" value={form.epochs} onChange={(e) => setForm({ ...form, epochs: +e.target.value })} />
              <input className={inputCls} type="number" step="0.0001" title="Learning rate" value={form.learning_rate} onChange={(e) => setForm({ ...form, learning_rate: +e.target.value })} />
              <input className={inputCls} type="number" title="LoRA rank" value={form.lora_r} onChange={(e) => setForm({ ...form, lora_r: +e.target.value })} />
            </div>
          </div>
          <Btn onClick={start} disabled={!form.dataset_id || !form.base_model_path || !form.output_dir} className="mt-3">
            <Play className="h-4 w-4" /> Start training
          </Btn>
        </Card>

        <Card title="Training jobs">
          {jobs.length === 0 && <p className="text-xs text-muted">No training jobs yet.</p>}
          <div className="space-y-2">
            {jobs.map((j) => (
              <div key={j.id} className="rounded-lg border border-border p-3 text-xs">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-medium flex items-center gap-1.5">
                    {(j.status === "running" || j.status === "queued") && <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" />}
                    {j.status}
                  </span>
                  <span className="text-muted">{j.progress_pct}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden">
                  <motion.div className={`h-full ${j.status === "failed" ? "bg-red-500" : "bg-accent"}`}
                    animate={{ width: `${j.progress_pct}%` }} transition={{ type: "spring", stiffness: 120, damping: 20 }} />
                </div>
                <p className="text-muted mt-1.5">{j.current_step}</p>
                {j.error && <pre className="mt-2 whitespace-pre-wrap text-red-500 max-h-32 overflow-auto">{j.error}</pre>}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="rounded-xl border border-border bg-surface p-4">
      <h2 className="text-sm font-medium mb-3">{title}</h2>
      {children}
    </motion.section>
  );
}
function Btn({ children, className = "", ...p }: any) {
  return (
    <motion.button whileTap={{ scale: 0.96 }} {...p}
      className={`h-9 px-3 rounded-lg bg-accent text-white text-sm font-medium flex items-center gap-2 disabled:opacity-40 ${className}`}>
      {children}
    </motion.button>
  );
}
