import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Mic, MicOff, X, Volume2, VolumeX, Loader2 } from "lucide-react";
import { listen, speak, stopSpeaking, resolveEngine, type Engine } from "@/lib/voice";
import { toast } from "@/store/useToast";

type Phase = "starting" | "listening" | "thinking" | "speaking" | "paused";

/** Voice-to-voice conversation: listen -> send -> speak the reply -> listen again. */
export function VoiceMode({ aiName, enginePref, voiceName, initialText, onSend, onClose }: {
  aiName: string; enginePref: string; voiceName?: string; initialText?: string;
  onSend: (text: string) => Promise<string | null>; onClose: () => void;
}) {
  const [phase, setPhase] = useState<Phase>("starting");
  const [level, setLevel] = useState(0);
  const [heard, setHeard] = useState(""); const [reply, setReply] = useState("");
  const [engine, setEngine] = useState<Engine>("browser");
  const alive = useRef(true); const ac = useRef<AbortController | null>(null); const paused = useRef(false);

  useEffect(() => {
    alive.current = true;
    (async () => {
      const r = await resolveEngine(enginePref);
      if (r.note) toast.info(r.note);
      setEngine(r.engine);
      let pending = initialText || "";
      while (alive.current) {
        if (paused.current) { setPhase("paused"); await new Promise((x) => setTimeout(x, 300)); continue; }
        try {
          let text = pending; pending = "";
          if (!text) {
            setPhase("listening"); ac.current = new AbortController();
            text = await listen({ engine: r.engine, onLevel: setLevel, signal: ac.current.signal });
            setLevel(0);
          }
          if (!alive.current) return;
          if (!text) continue;
          setHeard(text); setReply(""); setPhase("thinking");
          const answer = await onSend(text);
          if (!alive.current) return;
          if (answer) { setReply(answer); setPhase("speaking"); await speak(answer, r.engine, voiceName); }
        } catch (e: any) {
          toast.error(e.message || "Voice error"); paused.current = true;
        }
      }
    })();
    return () => { alive.current = false; ac.current?.abort(); stopSpeaking(); };
  }, []); // eslint-disable-line

  const label = { starting: "Getting ready…", listening: "Listening…", thinking: `${aiName} is thinking…`, speaking: `${aiName} is speaking`, paused: "Microphone paused" }[phase];
  const size = phase === "listening" ? 1 + level * 0.9 : phase === "speaking" ? 1.15 : 1;

  return (
    <motion.div className="fixed inset-0 z-[55] bg-canvas/95 backdrop-blur flex flex-col items-center justify-center gap-8 p-6"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <button onClick={onClose} className="absolute top-4 right-4 text-muted hover:text-ink" aria-label="Close voice mode"><X className="h-6 w-6" /></button>
      <div className="relative h-40 w-40 flex items-center justify-center">
        {[0, 1, 2].map((i) => (
          <motion.span key={i} className="absolute inset-0 rounded-full bg-accent/20"
            animate={phase === "speaking" || phase === "thinking" ? { scale: [1, 1.5 + i * 0.25], opacity: [0.5, 0] } : { scale: size + i * 0.08, opacity: 0.25 - i * 0.06 }}
            transition={phase === "speaking" || phase === "thinking" ? { repeat: Infinity, duration: 1.8, delay: i * 0.4 } : { type: "spring", stiffness: 200, damping: 18 }} />
        ))}
        <motion.div className="relative h-24 w-24 rounded-full bg-accent flex items-center justify-center shadow-xl"
          animate={{ scale: size }} transition={{ type: "spring", stiffness: 260, damping: 16 }}>
          {phase === "thinking" || phase === "starting" ? <Loader2 className="h-9 w-9 text-white animate-spin" />
            : phase === "speaking" ? <Volume2 className="h-9 w-9 text-white" /> : phase === "paused" ? <MicOff className="h-9 w-9 text-white" /> : <Mic className="h-9 w-9 text-white" />}
        </motion.div>
      </div>
      <div className="text-center max-w-md min-h-[110px]">
        <p className="text-lg font-medium">{label}</p>
        <AnimatePresence mode="wait">
          <motion.p key={heard + reply} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="text-sm text-muted mt-2 line-clamp-4">
            {reply ? reply : heard ? `“${heard}”` : `Say something to ${aiName}…`}
          </motion.p>
        </AnimatePresence>
        <p className="text-[11px] text-muted mt-3">{engine === "local" ? "Local voice (works offline)" : "Browser voice — speech recognition may use the internet"}</p>
      </div>
      <div className="flex gap-3">
        <button onClick={() => { paused.current = !paused.current; if (paused.current) ac.current?.abort(); setPhase(paused.current ? "paused" : "listening"); }}
          className="h-11 px-4 rounded-full border border-border text-sm flex items-center gap-2 hover:bg-surface-2">
          {paused.current ? <Mic className="h-4 w-4" /> : <MicOff className="h-4 w-4" />} {paused.current ? "Resume" : "Mute mic"}
        </button>
        <button onClick={() => { stopSpeaking(); }} className="h-11 px-4 rounded-full border border-border text-sm flex items-center gap-2 hover:bg-surface-2">
          <VolumeX className="h-4 w-4" /> Stop talking
        </button>
      </div>
    </motion.div>
  );
}
