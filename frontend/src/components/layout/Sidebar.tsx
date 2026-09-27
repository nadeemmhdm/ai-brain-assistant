import { useEffect, useState } from "react";
import { Plus, MessageSquare, Pencil, Trash2, Settings, Sun, Moon, Circle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, type Conversation } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { cn } from "@/lib/utils";

export function Sidebar({
  conversations, onNew, onSelect, onRename, onDelete,
}: {
  conversations: Conversation[];
  onNew: () => void;
  onSelect: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}) {
  const { activeConversationId, theme, setTheme, setSettingsOpen } = useAppStore();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [modelStatus, setModelStatus] = useState<{ main?: any; agent?: any }>({});

  useEffect(() => {
    const check = () => api.getModelStatus().then(setModelStatus).catch(() => {});
    check();
    const t = setInterval(check, 15000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="h-full w-64 flex-shrink-0 bg-canvas border-r border-border flex flex-col">
      <div className="p-3">
        <Button onClick={onNew} variant="outline" className="w-full justify-start gap-2">
          <Plus className="h-4 w-4" /> New chat
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 space-y-0.5 hide-scroll-bar">
        {conversations.map((c) => (
          <div
            key={c.id}
            className={cn(
              "group flex items-center gap-2 rounded-md px-2 py-2 cursor-pointer text-sm",
              c.id === activeConversationId ? "bg-surface-2 text-ink" : "text-muted hover:bg-surface-2/60"
            )}
            onClick={() => onSelect(c.id)}
          >
            <MessageSquare className="h-3.5 w-3.5 flex-shrink-0" />
            {editingId === c.id ? (
              <input
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onClick={(e) => e.stopPropagation()}
                onKeyDown={(e) => {
                  if (e.key === "Enter") { onRename(c.id, draft); setEditingId(null); }
                  if (e.key === "Escape") setEditingId(null);
                }}
                onBlur={() => { onRename(c.id, draft); setEditingId(null); }}
                className="flex-1 bg-transparent border-b border-border text-sm focus:outline-none"
              />
            ) : (
              <span className="flex-1 truncate">{c.title}</span>
            )}
            <div className="hidden group-hover:flex items-center gap-1">
              <button onClick={(e) => { e.stopPropagation(); setDraft(c.title); setEditingId(c.id); }}>
                <Pencil className="h-3 w-3 text-muted hover:text-ink" />
              </button>
              <button onClick={(e) => { e.stopPropagation(); onDelete(c.id); }}>
                <Trash2 className="h-3 w-3 text-muted hover:text-red-400" />
              </button>
            </div>
          </div>
        ))}
        {conversations.length === 0 && (
          <p className="text-xs text-muted px-2 py-4">No chats yet — start one above.</p>
        )}
      </div>

      <div className="p-3 border-t border-border space-y-2">
        <div className="flex items-center justify-between text-[11px] text-muted px-1">
          <StatusDot label="Main" online={!!modelStatus.main?.online} />
          <StatusDot label="Agent" online={!!modelStatus.agent?.online} />
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost" size="sm" className="flex-1 justify-start gap-2"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setSettingsOpen(true)} title="Settings">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function StatusDot({ label, online }: { label: string; online: boolean }) {
  return (
    <span className="flex items-center gap-1">
      <Circle className={cn("h-2 w-2", online ? "text-emerald-500 fill-emerald-500" : "text-red-500 fill-red-500")} />
      {label}
    </span>
  );
}
