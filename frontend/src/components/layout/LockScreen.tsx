import { useState } from "react";
import { motion } from "motion/react";
import { Lock, ArrowRight, Loader2 } from "lucide-react";
import { api, setSessionToken } from "@/lib/api";

export function LockScreen({ onUnlocked }: { onUnlocked: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [shake, setShake] = useState(0);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;
    setBusy(true); setError("");
    try {
      const { token } = await api.authLogin(password);
      setSessionToken(token);
      onUnlocked();
    } catch (err: any) {
      setError(err.message || "Incorrect passphrase.");
      setShake((n) => n + 1);
    } finally { setBusy(false); }
  };

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-canvas p-4">
      <motion.form
        onSubmit={submit}
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: "spring", stiffness: 260, damping: 26 }}
        className="w-full max-w-sm bg-surface border border-border rounded-2xl p-6 shadow-xl"
      >
        <motion.div
          className="mx-auto mb-4 h-12 w-12 rounded-full bg-accent/15 flex items-center justify-center"
          animate={{ scale: [1, 1.06, 1] }}
          transition={{ repeat: Infinity, duration: 2.8, ease: "easeInOut" }}
        >
          <Lock className="h-5 w-5 text-accent" />
        </motion.div>
        <h1 className="text-center text-lg font-semibold">AI Brain is locked</h1>
        <p className="text-center text-xs text-muted mt-1 mb-5">
          Enter your passphrase to open your chats and knowledge base.
        </p>
        <motion.div key={shake} animate={shake ? { x: [0, -8, 8, -6, 6, 0] } : {}} transition={{ duration: 0.35 }}>
          <input
            autoFocus type="password" value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Passphrase"
            className="w-full rounded-lg bg-surface-2 border border-border px-3 py-2.5 text-sm focus:outline-none focus:border-accent transition-colors"
          />
        </motion.div>
        {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
        <motion.button
          whileTap={{ scale: 0.97 }} whileHover={{ scale: 1.01 }}
          disabled={busy || !password}
          className="mt-4 w-full h-10 rounded-lg bg-accent text-white text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Unlock <ArrowRight className="h-4 w-4" /></>}
        </motion.button>
      </motion.form>
    </div>
  );
}
