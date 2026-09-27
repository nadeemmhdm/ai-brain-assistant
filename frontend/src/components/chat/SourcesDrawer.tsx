import { X, ExternalLink, ShieldCheck, ShieldAlert, Shield, ShieldQuestion } from "lucide-react";
import type { Source } from "@/lib/api";

const TIER_META: Record<string, { label: string; icon: any; color: string }> = {
  A: { label: "Official / standards / education", icon: ShieldCheck, color: "text-emerald-500" },
  B: { label: "Established organization", icon: Shield, color: "text-sky-500" },
  C: { label: "General web / blog", icon: ShieldQuestion, color: "text-amber-500" },
  D: { label: "Forum / user-generated", icon: ShieldAlert, color: "text-red-500" },
};

export function SourcesDrawer({ sources, onClose }: { sources: Source[]; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-label="Sources">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative w-full max-w-sm h-full bg-surface border-l border-border p-4 overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold">Sources ({sources.length})</h2>
          <button onClick={onClose} className="text-muted hover:text-ink" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="space-y-3">
          {sources.map((s) => {
            const meta = TIER_META[s.trust_tier] || TIER_META.C;
            const Icon = meta.icon;
            return (
              <a
                key={s.id}
                href={s.url}
                target="_blank"
                rel="noreferrer"
                className="block rounded-lg border border-border bg-surface-2 p-3 hover:border-accent transition-colors"
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <Icon className={`h-3.5 w-3.5 ${meta.color}`} />
                  <span className="text-[11px] text-muted">{meta.label}</span>
                  <span className="text-[11px] text-muted ml-auto">
                    Tier {s.trust_tier}
                  </span>
                </div>
                <p className="text-sm font-medium leading-snug line-clamp-2">{s.title || s.url}</p>
                <div className="flex items-center gap-1 mt-1 text-[11px] text-muted truncate">
                  <ExternalLink className="h-3 w-3 flex-shrink-0" />
                  <span className="truncate">{s.url}</span>
                </div>
                <p className="text-[10px] text-muted mt-1">
                  Fetched {new Date(s.fetched_at * 1000).toLocaleString()}
                </p>
              </a>
            );
          })}
          {sources.length === 0 && <p className="text-sm text-muted">No sources for this answer.</p>}
        </div>
      </div>
    </div>
  );
}
