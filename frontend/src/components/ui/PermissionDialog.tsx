import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/button";
import { ShieldQuestion, AlertTriangle } from "lucide-react";

export type Grant = "once" | "chat" | "always";
const RISK: Record<string, string> = {
  read: "This reads data from your Google account.",
  write: "This creates or changes something in your Google account.",
  external: "This is visible to other people (they may get an email).",
  destructive: "This removes data.",
};

export function PermissionDialog({ req, onChoose, onCancel }: {
  req: { label: string; risk: string; summary?: string } | null;
  onChoose: (g: Grant) => void; onCancel: () => void;
}) {
  return (
    <Modal open={!!req} onClose={onCancel} title="Allow this action?" icon={<ShieldQuestion className="h-4 w-4 text-accent" />} maxWidth="max-w-sm">
      {req && (
        <div className="text-sm space-y-3">
          <p className="font-medium">{req.label}</p>
          {req.summary && <p className="text-xs text-muted whitespace-pre-wrap break-words">{req.summary}</p>}
          <p className={`text-xs flex items-center gap-1 ${req.risk === "read" ? "text-sky-500" : "text-amber-500"}`}>
            {req.risk !== "read" && <AlertTriangle className="h-3 w-3" />}{RISK[req.risk]}
          </p>
          <div className="grid gap-2">
            <Button onClick={() => onChoose("once")}>Allow this time</Button>
            <Button variant="outline" onClick={() => onChoose("chat")}>Allow this chat</Button>
            <Button variant="outline" onClick={() => onChoose("always")}>Always allow</Button>
            <Button variant="ghost" onClick={onCancel}>Deny</Button>
          </div>
          <p className="text-[11px] text-muted">“Always allow” can be undone any time in Settings → Google permissions.</p>
        </div>
      )}
    </Modal>
  );
}
