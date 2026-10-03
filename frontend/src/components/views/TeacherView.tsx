import {useEffect,useRef,useState} from "react";
import {GraduationCap,ArrowRight,CheckCircle2,AlertTriangle,Brain,Cloud,Bot,Square,Sparkles} from "lucide-react";
import {motion,AnimatePresence} from "motion/react";
import {api2} from "@/lib/api2";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Turn={actor:"student"|"teacher";label:string;content?:string;thinking?:string};
type Lesson={id:string;subtopic:string;question:string;turns:Turn[];verified?:boolean};

function Dots(){return <span className="inline-flex items-center gap-1">{[0,1,2].map(i=><motion.span key={i} className="h-1.5 w-1.5 rounded-full bg-current" animate={{opacity:[.25,1,.25],y:[0,-2,0]}} transition={{duration:1,repeat:Infinity,delay:i*.16}}/>)}</span>}

function Bubble({turn}:{turn:Turn}){
 const teacher=turn.actor==="teacher";
 return <motion.div initial={{opacity:0,y:10,scale:.98}} animate={{opacity:1,y:0,scale:1}} className={`flex gap-2.5 ${teacher?"justify-start":"justify-end"}`}>
  {teacher&&<div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-border bg-surface text-accent shadow-sm"><GraduationCap className="h-4 w-4"/></div>}
  <div className={`max-w-[82%] rounded-2xl px-4 py-3 shadow-sm ${teacher?"rounded-tl-md border border-border bg-surface":"rounded-tr-md bg-accent text-white"}`}>
   <div className={`mb-1 text-[10px] font-semibold uppercase tracking-wider ${teacher?"text-muted":"text-white/70"}`}>{turn.label}</div>
   {turn.thinking?<div className="flex min-w-36 items-center gap-2 text-sm"><Dots/><span className={teacher?"text-muted":"text-white/80"}>{turn.thinking}</span></div>:<div className={`teacher-chat-markdown text-sm leading-6 ${teacher?"text-ink":"text-white"}`}>
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
     h1:({children})=><h3 className="mb-2 mt-1 text-base font-bold">{children}</h3>,
     h2:({children})=><h3 className="mb-2 mt-1 text-[15px] font-bold">{children}</h3>,
     h3:({children})=><h4 className="mb-1.5 mt-1 font-semibold">{children}</h4>,
     p:({children})=><p className="my-1.5 first:mt-0 last:mb-0">{children}</p>,
     strong:({children})=><strong className="font-bold">{children}</strong>,
     em:({children})=><em className="italic">{children}</em>,
     ul:({children})=><ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
     ol:({children})=><ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
     li:({children})=><li className="pl-0.5">{children}</li>,
     blockquote:({children})=><blockquote className={`my-2 border-l-2 pl-3 italic ${teacher?"border-accent/40 text-muted":"border-white/40 text-white/85"}`}>{children}</blockquote>,
     code:({children,className})=>className?<code className={`my-2 block overflow-x-auto rounded-lg p-3 font-mono text-xs whitespace-pre-wrap ${teacher?"bg-canvas":"bg-black/20"}`}>{children}</code>:<code className={`rounded px-1 py-0.5 font-mono text-[12px] ${teacher?"bg-canvas":"bg-black/20"}`}>{children}</code>,
     a:({href,children})=><a href={href} target="_blank" rel="noopener noreferrer" className={`underline underline-offset-2 ${teacher?"text-accent":"text-white"}`}>{children}</a>,
    }}>{turn.content||"—"}</ReactMarkdown>
   </div>}
  </div>
  {!teacher&&<div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-accent/10 text-accent"><Bot className="h-4 w-4"/></div>}
 </motion.div>
}

export function TeacherView(){
 const [topic,setTopic]=useState(""); const [status,setStatus]=useState<any>(null);
 const [busy,setBusy]=useState(false); const [error,setError]=useState(""); const [plan,setPlan]=useState<any>(null);
 const [lessons,setLessons]=useState<Lesson[]>([]); const [summary,setSummary]=useState<any>(null);
 const abort=useRef<AbortController|null>(null); const bottom=useRef<HTMLDivElement>(null);
 useEffect(()=>{api2.teacherStatus().then(setStatus).catch(()=>{})},[]);
 useEffect(()=>{bottom.current?.scrollIntoView({behavior:"smooth",block:"nearest"})},[lessons,busy]);
 const active=status?.providers?.find((p:any)=>p.provider===status?.active_provider);

 function updateLesson(id:string,fn:(l:Lesson)=>Lesson){setLessons(xs=>xs.map(l=>l.id===id?fn(l):l))}
 async function teach(){
  if(!topic.trim()||busy)return; setBusy(true);setError("");setPlan(null);setLessons([]);setSummary(null);
  const ac=new AbortController(); abort.current=ac;
  try{
   await api2.teacherCurriculumStream(topic.trim(),(e:any)=>{
    if(e.type==="error"){setError(e.message||"Teacher session failed");return}
    if(e.type==="plan"){setPlan(e);return}
    if(e.type==="question"){setLessons(xs=>[...xs,{id:e.lesson_id,subtopic:e.subtopic,question:e.question,turns:[]}]);return}
    if(e.type==="thinking"){updateLesson(e.lesson_id,l=>({...l,turns:[...l.turns.filter(t=>!t.thinking),{actor:e.actor,label:e.actor==="teacher"?"API Teacher":"Local AI",thinking:e.detail}]}));return}
    if(e.type==="message"){updateLesson(e.lesson_id,l=>({...l,turns:[...l.turns.filter(t=>!t.thinking),{actor:e.actor,label:e.label,content:e.content}]}));return}
    if(e.type==="lesson_done"){updateLesson(e.lesson_id,l=>({...l,verified:e.verified}));return}
    if(e.type==="done"){setSummary(e);return}
   },ac.signal);
  }catch(e:any){if(e?.name!=="AbortError")setError(e.message||"Teacher session failed")}
  finally{setBusy(false);abort.current=null}
 }
 function stop(){abort.current?.abort();setBusy(false)}
 const done=lessons.filter(l=>l.verified!==undefined).length;
 return <main className="flex-1 overflow-y-auto bg-canvas p-4 sm:p-7">
  <div className="mx-auto max-w-5xl">
   <div className="mb-6 flex items-center gap-3"><div className="rounded-2xl bg-accent/10 p-3 text-accent"><GraduationCap/></div><div><h1 className="text-2xl font-semibold">Teacher Mode</h1><p className="text-sm text-muted">Watch your Local AI learn live from the API Teacher.</p></div></div>
   <section className="overflow-hidden rounded-3xl border border-border bg-surface shadow-sm">
    <div className="border-b border-border p-4 sm:p-5">
     <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted"><span className="flex items-center gap-2"><Cloud className="h-4 w-4"/>{active?<><b className="text-ink">{active.label}</b><span>· {active.model}</span></>:<>No API Teacher configured</>}</span>{busy&&<span className="flex items-center gap-2 text-accent"><Sparkles className="h-3.5 w-3.5 animate-pulse"/>Live lesson in progress</span>}</div>
     <div className="flex gap-2"><input value={topic} disabled={busy} onChange={e=>setTopic(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")void teach()}} placeholder="What should your AI learn?" className="min-w-0 flex-1 rounded-xl border border-border bg-canvas px-4 py-3 outline-none focus:border-accent/50"/>
      {busy?<button onClick={stop} className="flex items-center gap-2 rounded-xl border border-red-500/30 px-4 text-sm text-red-500"><Square className="h-4 w-4"/>Stop</button>:<button onClick={()=>void teach()} disabled={!active||!topic.trim()} className="flex items-center gap-2 rounded-xl bg-accent px-4 text-sm font-medium text-white disabled:opacity-40">Teach<ArrowRight className="h-4 w-4"/></button>}</div>
     <p className="mt-2 text-[11px] text-muted">Only the topic, generated curriculum and lesson answers are sent to the configured API teacher. Chat history, files, memories and credentials are not automatically attached.</p>
    </div>

    <div className="min-h-[420px] bg-canvas/60 p-4 sm:p-6">
     {!plan&&!busy&&!error&&<div className="flex min-h-[350px] flex-col items-center justify-center text-center text-muted"><div className="mb-3 rounded-2xl border border-border bg-surface p-4"><Bot className="h-7 w-7 text-accent"/></div><p className="font-medium text-ink">Local AI ↔ API Teacher</p><p className="mt-1 max-w-md text-sm">Enter a topic to start a visible learning conversation. Correct answers can be validated and saved to Brain.</p></div>}
     {busy&&!plan&&<div className="flex min-h-52 items-center justify-center"><div className="rounded-2xl border border-border bg-surface px-5 py-4 text-sm text-muted shadow-sm"><div className="mb-2 flex items-center gap-2 text-ink"><GraduationCap className="h-4 w-4 text-accent"/><b>API Teacher</b></div><Dots/> <span className="ml-2">Building the curriculum…</span></div></div>}
     {plan&&<div className="mb-5 rounded-2xl border border-border bg-surface p-4"><div className="flex items-center justify-between gap-3"><div><div className="text-xs font-medium uppercase tracking-wider text-accent">Curriculum</div><h2 className="mt-1 font-semibold">{plan.topic}</h2></div><span className="rounded-full bg-accent/10 px-3 py-1 text-xs font-medium text-accent">{done}/{lessons.length || "…"} lessons</span></div><p className="mt-2 text-sm text-muted">{plan.summary}</p></div>}
     <div className="space-y-5"><AnimatePresence>{lessons.map((lesson,i)=><motion.section key={lesson.id} initial={{opacity:0,y:14}} animate={{opacity:1,y:0}} className="rounded-2xl border border-border bg-canvas p-3 sm:p-4">
      <div className="mb-4 flex items-start justify-between gap-3"><div><div className="text-[10px] font-medium uppercase tracking-wider text-muted">{lesson.subtopic} · Lesson {i+1}</div><h3 className="mt-1 text-sm font-semibold">{lesson.question}</h3></div>{lesson.verified!==undefined&&(lesson.verified?<span className="flex shrink-0 items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-1 text-[11px] text-emerald-600"><CheckCircle2 className="h-3 w-3"/>Verified</span>:<span className="flex shrink-0 items-center gap-1 rounded-full bg-amber-500/10 px-2 py-1 text-[11px] text-amber-600"><AlertTriangle className="h-3 w-3"/>Review</span>)}</div>
      <div className="space-y-3">{lesson.turns.map((t,j)=><Bubble key={j} turn={t}/>)}</div>
      {lesson.verified&&<div className="mt-3 flex items-center gap-1.5 text-[11px] text-muted"><Brain className="h-3.5 w-3.5 text-accent"/>Verified knowledge saved to Brain</div>}
     </motion.section>)}</AnimatePresence></div>
     {summary&&<motion.div initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} className="mt-5 rounded-2xl border border-accent/20 bg-accent/5 p-4"><div className="flex items-center justify-between gap-3"><div><div className="text-xs font-medium text-accent">Learning complete</div><p className="mt-1 text-sm">{summary.verified} of {summary.total} lessons verified and saved.</p></div><b className="text-lg">{summary.confidence?.percent??0}% · {summary.confidence?.grade??"D"}</b></div></motion.div>}
     {error&&<div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-500">{error}</div>}
     <div ref={bottom}/>
    </div>
   </section>
  </div>
 </main>
}
