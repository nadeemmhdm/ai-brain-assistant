import {useEffect,useState} from "react";
import {GraduationCap,ArrowRight,CheckCircle2,AlertTriangle,Brain,Cloud} from "lucide-react";
import {api2} from "@/lib/api2";

export function TeacherView(){
 const [topic,setTopic]=useState("");
 const [status,setStatus]=useState<any>(null); const [result,setResult]=useState<any>(null);
 const [busy,setBusy]=useState(false); const [error,setError]=useState("");
 useEffect(()=>{api2.teacherStatus().then(setStatus).catch(()=>{})},[]);
 async function teach(){if(!topic.trim()||busy)return;setBusy(true);setError("");setResult(null);try{setResult(await api2.teacherCurriculum(topic.trim()))}catch(e:any){setError(e.message||"Teacher session failed")}finally{setBusy(false)}}
 const active=status?.providers?.find((p:any)=>p.provider===status?.active_provider);
 return <main className="flex-1 overflow-y-auto p-5 sm:p-8">
  <div className="mx-auto max-w-4xl">
   <div className="mb-7 flex items-start gap-3"><div className="rounded-2xl bg-accent/10 p-3 text-accent"><GraduationCap/></div><div><h1 className="text-2xl font-semibold">Teacher Mode</h1><p className="mt-1 text-sm text-muted">Enter one topic. Local AI and the API teacher build subtopics, validate lessons, and save verified knowledge.</p></div></div>
   <section className="rounded-2xl border border-border bg-surface p-5">
    <div className="mb-4 flex items-center gap-2 text-xs text-muted"><Cloud className="h-4 w-4"/>{active?<>Teacher: <b className="text-ink">{active.label} · {active.model}</b></>:<span>No active cloud teacher. Configure one in Training.</span>}</div>
    <input value={topic} onChange={e=>setTopic(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")void teach()}} placeholder="Enter a topic — e.g. Python, Cybersecurity, Physics" className="w-full rounded-xl border border-border bg-canvas px-4 py-3 outline-none focus:border-accent/50"/>
    <button onClick={()=>void teach()} disabled={busy||!active||!topic.trim()} className="mt-3 inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40">{busy?"Learning…":"Start autonomous learning"}<ArrowRight className="h-4 w-4"/></button>
    <p className="mt-3 text-[11px] text-muted">No chats, memories, Brain dump, files, profile or credentials are automatically attached. Topic curriculum and local lesson answers are sent to the configured API teacher.</p>
    {error&&<p className="mt-3 text-sm text-red-500">{error}</p>}
   </section>
   {result&&<section className="mt-5 space-y-4">
    <div className="rounded-2xl border border-border bg-surface p-4"><div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-semibold">{result.topic}</h2><p className="mt-1 text-sm text-muted">{result.summary}</p></div><b className="text-sm">{result.confidence?.percent??0}% · {result.confidence?.grade??"D"}</b></div><p className="mt-3 text-xs text-muted">{result.verified??0} of {result.total??0} lessons verified and saved.</p></div>
    {(result.subtopics||[]).map((sub:any,i:number)=><div key={i} className="rounded-2xl border border-border bg-surface p-4"><h3 className="mb-3 font-medium">{sub.name}</h3><div className="space-y-2">{(sub.lessons||[]).map((lesson:any,j:number)=><div key={j} className="rounded-xl border border-border/70 bg-canvas p-3"><div className="flex items-start gap-2">{lesson.verified?<CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500"/>:<AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500"/>}<div><p className="text-sm font-medium">{lesson.question}</p><p className="mt-1 text-xs text-muted">{lesson.final_review?.feedback||lesson.final_review?.canonical_answer||"Validation completed."}</p><p className="mt-2 flex items-center gap-1 text-[11px] text-muted"><Brain className="h-3 w-3"/>{lesson.verified?"Saved to Brain":"Not saved"}</p></div></div></div>)}</div></div>)}
   </section>}
  </div>
 </main>
}
