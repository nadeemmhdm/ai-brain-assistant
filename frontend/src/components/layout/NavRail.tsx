import { motion } from "motion/react";
import { MessageSquare, Database, Cpu, Settings } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";

export type View = "chat" | "brain" | "training";
const ITEMS: { id: View; icon: any; label: string }[] = [
  { id: "chat", icon: MessageSquare, label: "Chat" },
  { id: "brain", icon: Database, label: "AI Brain" },
  { id: "training", icon: Cpu, label: "Training" },
];

export function NavRail({ view, onChange }: { view: View; onChange: (v: View) => void }) {
  const setSettingsOpen = useAppStore((s) => s.setSettingsOpen);
  return (
    <nav className="w-14 flex-shrink-0 bg-surface border-r border-border flex flex-col items-center py-3 gap-1">
      {ITEMS.map(({ id, icon: Icon, label }) => (
        <button
          key={id} title={label} onClick={() => onChange(id)}
          className="relative h-10 w-10 flex items-center justify-center rounded-xl text-muted hover:text-ink transition-colors"
        >
          {view === id && (
            <motion.span
              layoutId="nav-pill"
              className="absolute inset-0 rounded-xl bg-accent/15 border border-accent/30"
              transition={{ type: "spring", stiffness: 420, damping: 32 }}
            />
          )}
          <motion.span whileTap={{ scale: 0.88 }} className={`relative ${view === id ? "text-accent" : ""}`}>
            <Icon className="h-[18px] w-[18px]" />
          </motion.span>
        </button>
      ))}
      <div className="flex-1" />
      <button title="Settings" onClick={() => setSettingsOpen(true)}
        className="h-10 w-10 flex items-center justify-center rounded-xl text-muted hover:text-ink hover:bg-surface-2 transition-colors">
        <motion.span whileHover={{ rotate: 45 }} transition={{ type: "spring", stiffness: 300 }}>
          <Settings className="h-[18px] w-[18px]" />
        </motion.span>
      </button>
    </nav>
  );
}
