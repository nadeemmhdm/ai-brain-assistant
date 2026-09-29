"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { ArrowUp, Search, ChevronDown, Check, Square, Mic, Telescope, WifiOff } from "lucide-react";
import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { SkillPicker } from "./SkillPicker";
import { cn } from "@/lib/utils";
import type { ModelChoice, ReasoningLevel, SearchMode } from "@/lib/api";

const REASONING_LEVELS: { id: ReasoningLevel; label: string }[] = [
  { id: "off", label: "Off" },
  { id: "low", label: "Low" },
  { id: "medium", label: "Medium" },
  { id: "high", label: "High" },
  { id: "max", label: "Max" },
];

const MODELS: { id: ModelChoice; label: string; description: string }[] = [
  { id: "main", label: "Main model", description: "Best answers — chat, research, writing" },
  { id: "agent", label: "Fast model", description: "Quicker, lighter — simple questions" },
];

const SEARCH_MODES: { id: SearchMode; label: string; description: string }[] = [
  { id: "off", label: "Search off", description: "Answer from what I know and have learned" },
  { id: "quick", label: "Quick search", description: "Check my memory, then read the top web pages" },
  { id: "deep", label: "Deep research", description: "Several searches, more pages, cross-checked" },
];

function Dropdown<T extends string>({
  value, options, onChange, renderLabel, align = "right",
}: {
  align?: "left" | "right";
  value: T;
  options: { id: T; label: string; description?: string }[];
  onChange: (v: T) => void;
  renderLabel: (opt: { id: T; label: string }) => React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onDoc = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);
  const current = options.find((o) => o.id === value) || options[0];
  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="h-8 px-2.5 rounded-md text-xs font-medium text-muted hover:text-ink hover:bg-surface-2 flex items-center gap-1"
      >
        {renderLabel(current)}
        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className={cn("absolute bottom-full mb-2 w-64 bg-surface border border-border rounded-lg shadow-xl z-20 p-1.5", align === "left" ? "left-0" : "right-0")}>
          {options.map((opt) => (
            <button
              key={opt.id}
              onClick={() => { onChange(opt.id); setOpen(false); }}
              className={cn(
                "w-full text-left px-2.5 py-2 rounded-md hover:bg-surface-2 flex items-center justify-between text-sm",
                opt.id === value && "bg-surface-2"
              )}
            >
              <div>
                <div className="font-medium">{opt.label}</div>
                {opt.description && <div className="text-[11px] text-muted">{opt.description}</div>}
              </div>
              {opt.id === value && <Check className="h-3.5 w-3.5 text-accent flex-shrink-0" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function ChatComposer({
  onSend, disabled, streaming, onStop,
  model, setModel, reasoningLevel, setReasoningLevel, searchMode, setSearchMode, offline, onVoice, aiName,
  skillId, skillName, onSkillChange,
  placeholder,
}: {
  skillId?: string | null;
  skillName?: string | null;
  onSkillChange?: (id: string | null, name: string | null) => void;
  offline?: boolean;
  onVoice?: () => void;
  aiName?: string;
  onSend: (text: string) => void;
  disabled?: boolean;
  streaming?: boolean;
  onStop?: () => void;
  model: ModelChoice;
  setModel: (m: ModelChoice) => void;
  reasoningLevel: ReasoningLevel;
  setReasoningLevel: (r: ReasoningLevel) => void;
  searchMode: SearchMode;
  setSearchMode: (m: SearchMode) => void;
  placeholder?: string;
}) {
  const [message, setMessage] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = "auto";
      ref.current.style.height = `${Math.min(ref.current.scrollHeight, 160)}px`;
    }
  }, [message]);

  const send = useCallback(() => {
    if (!message.trim() || disabled) return;
    onSend(message);
    onSkillChange?.(null, null);
    setMessage("");
    if (ref.current) ref.current.style.height = "auto";
  }, [message, disabled, onSend]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="bg-surface-2 border border-border rounded-xl shadow-lg flex flex-col">
        <textarea
          ref={ref}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder || (skillName ? `${skillName}… (message ${aiName || "Nila"})` : `Message ${aiName || "Nila"}…`)}
          rows={1}
          className="flex-1 min-h-[56px] max-h-[160px] w-full p-4 resize-none bg-transparent text-ink placeholder:text-muted text-sm sm:text-base focus:outline-none custom-scrollbar"
        />
        <div className="flex items-center gap-1.5 justify-between w-full px-3 pb-2.5 flex-wrap">
          <div className="flex items-center gap-1.5">
            <Dropdown
              value={searchMode}
              options={SEARCH_MODES}
              onChange={setSearchMode}
              renderLabel={(o) => (
                <span className={cn("flex items-center gap-1.5", searchMode !== "off" && "text-accent")}>
                  {searchMode === "deep" ? <Telescope className="h-3.5 w-3.5" /> : <Search className="h-3.5 w-3.5" />}{o.label}
                </span>
              )}
              align="left"
            />
            {onSkillChange && <SkillPicker skillId={skillId ?? null} onChange={onSkillChange} />}
            {offline && (
              <span className="flex items-center gap-1 text-[11px] text-amber-500" title="Offline: only saved knowledge is used">
                <WifiOff className="h-3.5 w-3.5" /> Offline
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <Dropdown
              value={reasoningLevel}
              options={REASONING_LEVELS}
              onChange={setReasoningLevel}
              renderLabel={(o) => <>Reasoning: {o.label}</>}
            />
            <Dropdown
              value={model}
              options={MODELS}
              onChange={setModel}
              renderLabel={(o) => <>{o.label}</>}
            />
            {onVoice && (
              <motion.button whileTap={{ scale: 0.88 }} whileHover={{ scale: 1.08 }} onClick={onVoice} title={`Talk to ${aiName || "Nila"}`}
                className="h-9 w-9 rounded-md flex items-center justify-center text-muted hover:text-accent hover:bg-surface">
                <Mic className="h-[18px] w-[18px]" />
              </motion.button>
            )}
            {streaming ? (
              <Button size="icon" variant="destructive" onClick={onStop} title="Stop generating">
                <Square className="h-4 w-4" />
              </Button>
            ) : (
              <Button size="icon" onClick={send} disabled={!message.trim() || disabled} title="Send">
                <ArrowUp className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
