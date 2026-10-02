import { Brain, Sparkles } from "lucide-react";
import { motion } from "motion/react";

function Dots() { return <span className="flex gap-1">{[0,1,2].map(i=><motion.span key={i} className="h-1 w-1 rounded-full bg-accent" animate={{y:[0,-4,0],opacity:[.35,1,.35]}} transition={{repeat:Infinity,duration:1.05,delay:i*.14}} />)}</span> }

export function ThinkingIndicator({ label = "Thinking" }: { label?: string }) {
  return <div className="ai-status-chip"><motion.span animate={{rotate:[0,8,-8,0]}} transition={{repeat:Infinity,duration:2}}><Brain className="h-4 w-4 text-accent"/></motion.span><span className="think-shimmer font-medium">{label}</span><Dots/></div>;
}
export function GeneratingIndicator({ label = "Preparing a response" }: { label?: string }) {
  return <motion.div initial={{opacity:0,y:4}} animate={{opacity:1,y:0}} className="ai-status-chip"><motion.span animate={{scale:[1,1.18,1],rotate:[0,8,0]}} transition={{repeat:Infinity,duration:1.8}}><Sparkles className="h-4 w-4 text-accent"/></motion.span><span className="think-shimmer font-medium">{label}</span><Dots/></motion.div>;
}