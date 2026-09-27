import { Brain } from "lucide-react";

export function ThinkingIndicator({ label = "Thinking" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm py-1.5">
      <Brain className="h-4 w-4 text-accent" />
      <span className="think-shimmer font-medium">{label}</span>
      <span className="flex items-center gap-0.5 ml-0.5">
        <span className="think-dot h-1 w-1 rounded-full bg-accent inline-block" />
        <span className="think-dot h-1 w-1 rounded-full bg-accent inline-block" />
        <span className="think-dot h-1 w-1 rounded-full bg-accent inline-block" />
      </span>
    </div>
  );
}

export function GeneratingIndicator({ label = "Generating" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm py-1.5">
      <span className="think-shimmer font-medium">{label}</span>
      <span className="flex items-center gap-0.5 ml-0.5">
        <span className="think-dot h-1 w-1 rounded-full bg-muted inline-block" />
        <span className="think-dot h-1 w-1 rounded-full bg-muted inline-block" />
        <span className="think-dot h-1 w-1 rounded-full bg-muted inline-block" />
      </span>
    </div>
  );
}
