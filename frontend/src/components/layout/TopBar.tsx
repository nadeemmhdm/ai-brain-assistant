import { GraduationCap, Wifi, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";

export function TopBar({
  title, onOpenAutoLearn, offline,
}: { title: string; onOpenAutoLearn: () => void; offline: boolean }) {
  return (
    <div className="h-14 flex-shrink-0 border-b border-border flex items-center justify-between px-4">
      <h1 className="text-sm font-medium truncate">{title}</h1>
      <div className="flex items-center gap-2">
        <span className={`flex items-center gap-1 text-xs ${offline ? "text-amber-500" : "text-muted"}`}>
          {offline ? <WifiOff className="h-3.5 w-3.5" /> : <Wifi className="h-3.5 w-3.5" />}
          {offline ? "Offline mode" : "Online"}
        </span>
        <Button size="sm" variant="outline" className="gap-1.5" onClick={onOpenAutoLearn}>
          <GraduationCap className="h-3.5 w-3.5" /> Auto Learn
        </Button>
      </div>
    </div>
  );
}
