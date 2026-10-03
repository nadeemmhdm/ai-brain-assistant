import {useEffect,useState} from "react";
import {GraduationCap,ArrowRight,CheckCircle2,AlertTriangle,Brain,Cloud} from "lucide-react";
import {api2} from "@/lib/api2";

export function TeacherView(){
 const [topic,setTopic]=useState(""); const [question,setQuestion]=useState("");
 const [status,setStatus]=useState<any>(null); const [result,setResult]=useState<any>(null);
 const [busy,setBusy]=useState(false); const [error,setError]=useState("");
 useEffect(()=>{api2.teacherStatus().then(setStatus).catch(()=>{})},[]);
 async function teach(){if(!topic.trim()||!question.trim())return;setBusy(true);setError("");setResult(null);try{setResult(await api2.teacherLesson(topic,question))}catch(e:any){setError(e.message||"Teacher session failed")}finally{setBusy(false)}}
 const active=status?.providers?.find((p:any)=>p.provider===status?.active_provider);
 return <main className="flex-1 overflow-y-auto p-5 sm:p-8">
  <div className="mx-auto max-w-4xl">
   <div className="mb-7 flex items-start gap-3"><div className="rounded-2xl bg-accent/10 p-3 text-accent"><GraduationCap/></div><div><h1 className="text-2xl font-semibold">Teacher Mode</h1><p className="mt-1 text-sm text-muted">Your local model answers first. The configured cloud teacher reviews, explains, and verifies before a lesson can enter the Brain.</p></div></div>
   <section className="rounded-2xl border border-border bg-surface p-5">
    <div className="mb-4 flex items-center gap-2 text-xs text-muted"><Cloud className="h-4 w-4"/>{active?<>Teacher: <b className="text-ink">{active.label} · {active.model}</b></>:<span>No active cloud teacher. Configure one in Training.</span>}</div>
    <input value={topic} onChange={e=>setTopic(e.target.value)} placeholder="Topic — e.g. Python, Cybersecurity, Physics" className="mb-3 w-full rounded-xl border border-border bg-canvas px-4 py-3 outline-none focus:border-accent/50"/>
    <textarea value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask something you want the local AI to learn…" rows={4} className="w-full resize-none rounded-xl border border-border bg-canvas px-4 py-3 outline-none focus:border-accent/50"/>
    <button onClick={teach} disabled={busy||!active||!topic.trim()||!question.trim()} className="mt-3 inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40">{busy?"Teaching…":"Start lesson"}<ArrowRight className="h-4 w-4"/></button>
    {error&&<p className="mt-3 text-sm text-red-500">{error}</p>}
   </section>
   {result&&<section className="mt-5 space-y-3">
    <Step title="1 · Local AI answer" text={result.student_answer}/>
    <Step title="2 · Teacher review" text={result.review?.feedback||"No feedback"} good={result.review?.correct}/>
    {!result.review?.correct&&<Step title="3 · Local AI learned & retried" text={result.student_retry}/>}
    <Step title="4 · Final validation" text={result.final_review?.feedback||result.final_review?.canonical_answer} good={result.verified}/>
    <div className={"flex items-center gap-3 rounded-2xl border p-4 "+(result.verified?"border-emerald-500/30 bg-emerald-500/5":"border-amber-500/30 bg-amber-500/5")}>{result.verified?<><Brain className="text-emerald-500"/><div><b>Verified lesson saved to Brain</b><p className="text-xs text-muted">Stored as cloud-teacher verified provenance, not independent web verification.</p></div></>:<><AlertTriangle className="text-amber-500"/><div><b>Not saved</b><p className="text-xs text-muted">The final teacher validation did not pass.</p></div></>}</div>
   </section>}
  </div>
 </main>
}
function Step({title,text,good}:{title:string;text:string;good?:boolean}){return <div className="rounded-2xl border border-border bg-surface p-4"><div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted">{good&&<CheckCircle2 className="h-4 w-4 text-emerald-500"/>}{title}</div><p className="whitespace-pre-wrap text-sm leading-6">{text}</p></div>}
