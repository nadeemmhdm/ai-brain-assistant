import { motion, type TargetAndTransition } from "motion/react";
import type { LucideIcon } from "lucide-react";

type Kind = "wiggle" | "spin" | "pulse" | "bounce" | "float";
const HOVER: Record<Kind, TargetAndTransition> = {
  wiggle: { rotate: [0, -14, 12, -8, 0], transition: { duration: 0.5 } },
  spin: { rotate: 180, transition: { type: "spring", stiffness: 200, damping: 12 } },
  pulse: { scale: [1, 1.25, 1], transition: { duration: 0.45 } },
  bounce: { y: [0, -5, 0], transition: { duration: 0.45 } },
  float: { y: -2, scale: 1.1 },
};

/** A lucide icon that animates on hover/tap. Pass `loop` for a gentle idle animation. */
export function AnimatedIcon({ icon: Icon, kind = "wiggle", loop = false, className = "h-[18px] w-[18px]" }:
  { icon: LucideIcon; kind?: Kind; loop?: boolean; className?: string }) {
  return (
    <motion.span
      className="inline-flex"
      whileHover={HOVER[kind]}
      whileTap={{ scale: 0.85 }}
      animate={loop ? { y: [0, -2, 0], opacity: [0.85, 1, 0.85] } : undefined}
      transition={loop ? { repeat: Infinity, duration: 2.4, ease: "easeInOut" } : undefined}
    >
      <Icon className={className} />
    </motion.span>
  );
}
