import { motion } from "motion/react";
import { GraduationCap, Wifi, WifiOff, PanelLeftClose, PanelLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export function TopBar({
  title, onOpenAutoLearn, offline, sidebarOpen, onToggleSidebar,
}: {
  title: string; onOpenAutoLearn: () => void; offline: boolean;
  sidebarOpen?: boolean; onToggleSidebar?: () => void;
}) {
  return (
    <div className="h-14 flex-shrink-0 border-b border-border flex items-center justify-between px-4 gap-2">
      <div className="flex items-center gap-2 min-w-0">
        {onToggleSidebar && (
          <motion.button
            whileTap={{ scale: 0.88 }} whileHover={{ scale: 1.08 }}
            onClick={onToggleSidebar}
            title={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
            className="h-8 w-8 flex-shrink-0 flex items-center justify-center rounded-md text-muted hover:text-ink hover:bg-surface-2"
          >
            {sidebarOpen ? <PanelLeftClose className="h-[18px] w-[18px]" /> : <PanelLeft className="h-[18px] w-[18px]" />}
          </motion.button>
        )}
        <h1 className="text-sm font-medium truncate">{title}</h1>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
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
