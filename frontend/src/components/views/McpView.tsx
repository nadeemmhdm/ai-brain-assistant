import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Plug, Play, Square, Trash2, Wrench, Plus, ShieldCheck, Loader2, ChevronDown } from "lucide-react";
import { api2 } from "@/lib/api2";
import { useAppStore } from "@/store/useAppStore";
import { toast } from "@/store/useToast";
import { PermissionDialog, type Grant } from "@/components/ui/PermissionDialog";
import { AnimatedIcon } from "@/components/ui/AnimatedIcon";

const inp = "w-full h-9 px-3 rounded-lg bg-surface-2 border border-border text-sm focus:outline-none focus:border-accent";

export function McpView() {
  const convId = useAppStore((s) => s.activeConversationId);
  const [catalog, setCatalog] = useState<any[]>([]);
  const [servers, setServers] = useState<any[]>([]);
  const [paths, setPaths] = useState<Record<string, string>>({});
  const [open, setOpen] = useState<string | null>(null);
  const [tools, setTools] = useState<Record<string, any[]>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [custom, setCustom] = useState(false);
  const [cf, setCf] = useState({ name: "", command: "", args: "" });
  const [req, setReq] = useState<{ sid: string; tool: string; args: any; label: string; resolve: (g: Grant | null) => void } | null>(null);
  const poll = useRef<number | null>(null);

  const load = () => { api2.mcpCatalog().then(setCatalog).catch(() => {}); api2.mcpServers().then(setServers).catch(() => {}); };
  useEffect(() => { load(); poll.current = window.setInterval(load, 4000); return () => { if (poll.current) clearInterval(poll.current); }; }, []);

  const act = async (key: string, fn: () => Promise<any>, ok?: string) => {
    setBusy(key);
    try { await fn(); if (ok) toast.success(ok); load(); } catch (e: any) { toast.error(e.message); } finally { setBusy(null); }
  };

  const toggleOpen = async (sid: string) => {
    if (open === sid) { setOpen(null); return; }
    setOpen(sid);
    if (!tools[sid]) { try { setTools((t) => ({ ...t, [sid]: [] })); const r = await api2.mcpTools(sid); setTools((t) => ({ ...t, [sid]: r })); } catch (e: any) { toast.error(e.message); } }
  };

  const callTool = async (sid: string, tool: any, argsText: string) => {
    let args: any = {};
    try { args = argsText.trim() ? JSON.parse(argsText) : {}; } catch { toast.error("Arguments must be valid JSON"); return; }
    const grant = await new Promise<Grant | null>((resolve) => setReq({ sid, tool: tool.name, args, label: tool.name, resolve }));
    setReq(null);
    if (!grant) return;
    try {
      const r = await api2.mcpCall(sid, tool.name, args, grant, convId);
      toast.success("Tool ran"); return r.result;
    } catch (e: any) { toast.error(e.message); }
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2"><AnimatedIcon icon={Plug} kind="wiggle" loop className="h-5 w-5 text-accent" /> MCP Connectors</h1>
          <p className="text-xs text-muted mt-1">Trusted, official local tool servers. Each runs as its own process on your machine; every tool call still asks your permission.</p>
          <p className="text-[11px] text-muted mt-1">Needs Node.js (for <code>npx</code>) to launch the official servers below.</p>
        </div>

        <Card title="Trusted catalog">
          <div className="grid sm:grid-cols-2 gap-3">
            {catalog.map((c) => (
              <div key={c.key} className="rounded-lg border border-border p-3">
                <div className="flex items-center gap-2 mb-1"><ShieldCheck className="h-3.5 w-3.5 text-emerald-500" /><span className="text-sm font-medium">{c.name}</span></div>
                <p className="text-xs text-muted mb-2">{c.description}</p>
                {c.installed ? <span className="text-xs text-emerald-500">Installed</span> : (
                  <div className="flex gap-2">
                    {c.needs_path && <input className={inp + " h-8 text-xs"} placeholder="Folder path" value={paths[c.key] || ""} onChange={(e) => setPaths({ ...paths, [c.key]: e.target.value })} />}
                    <button disabled={busy === c.key || (c.needs_path && !paths[c.key])} onClick={() => act(c.key, () => api2.mcpInstall(c.key, paths[c.key]), `${c.name} installed`)}
                      className="h-8 px-3 rounded-md bg-accent text-white text-xs flex items-center gap-1 disabled:opacity-40 flex-shrink-0">
                      {busy === c.key ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />} Install
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>

        <Card title="Installed servers">
          {servers.length === 0 && <p className="text-xs text-muted">Nothing installed yet.</p>}
          <div className="space-y-2">
            {servers.map((s) => (
              <div key={s.id} className="rounded-lg border border-border">
                <div className="flex items-center gap-2 px-3 py-2">
                  <button onClick={() => toggleOpen(s.id)} className="flex-1 flex items-center gap-2 text-left text-sm">
                    <motion.span animate={{ rotate: open === s.id ? 180 : 0 }}><ChevronDown className="h-4 w-4 text-muted" /></motion.span>
                    <span className={`h-1.5 w-1.5 rounded-full ${s.running ? "bg-emerald-500" : "bg-muted"}`} />
                    <span className="font-medium">{s.name}</span>
                    {s.trusted && <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />}
                    <span className="text-xs text-muted">{s.running ? `${s.tool_count} tools` : "stopped"}</span>
                  </button>
                  {s.running
                    ? <button disabled={busy === "stop" + s.id} onClick={() => act("stop" + s.id, () => api2.mcpStop(s.id))} className="text-xs text-muted hover:text-ink flex items-center gap-1"><Square className="h-3.5 w-3.5" /></button>
                    : <button disabled={busy === "start" + s.id} onClick={() => act("start" + s.id, () => api2.mcpStart(s.id), "Started")} className="text-xs text-muted hover:text-accent flex items-center gap-1">{busy === "start" + s.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}</button>}
                  <button onClick={() => act("rm" + s.id, () => api2.mcpRemove(s.id), "Removed")} className="text-muted hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
                </div>
                <AnimatePresence initial={false}>
                  {open === s.id && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden border-t border-border">
                      <div className="p-3 space-y-2">
                        {(tools[s.id] || []).length === 0 && <p className="text-xs text-muted flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" /> Loading tools…</p>}
                        {(tools[s.id] || []).map((t) => <ToolRow key={t.name} tool={t} onCall={(args) => callTool(s.id, t, args)} />)}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Add a custom server">
          {!custom ? <button onClick={() => setCustom(true)} className="text-xs h-8 px-3 rounded-lg border border-border hover:border-accent flex items-center gap-1"><Plus className="h-3.5 w-3.5" /> Add custom (not pre-vetted)</button> : (
            <div className="space-y-2">
              <p className="text-[11px] text-amber-500">Only add servers you trust — they run as a local process with your permission on each tool call.</p>
              <input className={inp} placeholder="Name" value={cf.name} onChange={(e) => setCf({ ...cf, name: e.target.value })} />
              <input className={inp} placeholder="npm package (@scope/name) or local command" value={cf.command} onChange={(e) => setCf({ ...cf, command: e.target.value })} />
              <input className={inp} placeholder="Extra args (space separated, optional)" value={cf.args} onChange={(e) => setCf({ ...cf, args: e.target.value })} />
              <button disabled={!cf.name || !cf.command} onClick={() => act("custom", async () => { await api2.mcpInstallCustom(cf.name, cf.command, cf.args.split(" ").filter(Boolean)); setCustom(false); setCf({ name: "", command: "", args: "" }); }, "Added")}
                className="h-8 px-3 rounded-lg bg-accent text-white text-xs">Add</button>
            </div>
          )}
        </Card>
      </div>
      <PermissionDialog req={req ? { label: `Run tool "${req.label}"`, risk: "write", summary: JSON.stringify(req.args, null, 2) } : null}
        onChoose={(g) => req?.resolve(g)} onCancel={() => req?.resolve(null)} />
    </div>
  );
}

function ToolRow({ tool, onCall }: { tool: any; onCall: (args: string) => Promise<any> }) {
  const [open, setOpen] = useState(false);
  const [args, setArgs] = useState("{}");
  const [result, setResult] = useState<any>(null);
  return (
    <div className="rounded-md border border-border p-2 text-xs">
      <button onClick={() => setOpen((v) => !v)} className="flex items-center gap-1.5 w-full text-left">
        <Wrench className="h-3.5 w-3.5 text-accent" /><span className="font-medium">{tool.name}</span>
        <span className="text-muted truncate flex-1">{tool.description}</span>
      </button>
      {open && (
        <div className="mt-2 space-y-1.5">
          <textarea className="w-full h-16 rounded-md bg-surface border border-border p-2 font-mono text-[11px]" value={args} onChange={(e) => setArgs(e.target.value)} />
          <button onClick={async () => setResult(await onCall(args))} className="h-7 px-2 rounded-md bg-accent text-white text-[11px]">Run</button>
          {result !== undefined && result !== null && <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap bg-surface rounded-md p-2 text-[11px]">{JSON.stringify(result, null, 2)}</pre>}
        </div>
      )}
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="rounded-xl border border-border bg-surface p-4"><h2 className="text-sm font-medium mb-3">{title}</h2>{children}</motion.section>;
}
