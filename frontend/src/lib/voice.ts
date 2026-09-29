import { api2 } from "./api2";
import { matchWake } from "./wake";
export { matchWake };

export type Engine = "local" | "browser";
const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
export const browserSttSupported = !!SR;
export const browserTtsSupported = "speechSynthesis" in window;

/** auto -> local voice if a speech model AND a voice are installed, else the browser's built-in voice. */
export async function resolveEngine(pref: string): Promise<{ engine: Engine; note?: string }> {
  if (pref === "browser") return { engine: "browser" };
  try {
    const st = await api2.voiceStatus();
    const ready = st.stt.installed.length > 0 && st.tts.voices.length > 0;
    if (ready) return { engine: "local" };
    if (pref === "local") return { engine: "browser", note: "Local voice isn't set up yet, using the browser voice. (Models → Voice)" };
  } catch { /* backend unreachable: fall through */ }
  return { engine: "browser" };
}

// ------------------------------------------------------------------ speaking
let currentAudio: HTMLAudioElement | null = null;
let stopFlag = 0;

export function stopSpeaking() {
  stopFlag++;
  currentAudio?.pause(); currentAudio = null;
  if (browserTtsSupported) speechSynthesis.cancel();
}

export function splitSentences(text: string): string[] {
  const clean = text.replace(/```[\s\S]*?```/g, " ").replace(/\[(\d{1,2})\]/g, "").replace(/[*_`#>]/g, "").replace(/\[([^\]]+)\]\([^)]+\)/g, "$1").replace(/https?:\/\/\S+/g, "").trim();
  const parts = clean.match(/[^.!?\n]+[.!?]*/g) || [];
  const out: string[] = [];
  for (const p of parts.map((x) => x.trim()).filter(Boolean)) {
    if (out.length && out[out.length - 1].length < 40) out[out.length - 1] += " " + p; else out.push(p);
  }
  return out;
}

function playBlob(blob: Blob, token: number): Promise<void> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(blob);
    const a = new Audio(url); currentAudio = a;
    const done = () => { URL.revokeObjectURL(url); resolve(); };
    a.onended = done; a.onerror = done;
    if (token !== stopFlag) return done();
    a.play().catch(done);
  });
}

function browserSay(text: string, voiceName?: string): Promise<void> {
  return new Promise((resolve) => {
    const u = new SpeechSynthesisUtterance(text);
    const v = speechSynthesis.getVoices().find((x) => x.name === voiceName);
    if (v) u.voice = v;
    u.onend = () => resolve(); u.onerror = () => resolve();
    speechSynthesis.speak(u);
  });
}

/** Speaks text sentence by sentence; with the local engine the next sentence is synthesised while the current one plays. */
export async function speak(text: string, engine: Engine, voice?: string): Promise<void> {
  const token = ++stopFlag;
  const sentences = splitSentences(text);
  if (!sentences.length) return;
  if (engine === "browser") {
    for (const s of sentences) { if (token !== stopFlag) return; await browserSay(s, voice); }
    return;
  }
  let next: Promise<Blob> | null = api2.tts(sentences[0], voice);
  for (let i = 0; i < sentences.length; i++) {
    const blob = await next!;
    next = i + 1 < sentences.length ? api2.tts(sentences[i + 1], voice) : null;
    if (token !== stopFlag) return;
    await playBlob(blob, token);
  }
}

// ------------------------------------------------------------------ listening
export interface ListenOpts { engine: Engine; onLevel?: (v: number) => void; signal?: AbortSignal; maxMs?: number; silenceMs?: number; startTimeoutMs?: number }

/** Listens until the person stops talking and returns the text ("" if nothing was said). */
export async function listen(o: ListenOpts): Promise<string> {
  if (o.engine === "browser") return listenBrowser(o);
  const blob = await recordUntilSilence(o);
  if (!blob) return "";
  return (await api2.stt(blob)).trim();
}

function listenBrowser(o: ListenOpts): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!SR) return reject(new Error("This browser has no speech recognition. Use Chrome/Edge, or set up local voice in Models → Voice."));
    const r = new SR(); r.lang = navigator.language || "en-US"; r.interimResults = false; r.maxAlternatives = 1;
    let text = "";
    r.onresult = (e: any) => { text = Array.from(e.results).map((x: any) => x[0].transcript).join(" "); };
    r.onerror = (e: any) => { if (e.error === "no-speech" || e.error === "aborted") resolve(""); else reject(new Error(e.error === "not-allowed" ? "Microphone permission was denied." : `Speech recognition error: ${e.error}`)); };
    r.onend = () => resolve(text.trim());
    o.signal?.addEventListener("abort", () => r.abort());
    r.start();
  });
}

async function recordUntilSilence(o: ListenOpts): Promise<Blob | null> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  const ctx = new AudioContext(); const src = ctx.createMediaStreamSource(stream);
  const an = ctx.createAnalyser(); an.fftSize = 1024; src.connect(an);
  const buf = new Uint8Array(an.fftSize);
  const rec = new MediaRecorder(stream); const chunks: Blob[] = [];
  rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  rec.start(200);
  const THRESH = 0.035, silenceMs = o.silenceMs ?? 1100, maxMs = o.maxMs ?? 20000, startTimeout = o.startTimeoutMs ?? 8000;
  const t0 = performance.now(); let lastVoice = 0, heard = false;
  await new Promise<void>((resolve) => {
    const tick = () => {
      an.getByteTimeDomainData(buf);
      let sum = 0; for (const b of buf) { const v = (b - 128) / 128; sum += v * v; }
      const rms = Math.sqrt(sum / buf.length); o.onLevel?.(Math.min(1, rms * 8));
      const now = performance.now();
      if (rms > THRESH) { heard = true; lastVoice = now; }
      if (o.signal?.aborted || now - t0 > maxMs || (heard && now - lastVoice > silenceMs) || (!heard && now - t0 > startTimeout)) return resolve();
      requestAnimationFrame(tick);
    };
    tick();
  });
  await new Promise<void>((r) => { rec.onstop = () => r(); rec.stop(); });
  stream.getTracks().forEach((t) => t.stop()); ctx.close();
  return heard && !o.signal?.aborted ? new Blob(chunks, { type: rec.mimeType || "audio/webm" }) : null;
}

// ------------------------------------------------------------------ wake word ("Hey Nila")
/** Keeps listening in the background (while this tab is open) and calls onWake when it hears "Hey <name>". */
export function startWakeListener(name: string, engine: Engine, onWake: (rest: string) => void, onError?: (e: Error) => void): () => void {
  const ac = new AbortController();
  (async () => {
    while (!ac.signal.aborted) {
      try {
        const text = await listen({ engine, signal: ac.signal, maxMs: 5000, silenceMs: 700, startTimeoutMs: 60000 });
        if (ac.signal.aborted) return;
        const m = matchWake(text, name);
        if (m.matched) { onWake(m.rest); return; }
      } catch (e: any) {
        if (ac.signal.aborted) return;
        onError?.(e); return;
      }
      await new Promise((r) => setTimeout(r, 150));
    }
  })();
  return () => ac.abort();
}
