import { AnimatePresence, motion } from "motion/react";
import { CheckCircle2, AlertCircle, Info } from "lucide-react";
import { useToast } from "@/store/useToast";

const ICONS = { success: CheckCircle2, error: AlertCircle, info: Info };
const COLORS = { success: "text-emerald-500", error: "text-red-500", info: "text-sky-500" };

export function Toaster() {
  const { toasts, dismiss } = useToast();
  return (
    <div className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2 pointer-events-none">
      <AnimatePresence initial={false}>
        {toasts.map((t) => {
          const Icon = ICONS[t.kind];
          return (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, y: 16, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, x: 40, transition: { duration: 0.18 } }}
              transition={{ type: "spring", stiffness: 420, damping: 30 }}
              onClick={() => dismiss(t.id)}
              className="pointer-events-auto flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm shadow-lg cursor-pointer"
            >
              <Icon className={`h-4 w-4 ${COLORS[t.kind]}`} />
              {t.text}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
