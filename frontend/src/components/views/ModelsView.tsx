import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Boxes, Play, Square, FolderInput, Search, Download, KeyRound, Mic, Volume2, Loader2, Trash2, X, Check, Languages, Crown, Zap } from "lucide-react";
import { api2 } from "@/lib/api2";
import { toast } from "@/store/useToast";
import { AnimatedIcon } from "@/components/ui/AnimatedIcon";

const inp = "h-9 px-3 rounded-lg bg-surface-2 border border-border text-sm focus:outline-none focus:border-accent";
const fmtMB = (b: number) => (b > 1e9 ? `${(b / 1e9).toFixed(2)} GB` : `${(b / 1e6).toFixed(0)} MB`);

export function ModelsView() {
  const [local, setLocal] = useState<any>({ models: [], running: {}, models_dir: "" });
  const [status, setStatus] = useState<any>(null);
  const [importPath, setImportPath] = useState(""); const [mode, setMode] = useState<"link" | "copy">("link");
  const [q, setQ] = useState(""); const [results, setResults] = useState<any[]>([]); const [searching, setSearching] = useState(false);
  const [repo, setRepo] = useState<string | null>(null); const [files, setFiles] = useState<any[]>([]);
  const [downloads, setDownloads] = useState<any[]>([]);
  const [hfSet, setHfSet] = useState(false); const [token, setToken] = useState("");
  const [voice, setVoice] = useState<any>(null); const [catalog, setCatalog] = useState<any[]>([]); const [voiceFilter, setVoiceFilter] = useState("en");
  const [trStatus, setTrStatus] = useState<any>(null); const [trCatalog, setTrCatalog] = useState<any[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const poll = useRef<number | null>(null);
  const modelFile = useRef<HTMLInputElement>(null);

  const load = () => { api2.localModels().then(setLocal).catch(() => {}); api2.modelStatus().then(setStatus).catch(() => {}); };
  const loadDownloads = () => api2.downloads().then((d) => { setDownloads(d); if (d.some((x) => x.status === "running")) load(); }).catch(() => {});
  const loadVoice = () => api2.voiceStatus().then(setVoice).catch(() => {});
  const loadTranslate = () => api2.translateStatus().then(setTrStatus).catch(() => {});
  useEffect(() => { load(); loadDownloads(); loadVoice(); loadTranslate(); api2.hfTokenStatus().then((r) => setHfSet(r.set)).catch(() => {}); }, []);
  useEffect(() => {
    poll.current = window.setInterval(() => { loadDownloads(); loadVoice(); loadTranslate(); }, 1500);
    return () => { if (poll.current) clearInterval(poll.current); };
  }, []);

  const act = async (key: string, fn: () => Promise<any>, ok?: string) => {
    setBusy(key);
    try { await fn(); if (ok) toast.success(ok); load(); } catch (e: any) { toast.error(e.message); } finally { setBusy(null); }
  };
  const search = async () => { setSearching(true); setRepo(null); try { setResults(await api2.hfSearch(q)); } catch (e: any) { toast.error(e.message); } finally { setSearching(false); } };
  const openRepo = async (id: string) => { setRepo(id); setFiles([]); try { setFiles(await api2.hfFiles(id)); } catch (e: any) { toast.error(e.message); } };
  const online = (role: string) => status?.[role]?.online;
  const modelDownloadRunning = downloads.some((d:any) => d.kind === "model" && d.status === "running");

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2"><AnimatedIcon icon={Boxes} kind="float" loop className="h-5 w-5 text-accent" /> Models &amp; Voice</h1>
          <p className="text-xs text-muted mt-1">Models live in <code>{local.models_dir}</code>. The internet is only needed to download; everything runs locally afterwards.</p>
        </div>

        <Card title="Your model library">
          {(["main", "agent"] as const).map((role) => (
            <div key={role} className="flex items-center gap-3 py-2 border-b border-border last:border-0">
              <span className={`h-2 w-2 rounded-full ${online(role) ? "bg-emerald-500" : "bg-red-500"}`} />
              <div className="w-24 text-sm font-medium">{role === "main" ? "Main" : "Fast"} model</div>
              <div className="flex-1 min-w-0">
                <div className="truncate text-xs font-medium">{local.assigned?.[role] || "Not selected"}</div>
                <div className="truncate text-[10px] text-muted">{local.running?.[role]?.filename ? "Running now" : online(role) ? "External model server online" : "Stopped"}</div>
              </div>
              {local.running?.[role] && <button onClick={() => act(`un${role}`, () => api2.unloadModel(role), "Stopped")} className="text-xs flex items-center gap-1 text-red-400"><Square className="h-3 w-3" /> Stop</button>}
            </div>
          ))}
          <div className="mt-3 space-y-1.5">
            {local.models.length === 0 && <p className="text-xs text-muted">No .gguf models found yet. Import one you already have, or download from Hugging Face below.</p>}
            {local.models.map((m: any) => (
              <div key={m.filename} className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm">
                <div className="flex-1 min-w-0">
                  <div className="truncate font-medium">{m.filename}</div>
                  <div className="text-[11px] text-muted">{m.size_mb} MB{m.imported ? " · imported (in place)" : ""}</div>
                </div>
                {(["main", "agent"] as const).map((role) => {
                  const selected=local.assigned?.[role]===m.filename;
                  const key=m.filename+role;
                  return <button key={role} disabled={busy===key} onClick={() => act(key,()=>api2.loadModel(role,m.filename),`${m.filename} set as ${role==="main"?"Main":"Fast"} and started`)}
                    className={`text-xs h-8 px-2.5 rounded-md border flex items-center gap-1.5 transition-colors ${selected?"border-accent bg-accent/10 text-accent":"border-border hover:border-accent hover:text-accent"}`}>
                    {busy===key?<Loader2 className="h-3 w-3 animate-spin"/>:role==="main"?<Crown className="h-3 w-3"/>:<Zap className="h-3 w-3"/>}
                    {selected?(role==="main"?"Main selected":"Fast selected"):(role==="main"?"Set Main":"Set Fast")}
                  </button>
                })}
                {m.imported && <button title="Forget this import (file is not deleted)" onClick={() => act("rm" + m.filename, () => api2.removeImport(m.filename))} className="text-muted hover:text-red-500"><Trash2 className="h-4 w-4" /></button>}
              </div>
            ))}
          </div>
        </Card>

        <Card title="Add a model you already downloaded">
          <input ref={modelFile} type="file" accept=".gguf" className="hidden" onChange={async (e) => {
            const file = e.target.files?.[0]; e.currentTarget.value = ""; if (!file) return;
            await act("upload", async () => { await api2.uploadModel(file); load(); }, `${file.name} imported`);
          }} />
          <div className="flex gap-2 flex-wrap mb-3">
            <motion.button whileTap={{ scale: 0.96 }} disabled={busy === "upload" || modelDownloadRunning} onClick={() => modelFile.current?.click()}
              className="h-9 px-3 rounded-lg bg-accent text-white text-sm flex items-center gap-2 disabled:opacity-40">
              {busy === "upload" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FolderInput className="h-4 w-4" />} {modelDownloadRunning ? "Available after download" : "Select GGUF file"}
            </motion.button>
            <span className="text-[11px] text-muted self-center">Choose any GGUF model. After import, select it as Main or Fast from your model library above.</span>
          </div>
          <details className="text-xs text-muted">
            <summary className="cursor-pointer hover:text-ink mb-2">Advanced: import by local path</summary>
          <div className="flex gap-2 flex-wrap">
            <input className={inp + " flex-1 min-w-[220px]"} placeholder={String.raw`C:\Users\you\Downloads\model.gguf`} value={importPath} onChange={(e) => setImportPath(e.target.value)} />
            <select className={inp} value={mode} onChange={(e) => setMode(e.target.value as any)}>
              <option value="link">Use where it is (no copy)</option>
              <option value="copy">Copy into models folder</option>
            </select>
            <motion.button whileTap={{ scale: 0.96 }} disabled={!importPath.trim() || busy === "import"}
              onClick={() => act("import", async () => { await api2.importModel(importPath, mode); setImportPath(""); }, "Model imported")}
              className="h-9 px-3 rounded-lg bg-accent text-white text-sm flex items-center gap-2 disabled:opacity-40"><FolderInput className="h-4 w-4" /> Import</motion.button>
          </div>
          <p className="text-[11px] text-muted mt-2">Only real GGUF files are accepted (the file header is checked). Linked models are never moved or modified.</p>
          </details>
        </Card>

        <Card title="Download from Hugging Face">
          <div className="flex gap-2 items-center mb-3 flex-wrap">
            <KeyRound className="h-4 w-4 text-muted" />
            {hfSet ? (
              <>
                <span className="text-xs text-emerald-500 flex items-center gap-1"><Check className="h-3.5 w-3.5" /> Access token saved (encrypted, never shown again)</span>
                <button className="text-xs text-muted hover:text-red-400" onClick={() => act("hfclr", async () => { await api2.hfTokenClear(); setHfSet(false); }, "Token removed")}>Remove</button>
              </>
            ) : (
              <>
                <input type="password" className={inp + " w-64"} placeholder="Access token (hf_…) — only for private/gated models" value={token} onChange={(e) => setToken(e.target.value)} />
                <button disabled={!token} className="text-xs h-9 px-3 rounded-lg border border-border hover:border-accent"
                  onClick={() => act("hftok", async () => { await api2.hfTokenSet(token); setToken(""); setHfSet(true); }, "Token saved")}>Save token</button>
              </>
            )}
          </div>
          <div className="flex gap-2">
            <input className={inp + " flex-1"} placeholder="Search GGUF models, e.g. qwen2.5 1.5b instruct" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && q && search()} />
            <motion.button whileTap={{ scale: 0.96 }} disabled={!q || searching} onClick={search} className="h-9 px-3 rounded-lg bg-accent text-white text-sm flex items-center gap-2 disabled:opacity-40">
              {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />} Search
            </motion.button>
          </div>
          <div className="mt-3 space-y-1">
            {results.map((r) => (
              <div key={r.id}>
                <button onClick={() => openRepo(r.id)} className="w-full text-left rounded-lg border border-border px-3 py-2 text-sm hover:border-accent flex justify-between">
                  <span className="truncate">{r.id}</span><span className="text-[11px] text-muted">⬇ {r.downloads.toLocaleString()}</span>
                </button>
                <AnimatePresence initial={false}>
                  {repo === r.id && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                      <div className="pl-3 py-1 space-y-1">
                        {files.length === 0 && <p className="text-xs text-muted flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" /> Loading files…</p>}
                        {files.map((f) => (
                          <div key={f.filename} className="flex items-center gap-2 text-xs">
                            <span className="flex-1 truncate">{f.filename}</span><span className="text-muted">{f.size_mb} MB</span>
                            <button onClick={() => act("dl" + f.filename, () => api2.hfDownload(r.id, f.filename), "Download started")} className="h-7 px-2 rounded-md border border-border hover:border-accent flex items-center gap-1"><Download className="h-3 w-3" /> Get</button>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
          <DownloadList items={downloads} />
        </Card>

        <Card title="Voice (offline voice chat)">
          <p className="text-xs text-muted mb-3">Download a speech-recognition model and a voice once; after that voice chat and “Hey {"{name}"}” work with no internet. Without them the app uses your browser’s built-in voice.</p>
          {voice && (!voice.stt.library || !voice.tts.library) && <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 mb-3">
            <p className="text-xs text-amber-500 mb-2">Offline voice engine is not installed yet.</p>
            <button onClick={() => act("voicesetup", () => api2.voiceSetup(), "Offline voice installation started")}
              className="text-xs h-8 px-3 rounded-lg border border-amber-500/40 hover:bg-amber-500/10">Install offline voice engine</button>
          </div>}
          <div className="flex items-center gap-2 flex-wrap mb-3">
            <Mic className="h-4 w-4 text-muted" /><span className="text-sm">Speech recognition:</span>
            {voice && Object.keys(voice.stt.sizes_mb).filter((s) => s.endsWith(".en") || true).slice(0, 6).map((size: string) => {
              const have = voice.stt.installed.includes(size); const ins = voice.stt.installing[size];
              return (
                <button key={size} disabled={have || ins?.status === "running" || !voice.stt.library}
                  onClick={() => act("stt" + size, () => api2.installStt(size), "Downloading speech model…")}
                  className={`text-xs h-7 px-2 rounded-md border ${have ? "border-emerald-500/50 text-emerald-500" : "border-border hover:border-accent"} disabled:opacity-60`}>
                  {have ? "✓ " : ins?.status === "running" ? "… " : ""}{size} <span className="text-muted">({voice.stt.sizes_mb[size]} MB)</span>
                </button>
              );
            })}
          </div>
          {voice?.stt.installing && Object.entries(voice.stt.installing).filter(([, v]: any) => v.status === "failed").map(([k, v]: any) => <p key={k} className="text-xs text-red-400">{k}: {v.error}</p>)}
          <div className="flex items-center gap-2 mb-2"><Volume2 className="h-4 w-4 text-muted" /><span className="text-sm">Voices:</span>
            <span className="text-xs text-muted">{voice?.tts.voices.length ? voice.tts.voices.join(", ") : "none installed"}</span></div>
          {voice && !voice.tts.library && <p className="text-xs text-amber-500 mb-2">Local speech needs the <code>piper-tts</code> package (in requirements-voice.txt).</p>}
          <div className="flex gap-2 mb-2">
            <button className="text-xs h-8 px-3 rounded-lg border border-border hover:border-accent" onClick={() => act("cat", async () => setCatalog(await api2.voiceCatalog()))}>{busy === "cat" ? "Loading…" : "Browse voices"}</button>
            {catalog.length > 0 && <input className={inp + " h-8 w-28 text-xs"} value={voiceFilter} onChange={(e) => setVoiceFilter(e.target.value)} placeholder="filter: en, hi…" />}
          </div>
          <div className="max-h-48 overflow-y-auto space-y-1">
            {catalog.filter((v) => v.id.toLowerCase().includes(voiceFilter.toLowerCase())).slice(0, 60).map((v) => (
              <div key={v.id} className="flex items-center gap-2 text-xs rounded-md border border-border px-2 py-1.5">
                <span className="flex-1 truncate">{v.id}</span><span className="text-muted">{v.language}</span>
                {voice?.tts.voices.includes(v.id) ? <span className="text-emerald-500">installed</span> :
                  <button disabled={!voice?.tts.library} onClick={() => act("v" + v.id, () => api2.installVoice(v.id), "Downloading voice…")} className="h-6 px-2 rounded border border-border hover:border-accent disabled:opacity-40 flex items-center gap-1"><Download className="h-3 w-3" /> Get</button>}
              </div>
            ))}
          </div>
          <DownloadList items={downloads.filter((d) => d.kind === "voice")} />
        </Card>

        <Card title="Translate (offline, powered by Argos Translate)">
          <p className="text-xs text-muted mb-3">
            Used by the <b>Translate</b> skill in the composer — say "to French: hello" and it calls this directly, no guessing from the chat model.
            {trStatus && !trStatus.available && <> Offline translate engine is not installed yet.</>}
          </p>
          {trStatus && !trStatus.available && <button onClick={() => act("trsetup", () => api2.translateSetup(), "Offline translate installation started")}
            className="text-xs h-8 px-3 mb-3 rounded-lg border border-amber-500/40 text-amber-500 hover:bg-amber-500/10">Install offline translate engine</button>}
          <div className="flex items-center gap-2 mb-2 text-sm"><Languages className="h-4 w-4 text-muted" />
            <span className="text-muted">Installed pairs:</span>
            <span>{trStatus?.installed?.length ? trStatus.installed.map((p: any) => `${p.from_name}→${p.to_name}`).join(", ") : "none yet"}</span>
          </div>
          <button disabled={!trStatus?.available || busy === "trcat"} onClick={() => act("trcat", async () => setTrCatalog(await api2.translateCatalog()))}
            className="text-xs h-8 px-3 rounded-lg border border-border hover:border-accent disabled:opacity-40">
            {busy === "trcat" ? "Loading…" : "Browse language pairs"}
          </button>
          {trCatalog && (
            <div className="mt-2 max-h-48 overflow-y-auto space-y-1">
              {trCatalog.filter((p) => p.from_code === "en" || p.to_code === "en").map((p) => (
                <div key={`${p.from_code}-${p.to_code}`} className="flex items-center gap-2 text-xs rounded-md border border-border px-2 py-1.5">
                  <span className="flex-1">{p.from_name} → {p.to_name}</span>
                  {p.installed ? <span className="text-emerald-500">installed</span> :
                    <button onClick={() => act(`tr${p.from_code}${p.to_code}`, () => api2.translateInstall(p.from_code, p.to_code), "Downloading language pack…")}
                      className="h-6 px-2 rounded border border-border hover:border-accent flex items-center gap-1"><Download className="h-3 w-3" /> Get</button>}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function DownloadList({ items }: { items: any[] }) {
  const shown = items.filter((d) => d.status === "running" || Date.now() / 1000 - d.started_at < 3600).slice(0, 5);
  if (!shown.length) return null;
  return (
    <div className="mt-3 space-y-2">
      {shown.map((d) => {
        const pct = d.bytes_total ? Math.round((d.bytes_done / d.bytes_total) * 100) : 0;
        return (
          <div key={d.id} className="text-xs">
            <div className="flex justify-between"><span className="truncate">{d.name}</span>
              <span className="text-muted flex items-center gap-2">{d.status === "running" ? `${pct}% · ${fmtMB(d.bytes_done)}` : d.status}
                {d.status === "running" && <button onClick={() => api2.cancelDownload(d.id)}><X className="h-3 w-3" /></button>}</span></div>
            <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden mt-1">
              <motion.div className={`h-full ${d.status === "failed" ? "bg-red-500" : "bg-accent"}`} animate={{ width: `${d.status === "completed" ? 100 : pct}%` }} />
            </div>
            {d.error && <p className="text-red-400 mt-1">{d.error}</p>}
          </div>
        );
      })}
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="rounded-xl border border-border bg-surface p-4">
      <h2 className="text-sm font-medium mb-3">{title}</h2>{children}
    </motion.section>
  );
}
