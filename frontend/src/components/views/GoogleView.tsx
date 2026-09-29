import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { Mail, Video, Table, Presentation, Link2, Unplug, Trash2, Send, Save, Plus, RefreshCw, ExternalLink, Copy } from "lucide-react";
import { api2 } from "@/lib/api2";
import { useAppStore } from "@/store/useAppStore";
import { toast } from "@/store/useToast";
import { PermissionDialog, type Grant } from "@/components/ui/PermissionDialog";
import { AnimatedIcon } from "@/components/ui/AnimatedIcon";

const inp = "w-full h-9 px-3 rounded-lg bg-surface-2 border border-border text-sm focus:outline-none focus:border-accent";
type Tab = "mail" | "meet" | "sheets" | "slides";
const TABS: { id: Tab; icon: any; label: string }[] = [
  { id: "mail", icon: Mail, label: "Mail" }, { id: "meet", icon: Video, label: "Meet" },
  { id: "sheets", icon: Table, label: "Sheets" }, { id: "slides", icon: Presentation, label: "Slides" },
];
const META: Record<string, { label: string; risk: string }> = {
  "gmail.read": { label: "Read your recent emails", risk: "read" }, "gmail.get": { label: "Open an email", risk: "read" },
  "gmail.drafts": { label: "List your drafts", risk: "read" }, "gmail.draft.get": { label: "Open a draft", risk: "read" },
  "gmail.draft": { label: "Save an email draft", risk: "write" }, "gmail.send": { label: "Send an email", risk: "external" },
  "gmail.trash": { label: "Move an email to Trash", risk: "destructive" }, "gmail.draft.delete": { label: "Delete a draft", risk: "destructive" },
  "meet.create": { label: "Create a Google Meet", risk: "write" }, "meet.invite": { label: "Create a Meet and invite people", risk: "external" },
  "meet.list": { label: "Read your upcoming events", risk: "read" }, "meet.update": { label: "Edit an event", risk: "write" },
  "meet.share": { label: "Invite people to an event", risk: "external" }, "meet.delete": { label: "Delete an event", risk: "destructive" },
  "sheets.create": { label: "Create a Google Sheet", risk: "write" }, "sheets.write": { label: "Write to a Sheet", risk: "write" }, "sheets.read": { label: "Read a Sheet", risk: "read" },
  "slides.create": { label: "Create a Slides deck", risk: "write" }, "slides.add": { label: "Add a slide", risk: "write" }, "drive.list": { label: "List files made with this app", risk: "read" },
};

export function GoogleView() {
  const convId = useAppStore((s) => s.activeConversationId);
  const [st, setSt] = useState<any>(null); const [tab, setTab] = useState<Tab>("mail");
  const [req, setReq] = useState<{ action: string; params: any; summary?: string; resolve: (g: Grant | null) => void } | null>(null);
  const always = useRef<Set<string>>(new Set());

  const refreshStatus = () => api2.googleStatus().then(setSt).catch(() => {});
  const refreshGrants = () => api2.googlePermissions().then((g) => { always.current = new Set(g.filter((x) => x.scope === "always").map((x) => x.action)); }).catch(() => {});
  useEffect(() => { refreshStatus(); refreshGrants(); const h = (e: MessageEvent) => e.data === "google-connected" && refreshStatus(); window.addEventListener("message", h); return () => window.removeEventListener("message", h); }, []);

  /** Ask permission (unless "always allow" is on) and run the action. */
  const run = async (action: string, params: any = {}, summary?: string): Promise<any | null> => {
    try {
      if (always.current.has(action)) return (await api2.googleExecute(action, params, "standing", convId)).result;
      const grant = await new Promise<Grant | null>((resolve) => setReq({ action, params, summary, resolve }));
      setReq(null);
      if (!grant) return null;
      const r = (await api2.googleExecute(action, params, grant, convId)).result;
      if (grant === "always") always.current.add(action);
      return r;
    } catch (e: any) { toast.error(e.message); return null; }
  };

  const connect = async () => { try { const { url } = await api2.googleConnect(); window.open(url, "_blank", "noopener,width=520,height=700"); } catch (e: any) { toast.error(e.message); } };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6 space-y-5">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h1 className="text-xl font-semibold flex items-center gap-2"><AnimatedIcon icon={Mail} kind="bounce" loop className="h-5 w-5 text-accent" /> Google</h1>
            <p className="text-xs text-muted mt-1">Every action asks your permission first. Nothing is sent, invited or deleted without your say-so.</p>
          </div>
          {st?.connected ? (
            <div className="flex items-center gap-2 text-xs"><span className="text-emerald-500">● {st.email || "Connected"}</span>
              <button className="text-muted hover:text-red-400 flex items-center gap-1" onClick={async () => { await api2.googleDisconnect(); refreshStatus(); toast.success("Disconnected"); }}><Unplug className="h-3.5 w-3.5" /> Disconnect</button></div>
          ) : (
            <motion.button whileTap={{ scale: 0.96 }} onClick={connect} className="h-9 px-4 rounded-lg bg-accent text-white text-sm flex items-center gap-2"><Link2 className="h-4 w-4" /> Connect Google</motion.button>
          )}
        </div>

        {st && !st.configured && (
          <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-xs space-y-1">
            <p className="font-medium">One-time setup needed</p>
            <p>Create a Google Cloud OAuth client (type “Web application”), add <code>{st.redirect_uri}</code> as an authorised redirect URI, enable the Gmail, Calendar, Sheets, Slides and Drive APIs, then put <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code> in <code>backend/.env</code> and restart. Full steps are in the README.</p>
          </div>
        )}

        {st?.connected && (
          <>
            <div className="flex gap-1 border-b border-border">
              {TABS.map(({ id, icon: I, label }) => (
                <button key={id} onClick={() => setTab(id)} className={`relative px-3 py-2 text-sm flex items-center gap-1.5 ${tab === id ? "text-accent" : "text-muted hover:text-ink"}`}>
                  <I className="h-4 w-4" />{label}{tab === id && <motion.span layoutId="gtab" className="absolute inset-x-0 -bottom-px h-0.5 bg-accent" />}
                </button>
              ))}
            </div>
            {tab === "mail" && <MailTab run={run} />}
            {tab === "meet" && <MeetTab run={run} />}
            {tab === "sheets" && <SheetsTab run={run} />}
            {tab === "slides" && <SlidesTab run={run} />}
          </>
        )}
      </div>
      <PermissionDialog
        req={req ? { ...META[req.action], summary: req.summary } : null}
        onChoose={(g) => { req?.resolve(g); if (g === "always") refreshGrants(); }}
        onCancel={() => req?.resolve(null)} />
    </div>
  );
}

type Run = (action: string, params?: any, summary?: string) => Promise<any | null>;
const Box = ({ children, className = "" }: any) => <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={`rounded-xl border border-border bg-surface p-4 ${className}`}>{children}</motion.div>;
const Btn = ({ children, onClick, danger, disabled }: any) => <button disabled={disabled} onClick={onClick} className={`h-8 px-3 rounded-lg text-xs flex items-center gap-1.5 border disabled:opacity-40 ${danger ? "border-red-500/40 text-red-400 hover:bg-red-500/10" : "border-border hover:border-accent hover:text-accent"}`}>{children}</button>;

function MailTab({ run }: { run: Run }) {
  const [inbox, setInbox] = useState<any[] | null>(null); const [drafts, setDrafts] = useState<any[] | null>(null); const [open, setOpen] = useState<any>(null);
  const [f, setF] = useState({ id: "", to: "", subject: "", body: "" });
  const loadInbox = async () => { const r = await run("gmail.read", { q: "in:inbox", max: 10 }); if (r) setInbox(r.messages); };
  const loadDrafts = async () => { const r = await run("gmail.drafts"); if (r) setDrafts(r.drafts); };
  const params = () => ({ draft_id: f.id || undefined, to: f.to, subject: f.subject, body: f.body });
  const summary = () => `To: ${f.to}\nSubject: ${f.subject}\n\n${f.body.slice(0, 300)}`;
  return (
    <div className="grid md:grid-cols-2 gap-4">
      <Box className="space-y-2">
        <h2 className="text-sm font-medium">{f.id ? "Edit draft" : "Write an email"}</h2>
        <input className={inp} placeholder="To (comma separated)" value={f.to} onChange={(e) => setF({ ...f, to: e.target.value })} />
        <input className={inp} placeholder="Subject" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} />
        <textarea className={inp + " h-40 py-2"} placeholder="Message" value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} />
        <div className="flex gap-2 flex-wrap">
          <Btn disabled={!f.to} onClick={async () => { const r = await run("gmail.draft", params(), summary()); if (r) { toast.success("Draft saved"); setF({ id: "", to: "", subject: "", body: "" }); loadDrafts(); } }}><Save className="h-3.5 w-3.5" /> Save draft</Btn>
          <Btn disabled={!f.to || !f.body} onClick={async () => { const r = await run("gmail.send", params(), summary()); if (r) { toast.success("Email sent"); setF({ id: "", to: "", subject: "", body: "" }); } }}><Send className="h-3.5 w-3.5" /> Send</Btn>
          {f.id && <Btn onClick={() => setF({ id: "", to: "", subject: "", body: "" })}>New</Btn>}
        </div>
      </Box>
      <div className="space-y-4">
        <Box>
          <div className="flex items-center justify-between mb-2"><h2 className="text-sm font-medium">Inbox</h2><Btn onClick={loadInbox}><RefreshCw className="h-3.5 w-3.5" /> Load</Btn></div>
          <div className="space-y-1 max-h-56 overflow-y-auto">
            {inbox?.map((m) => (
              <div key={m.id} className="flex items-start gap-2 text-xs border border-border rounded-lg p-2">
                <button className="flex-1 text-left min-w-0" onClick={async () => { const r = await run("gmail.get", { id: m.id }); if (r) setOpen(r); }}>
                  <div className={`truncate ${m.unread ? "font-semibold" : ""}`}>{m.subject || "(no subject)"}</div><div className="text-muted truncate">{m.from}</div>
                </button>
                <button title="Move to Trash" className="text-muted hover:text-red-400" onClick={async () => { const r = await run("gmail.trash", { id: m.id }, m.subject); if (r) { toast.success("Moved to Trash"); setInbox((x) => x!.filter((y) => y.id !== m.id)); } }}><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            ))}
            {inbox && !inbox.length && <p className="text-xs text-muted">Nothing here.</p>}
          </div>
          {open && <div className="mt-2 border-t border-border pt-2 text-xs"><b>{open.subject}</b><div className="text-muted">{open.from}</div><pre className="whitespace-pre-wrap mt-1 max-h-40 overflow-auto">{open.body}</pre></div>}
        </Box>
        <Box>
          <div className="flex items-center justify-between mb-2"><h2 className="text-sm font-medium">Drafts</h2><Btn onClick={loadDrafts}><RefreshCw className="h-3.5 w-3.5" /> Load</Btn></div>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {drafts?.map((d) => (
              <div key={d.id} className="flex items-center gap-2 text-xs border border-border rounded-lg p-2">
                <button className="flex-1 text-left min-w-0" onClick={async () => { const r = await run("gmail.draft.get", { id: d.id }); if (r) setF({ id: d.id, to: r.to, subject: r.subject, body: r.body }); }}>
                  <div className="truncate">{d.subject || "(no subject)"}</div><div className="text-muted truncate">{d.to}</div></button>
                <button className="text-muted hover:text-red-400" onClick={async () => { const r = await run("gmail.draft.delete", { id: d.id }, d.subject); if (r) { toast.success("Draft deleted"); setDrafts((x) => x!.filter((y) => y.id !== d.id)); } }}><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            ))}
          </div>
        </Box>
      </div>
    </div>
  );
}

function MeetTab({ run }: { run: Run }) {
  const [f, setF] = useState({ summary: "", when: "", minutes: 30, invitees: "" }); const [events, setEvents] = useState<any[] | null>(null); const [created, setCreated] = useState<any>(null);
  const load = async () => { const r = await run("meet.list"); if (r) setEvents(r.events); };
  const create = async () => {
    const att = f.invitees.split(",").map((x) => x.trim()).filter(Boolean);
    const p = { summary: f.summary || "Meeting", start: f.when ? new Date(f.when).toISOString() : null, minutes: f.minutes, attendees: att };
    const r = await run(att.length ? "meet.invite" : "meet.create", p, `${p.summary}${att.length ? `\nInvites: ${att.join(", ")}` : ""}`);
    if (r) { setCreated(r); toast.success("Meeting created"); load(); }
  };
  const copy = (l: string) => { navigator.clipboard.writeText(l); toast.success("Meet link copied"); };
  return (
    <div className="grid md:grid-cols-2 gap-4">
      <Box className="space-y-2">
        <h2 className="text-sm font-medium">New Google Meet</h2>
        <input className={inp} placeholder="Title" value={f.summary} onChange={(e) => setF({ ...f, summary: e.target.value })} />
        <div className="flex gap-2"><input type="datetime-local" className={inp} value={f.when} onChange={(e) => setF({ ...f, when: e.target.value })} /><input type="number" min={5} className={inp + " w-24"} value={f.minutes} onChange={(e) => setF({ ...f, minutes: +e.target.value })} /></div>
        <input className={inp} placeholder="Invite by email (optional, comma separated)" value={f.invitees} onChange={(e) => setF({ ...f, invitees: e.target.value })} />
        <Btn onClick={create}><Plus className="h-3.5 w-3.5" /> Create meeting</Btn>
        {created?.meet_link && <div className="text-xs rounded-lg border border-emerald-500/40 p-2 flex items-center gap-2"><a className="text-accent underline truncate flex-1" href={created.meet_link} target="_blank" rel="noreferrer">{created.meet_link}</a><button onClick={() => copy(created.meet_link)}><Copy className="h-3.5 w-3.5" /></button></div>}
      </Box>
      <Box>
        <div className="flex items-center justify-between mb-2"><h2 className="text-sm font-medium">Upcoming</h2><Btn onClick={load}><RefreshCw className="h-3.5 w-3.5" /> Load</Btn></div>
        <div className="space-y-1 max-h-80 overflow-y-auto">
          {events?.map((e) => (
            <div key={e.id} className="text-xs border border-border rounded-lg p-2">
              <div className="font-medium truncate">{e.summary || "(no title)"}</div><div className="text-muted">{e.start && new Date(e.start).toLocaleString()}</div>
              <div className="flex gap-2 mt-1.5 flex-wrap">
                {e.meet_link && <><a className="text-accent flex items-center gap-1" href={e.meet_link} target="_blank" rel="noreferrer"><ExternalLink className="h-3 w-3" /> Join</a><button className="flex items-center gap-1 text-muted hover:text-accent" onClick={() => copy(e.meet_link)}><Copy className="h-3 w-3" /> Share link</button></>}
                <button className="text-muted hover:text-accent" onClick={async () => { const em = prompt("Invite (email, comma separated):"); if (!em) return; const r = await run("meet.share", { id: e.id, attendees: em }, `Invite: ${em}`); if (r) { toast.success("Invited"); load(); } }}>Invite</button>
                <button className="text-muted hover:text-accent" onClick={async () => { const t = prompt("New title:", e.summary); if (t === null) return; const r = await run("meet.update", { id: e.id, summary: t }, t); if (r) { toast.success("Updated"); load(); } }}>Rename</button>
                <button className="text-muted hover:text-red-400" onClick={async () => { const r = await run("meet.delete", { id: e.id }, e.summary); if (r) { toast.success("Deleted"); setEvents((x) => x!.filter((y) => y.id !== e.id)); } }}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      </Box>
    </div>
  );
}

function FileTab({ run, kind, noun, icon: Icon, children }: { run: Run; kind: "sheets" | "slides"; noun: string; icon: any; children: (files: any[], reload: () => void) => any }) {
  const [files, setFiles] = useState<any[] | null>(null);
  const load = async () => { const r = await run("drive.list", { kind }); if (r) setFiles(r.files); };
  return (
    <Box>
      <div className="flex items-center justify-between mb-2"><h2 className="text-sm font-medium flex items-center gap-2"><Icon className="h-4 w-4" /> Your {noun}s (made with this app)</h2><Btn onClick={load}><RefreshCw className="h-3.5 w-3.5" /> Load</Btn></div>
      <div className="space-y-1">{files?.map((f) => <a key={f.id} href={f.webViewLink} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-xs border border-border rounded-lg p-2 hover:border-accent"><span className="flex-1 truncate">{f.name}</span><ExternalLink className="h-3 w-3" /></a>)}{files && !files.length && <p className="text-xs text-muted">None yet.</p>}</div>
      {children(files || [], load)}
    </Box>
  );
}

function SheetsTab({ run }: { run: Run }) {
  const [title, setTitle] = useState(""); const [id, setId] = useState(""); const [row, setRow] = useState(""); const [preview, setPreview] = useState<any[][] | null>(null);
  return (
    <div className="space-y-4">
      <Box className="flex gap-2"><input className={inp} placeholder="New sheet title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Btn disabled={!title} onClick={async () => { const r = await run("sheets.create", { title }, title); if (r) { toast.success("Sheet created"); setId(r.id); window.open(r.url, "_blank", "noopener"); } }}><Plus className="h-3.5 w-3.5" /> Create</Btn></Box>
      <FileTab run={run} kind="sheets" noun="sheet" icon={Table}>{(files) => (
        <div className="mt-3 space-y-2">
          <select className={inp} value={id} onChange={(e) => setId(e.target.value)}><option value="">Pick a sheet…</option>{files.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select>
          <div className="flex gap-2"><input className={inp} placeholder="Add a row: value 1, value 2, value 3" value={row} onChange={(e) => setRow(e.target.value)} />
            <Btn disabled={!id || !row} onClick={async () => { const r = await run("sheets.write", { id, rows: [row.split(",").map((x) => x.trim())] }, row); if (r) { toast.success("Row added"); setRow(""); } }}>Add row</Btn>
            <Btn disabled={!id} onClick={async () => { const r = await run("sheets.read", { id }); if (r) setPreview(r.values); }}>Preview</Btn></div>
          {preview && <div className="overflow-auto max-h-56 border border-border rounded-lg"><table className="text-xs w-full"><tbody>{preview.map((r, i) => <tr key={i} className="border-b border-border last:border-0">{r.map((c, j) => <td key={j} className="px-2 py-1 whitespace-nowrap">{c}</td>)}</tr>)}</tbody></table></div>}
        </div>)}</FileTab>
    </div>
  );
}

function SlidesTab({ run }: { run: Run }) {
  const [title, setTitle] = useState(""); const [outline, setOutline] = useState(""); const [id, setId] = useState(""); const [st, setSt] = useState(""); const [sb, setSb] = useState("");
  return (
    <div className="space-y-4">
      <Box className="space-y-2"><h2 className="text-sm font-medium">New presentation</h2>
        <input className={inp} placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <textarea className={inp + " h-24 py-2"} placeholder={"Optional slides, one per line:  Slide title: point one; point two"} value={outline} onChange={(e) => setOutline(e.target.value)} />
        <Btn disabled={!title} onClick={async () => {
          const slides = outline.split("\n").filter(Boolean).slice(0, 8).map((l) => { const [t, ...b] = l.split(":"); return { title: t.trim(), body: b.join(":").split(";").map((x) => "• " + x.trim()).join("\n") }; });
          const r = await run("slides.create", { title, slides }, `${title} (${slides.length} slides)`); if (r) { toast.success("Presentation created"); window.open(r.url, "_blank", "noopener"); } }}><Plus className="h-3.5 w-3.5" /> Create</Btn></Box>
      <FileTab run={run} kind="slides" noun="deck" icon={Presentation}>{(files) => (
        <div className="mt-3 space-y-2">
          <select className={inp} value={id} onChange={(e) => setId(e.target.value)}><option value="">Pick a deck…</option>{files.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select>
          <input className={inp} placeholder="New slide title" value={st} onChange={(e) => setSt(e.target.value)} /><textarea className={inp + " h-20 py-2"} placeholder="Slide text" value={sb} onChange={(e) => setSb(e.target.value)} />
          <Btn disabled={!id || !st} onClick={async () => { const r = await run("slides.add", { id, title: st, body: sb }, st); if (r) { toast.success("Slide added"); setSt(""); setSb(""); } }}><Plus className="h-3.5 w-3.5" /> Add slide</Btn>
        </div>)}</FileTab>
    </div>
  );
}
