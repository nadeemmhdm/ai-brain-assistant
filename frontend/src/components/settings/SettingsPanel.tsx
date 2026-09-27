import { useEffect, useState } from "react";
import { X, ShieldCheck, Plug, Sun, Moon, Cpu, Database } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import type { ReasoningLevel, ModelChoice } from "@/lib/api";

const LEVELS: ReasoningLevel[] = ["off", "low", "medium", "high", "max"];
const MODELS: { id: ModelChoice; label: string }[] = [
  { id: "main", label: "Qwen 2.5 1.5B (main)" },
  { id: "agent", label: "Qwen 2.5 0.5B (agent)" },
];

export function SettingsPanel() {
  const {
    settingsOpen, setSettingsOpen, theme, setTheme,
    reasoningLevel, setReasoningLevel, model, setModel,
  } = useAppStore();
  const [brain, setBrain] = useState<any>(null);
  const [mcp, setMcp] = useState<any>(null);

  useEffect(() => {
    if (!settingsOpen) return;
    api.brainStats().then(setBrain).catch(() => {});
    api.mcpConnectors().then(setMcp).catch(() => {});
  }, [settingsOpen]);

  if (!settingsOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={() => setSettingsOpen(false)} />
      <div className="relative w-full max-w-lg max-h-[85vh] overflow-y-auto bg-surface border border-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold">Settings</h2>
          <button onClick={() => setSettingsOpen(false)} className="text-muted hover:text-ink">
            <X className="h-4 w-4" />
          </button>
        </div>

        <Section icon={<Cpu className="h-4 w-4" />} title="Model & reasoning">
          <Field label="Default model">
            <div className="flex gap-2">
              {MODELS.map((m) => (
                <Chip key={m.id} active={model === m.id} onClick={() => { setModel(m.id); api.setSetting("default_model", m.id); }}>
                  {m.label}
                </Chip>
              ))}
            </div>
          </Field>
          <Field label="Reasoning level (default: Medium)">
            <div className="flex gap-2 flex-wrap">
              {LEVELS.map((l) => (
                <Chip key={l} active={reasoningLevel === l} onClick={() => { setReasoningLevel(l); api.setSetting("reasoning_level", l); }}>
                  {l[0].toUpperCase() + l.slice(1)}
                </Chip>
              ))}
            </div>
            <p className="text-[11px] text-muted mt-1">
              "Off" skips the thinking step for the fastest replies. Higher levels let the model
              reason longer in a scratchpad before answering.
            </p>
          </Field>
        </Section>

        <Section icon={theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />} title="Appearance">
          <Field label="Theme">
            <div className="flex gap-2">
              <Chip active={theme === "dark"} onClick={() => setTheme("dark")}>Dark</Chip>
              <Chip active={theme === "light"} onClick={() => setTheme("light")}>Light</Chip>
            </div>
          </Field>
        </Section>

        <Section icon={<Plug className="h-4 w-4" />} title="MCP connectors">
          <p className="text-xs text-muted mb-2">
            {mcp?.note || "Loading…"}
          </p>
          <span className="inline-block text-[10px] uppercase tracking-wide px-2 py-0.5 rounded bg-amber-500/15 text-amber-500 border border-amber-500/30">
            Experimental — not yet connected
          </span>
        </Section>

        <Section icon={<Database className="h-4 w-4" />} title="AI Brain">
          {brain ? (
            <div className="grid grid-cols-2 gap-2 text-xs">
              <Stat label="Topics" value={brain.total_topics} />
              <Stat label="Knowledge items" value={brain.total_knowledge_items} />
              <Stat label="Verified" value={brain.verified_knowledge} />
              <Stat label="Conflicts" value={brain.conflicting_knowledge} />
              <Stat label="Sources" value={brain.total_sources} />
              <Stat label="Embedding" value={brain.embedding_backend} />
            </div>
          ) : (
            <p className="text-xs text-muted">Loading…</p>
          )}
        </Section>

        <Section icon={<ShieldCheck className="h-4 w-4" />} title="Privacy & security">
          <ul className="text-xs text-muted space-y-1 list-disc pl-4">
            <li>Chats, the AI Brain, and settings are stored only in a local SQLite file on this machine.</li>
            <li>The backend binds to 127.0.0.1 only — nothing is exposed to your network by default.</li>
            <li>No API keys are used or required; none are ever sent to the browser.</li>
            <li>Web content fetched during research is treated as untrusted data, never as instructions.</li>
          </ul>
        </Section>
      </div>
    </div>
  );
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <div className="flex items-center gap-2 mb-2 text-sm font-medium">
        {icon} {title}
      </div>
      <div className="pl-6">{children}</div>
    </div>
  );
}
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <p className="text-xs text-muted mb-1.5">{label}</p>
      {children}
    </div>
  );
}
function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-2.5 py-1 rounded-full text-xs border transition-colors ${
        active ? "bg-accent text-white border-accent" : "border-border text-muted hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
function Stat({ label, value }: { label: string; value: any }) {
  return (
    <div className="rounded-md bg-surface-2 border border-border px-2 py-1.5">
      <div className="text-muted text-[10px]">{label}</div>
      <div className="font-medium">{value ?? "—"}</div>
    </div>
  );
}
