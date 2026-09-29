import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import * as Icons from "lucide-react";
import { Sparkles, ChevronDown, X, Check } from "lucide-react";
import { api2 } from "@/lib/api2";
import { cn } from "@/lib/utils";

/** Lets the composer attach a saved Skill's instructions to the next message. */
export function SkillPicker({ skillId, onChange }: { skillId: string | null; onChange: (id: string | null, name: string | null) => void }) {
  const [open, setOpen] = useState(false);
  const [skills, setSkills] = useState<any[]>([]);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { api2.listSkills().then(setSkills).catch(() => {}); }, []);
  useEffect(() => {
    const onDoc = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", onDoc); return () => document.removeEventListener("mousedown", onDoc);
  }, []);
  const current = skills.find((s) => s.id === skillId);
  const Icon = (current && (Icons as any)[current.icon]) || Sparkles;

  return (
    <div className="relative" ref={ref}>
      <motion.button whileTap={{ scale: 0.95 }} onClick={() => setOpen((v) => !v)}
        className={cn("h-8 px-2.5 rounded-md text-xs font-medium flex items-center gap-1.5 border",
          current ? "bg-accent/15 text-accent border-accent/40" : "text-muted border-transparent hover:bg-surface-2")}>
        <Icon className="h-3.5 w-3.5" />{current ? current.name : "Skill"}
        {current && <X className="h-3 w-3 ml-0.5" onClick={(e) => { e.stopPropagation(); onChange(null, null); }} />}
      </motion.button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, y: 6, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 6, scale: 0.97 }}
            className="absolute bottom-full left-0 mb-2 w-64 bg-surface border border-border rounded-lg shadow-xl z-20 p-1.5 max-h-72 overflow-y-auto">
            <button onClick={() => { onChange(null, null); setOpen(false); }} className="w-full text-left px-2.5 py-2 rounded-md hover:bg-surface-2 text-xs text-muted">No skill — just chat</button>
            {skills.map((s) => {
              const I = (Icons as any)[s.icon] || Sparkles;
              return (
                <button key={s.id} onClick={() => { onChange(s.id, s.name); setOpen(false); }}
                  className="w-full text-left px-2.5 py-2 rounded-md hover:bg-surface-2 flex items-start gap-2">
                  <I className="h-3.5 w-3.5 text-accent mt-0.5 flex-shrink-0" />
                  <span className="flex-1 min-w-0">
                    <span className="text-sm font-medium flex items-center gap-1">{s.name}{s.id === skillId && <Check className="h-3 w-3 text-accent" />}</span>
                    <span className="block text-[11px] text-muted truncate">{s.description}</span>
                  </span>
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
