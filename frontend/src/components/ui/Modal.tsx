import { AnimatePresence, motion } from "motion/react";
import { X } from "lucide-react";

export function Modal({
  open, onClose, title, icon, children, maxWidth = "max-w-lg",
}: {
  open: boolean; onClose: () => void; title: string; icon?: React.ReactNode;
  children: React.ReactNode; maxWidth?: string;
}) {
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            role="dialog" aria-label={title}
            className={`relative w-full ${maxWidth} max-h-[88vh] overflow-y-auto bg-surface border border-border rounded-2xl p-5 shadow-2xl`}
            initial={{ opacity: 0, scale: 0.95, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ type: "spring", stiffness: 380, damping: 32 }}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold flex items-center gap-2">{icon}{title}</h2>
              <button onClick={onClose} className="text-muted hover:text-ink transition-colors" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
