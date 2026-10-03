import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Cpu, FileJson, Check, X, Trash2, Play, Info, Loader2, ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import { api2 } from "@/lib/api2";
import { toast } from "@/store/useToast";

const inputCls = "w-full h-9 px-3 rounded-lg bg-surface-2 border border-border text-sm focus:outline-none focus:border-accent";

export function TrainingView() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [trainModels, setTrainModels] = useState<any[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");
  const [onlyVerified, setOnlyVerified] = useState(true);
  const [form, setForm] = useState({ dataset_id: "", base_model_path: "", output_dir: "", epochs: 3, learning_rate: 0.0002, lora_r: 8, training_mode: "local" });
  const poll = useRef<number | null>(null);
  const [cloud, setCloud] = useState<any>({ active_provider: null, providers: [] });
  const [cloudForm, setCloudForm] = useState({ provider: "openai", model: "", base_url: "", api_key: "", active: true });
  const [distillId, setDistillId] = useState("");
  const loadCloud = () => api2.cloudTrainingProviders().then(setCloud).catch(() => {});

  const loadDatasets = () => api.listDatasets().then(setDatasets).catch(() => {});
  const loadJobs = () => api.listTraining().then(setJobs).catch(() => {});
  const loadTrainModels = () => api.trainingModels().then(setTrainModels).catch(() => setTrainModels([]));
  useEffect(() => { loadDatasets(); loadJobs(); loadCloud(); loadTrainModels(); }, []);

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
    try {
      await api.approveItem(it.id, approved);
      setItems((p) => p.map((x) => (x.id === it.id ? { ...x, approved: approved ? 1 : 0 } : x)));
      await loadDatasets();
    } catch(e:any) { toast.error(e.message); }
  };
  const approveAll = async (approved:boolean) => {
    try {
      await Promise.all(items.map(it=>api.approveItem(it.id,approved)));
      setItems(p=>p.map(x=>({...x,approved:approved?1:0})));
      await loadDatasets();
      toast.success(approved?"All examples approved":"All examples unapproved");
    } catch(e:any){toast.error(e.message)}
  };

  const start = async () => {
    try {
      if (form.training_mode === "cloud_assisted") toast.info("Cloud teacher is refining a protected copy of the approved dataset…");
      const r = await api.startTraining(form);
      toast.info(r.training_mode === "cloud_assisted" ? `Cloud-refined dataset ready · local LoRA training started` : "Local training job started");
      if (r.cloud_refinement) { await loadDatasets(); setForm((x) => ({ ...x, dataset_id: r.dataset_id })); }
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
                      <div className="p-2 border-t border-border flex items-center justify-between gap-2">
                        <div className="flex gap-2"><button onClick={()=>void approveAll(true)} className="text-xs text-emerald-500 hover:underline">Approve all</button><button onClick={()=>void approveAll(false)} className="text-xs text-muted hover:underline">Unapprove all</button></div>
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

        <Card title="3 · Configure cloud teacher (optional)">
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-muted mb-3">
            Cloud mode sends only approved examples from the dataset you explicitly select. Chat history, Memory, the full Brain database and local files are never attached. API keys are encrypted locally and are never shown again.
          </div>
          <div className="grid sm:grid-cols-2 gap-2">
            <select className={inputCls} value={cloudForm.provider} onChange={(e) => setCloudForm({ ...cloudForm, provider: e.target.value })}>
              <option value="openai">OpenAI API</option><option value="ollama_cloud">Ollama Cloud</option><option value="compatible">OpenAI-compatible Cloud</option>
            </select>
            <input className={inputCls} type="password" autoComplete="off" placeholder="API key (stored encrypted)" value={cloudForm.api_key} onChange={(e) => setCloudForm({ ...cloudForm, api_key: e.target.value })} />
            <input className={inputCls} placeholder="Model (leave blank for default)" value={cloudForm.model} onChange={(e) => setCloudForm({ ...cloudForm, model: e.target.value })} />
            <input className={inputCls} placeholder={cloudForm.provider === "compatible" ? "https://provider.example/v1" : "Base URL (default recommended)"} value={cloudForm.base_url} onChange={(e) => setCloudForm({ ...cloudForm, base_url: e.target.value })} />
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            <Btn onClick={async()=>{try{await api2.cloudTrainingConfigure(cloudForm);setCloudForm({...cloudForm,api_key:""});await loadCloud();toast.success("Cloud training provider saved");}catch(e:any){toast.error(e.message)}}}>Save & activate</Btn>
            <span className="text-xs text-muted self-center">Active: {cloud.active_provider || "none"} · only one provider can be active</span>
          </div>
          <div className="grid sm:grid-cols-[1fr_auto] gap-2 mt-4">
            <select className={inputCls} value={distillId} onChange={(e)=>setDistillId(e.target.value)}><option value="">Select approved dataset…</option>{datasets.map((d)=><option key={d.id} value={d.id}>{d.name} ({d.approved_count} approved)</option>)}</select>
            <Btn disabled={!distillId || !cloud.active_provider} onClick={async()=>{try{toast.info("Cloud teacher started — only selected approved examples are sent");const r=await api2.cloudTrainingDistill(distillId);toast.success(`${r.refined_items} examples refined and stored locally`);if(openId===distillId)setItems(await api.datasetItems(distillId));}catch(e:any){toast.error(e.message)}}}>Refine locally stored dataset</Btn>
          </div>
        </Card>

        <Card title="4 · Choose training method & start">
          <div className="grid sm:grid-cols-2 gap-2 mb-3">
            <button onClick={() => setForm({ ...form, training_mode: "local" })}
              className={`text-left rounded-xl border p-3 transition-colors ${form.training_mode === "local" ? "border-accent bg-accent/10" : "border-border"}`}>
              <div className="text-sm font-medium">Local only</div>
              <div className="text-[11px] text-muted mt-1">Train directly from the approved local dataset. No cloud API calls.</div>
            </button>
            <button onClick={() => setForm({ ...form, training_mode: "cloud_assisted" })} disabled={!cloud.active_provider}
              className={`text-left rounded-xl border p-3 transition-colors disabled:opacity-40 ${form.training_mode === "cloud_assisted" ? "border-accent bg-accent/10" : "border-border"}`}>
              <div className="text-sm font-medium">Cloud-assisted + local LoRA</div>
              <div className="text-[11px] text-muted mt-1">Teacher: {cloud.active_provider || "configure a provider first"}. Refines a copy, then automatically starts local training.</div>
            </button>
          </div>
          {form.training_mode === "cloud_assisted" && <div className="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-muted">
            Only approved examples in the selected dataset are sent to <b>{cloud.active_provider}</b>. Your original reviewed dataset is preserved. A derived “cloud refined” dataset is stored locally and that copy is used for LoRA training.
          </div>}
          <div className="grid sm:grid-cols-2 gap-2">
            <select className={inputCls} value={form.dataset_id} onChange={(e) => setForm({ ...form, dataset_id: e.target.value })}>
              <option value="">Select dataset…</option>
              {datasets.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.approved_count} approved)</option>)}
            </select>
            <select className={inputCls} value={form.base_model_path} onChange={(e)=>setForm({...form,base_model_path:e.target.value})}>
              <option value="">Choose training model…</option>
              {trainModels.map((m)=><option key={m.path} value={m.path}>{m.name}</option>)}
            </select>
            <input className={inputCls} placeholder="Output folder for LoRA adapter" value={form.output_dir} onChange={(e) => setForm({ ...form, output_dir: e.target.value })} />
            <div className="flex gap-2">
              <input className={inputCls} type="number" title="Epochs" value={form.epochs} onChange={(e) => setForm({ ...form, epochs: +e.target.value })} />
              <input className={inputCls} type="number" step="0.0001" title="Learning rate" value={form.learning_rate} onChange={(e) => setForm({ ...form, learning_rate: +e.target.value })} />
              <input className={inputCls} type="number" title="LoRA rank" value={form.lora_r} onChange={(e) => setForm({ ...form, lora_r: +e.target.value })} />
            </div>
          </div>
          {trainModels.length===0&&<div className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2 text-[11px] text-muted">No trainable HuggingFace checkpoint found. GGUF chat models cannot be LoRA-trained directly. Put an HF-format model folder (config.json + model weights) in your Models folder or the adjacent training-models folder, then reopen Training.</div>}
          <Btn onClick={start} disabled={!form.dataset_id || !form.base_model_path || !form.output_dir || !(datasets.find(d=>d.id===form.dataset_id)?.approved_count>0)} className="mt-3">
            <Play className="h-4 w-4" /> {form.training_mode === "cloud_assisted" ? "Refine with API & start local training" : "Start local training"}
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
