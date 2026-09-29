import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Sparkles, ArrowRight, User, Bot } from "lucide-react";
import { api } from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";

/** First-run setup: what to call the assistant, and what it should call you. */
export function Onboarding({ onDone }: { onDone: () => void }) {
  const setProfile = useAppStore((s) => s.setProfile);
  const [step, setStep] = useState(0);
  const [ai, setAi] = useState("Nila"); const [user, setUser] = useState("");
  const clean = (v: string) => v.replace(/[^\p{L}\p{N} .'-]/gu, "").slice(0, 30);

  const finish = async () => {
    const a = ai.trim() || "Nila", u = user.trim();
    await Promise.all([api.setSetting("ai_name", a), api.setSetting("user_name", u), api.setSetting("onboarded", "true")]);
    setProfile({ aiName: a, userName: u, onboarded: true });
    onDone();
  };
  const field = "w-full rounded-xl bg-surface-2 border border-border px-4 py-3 text-base focus:outline-none focus:border-accent";

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-canvas p-4">
      <motion.div initial={{ opacity: 0, y: 24, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ type: "spring", stiffness: 240, damping: 24 }}
        className="w-full max-w-md bg-surface border border-border rounded-2xl p-7 shadow-2xl">
        <motion.div animate={{ rotate: [0, 10, -10, 0] }} transition={{ repeat: Infinity, duration: 4 }} className="mx-auto mb-4 h-14 w-14 rounded-2xl bg-accent/15 flex items-center justify-center">
          <Sparkles className="h-7 w-7 text-accent" />
        </motion.div>
        <AnimatePresence mode="wait">
          {step === 0 ? (
            <motion.div key="a" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <h1 className="text-xl font-semibold text-center">Welcome! 👋</h1>
              <p className="text-sm text-muted text-center mt-1 mb-5">Your private assistant runs on your own computer. What would you like to call it?</p>
              <div className="relative"><Bot className="h-4 w-4 text-muted absolute left-4 top-1/2 -translate-y-1/2" />
                <input autoFocus className={field + " pl-10"} value={ai} onChange={(e) => setAi(clean(e.target.value))} onKeyDown={(e) => e.key === "Enter" && ai.trim() && setStep(1)} placeholder="Nila" /></div>
              <p className="text-[11px] text-muted mt-2">You can also wake it by voice by saying “Hey {ai.trim() || "Nila"}”.</p>
              <button disabled={!ai.trim()} onClick={() => setStep(1)} className="mt-5 w-full h-11 rounded-xl bg-accent text-white font-medium flex items-center justify-center gap-2 disabled:opacity-50">Next <ArrowRight className="h-4 w-4" /></button>
            </motion.div>
          ) : (
            <motion.div key="b" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <h1 className="text-xl font-semibold text-center">Nice to meet you!</h1>
              <p className="text-sm text-muted text-center mt-1 mb-5">I’m {ai.trim() || "Nila"}. What should I call you?</p>
              <div className="relative"><User className="h-4 w-4 text-muted absolute left-4 top-1/2 -translate-y-1/2" />
                <input autoFocus className={field + " pl-10"} value={user} onChange={(e) => setUser(clean(e.target.value))} onKeyDown={(e) => e.key === "Enter" && user.trim() && finish()} placeholder="Your name" /></div>
              <button disabled={!user.trim()} onClick={finish} className="mt-5 w-full h-11 rounded-xl bg-accent text-white font-medium flex items-center justify-center gap-2 disabled:opacity-50">Let’s go <ArrowRight className="h-4 w-4" /></button>
              <button onClick={() => setStep(0)} className="mt-2 w-full text-xs text-muted hover:text-ink">Back</button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
