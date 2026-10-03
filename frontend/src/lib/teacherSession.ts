import {api2} from "@/lib/api2";
import {useAppStore} from "@/store/useAppStore";

let controller:AbortController|null=null;
let running:Promise<void>|null=null;

export function teacherSessionRunning(){return !!running}

export function stopTeacherSession(){
 controller?.abort();
 controller=null;
 running=null;
 useAppStore.getState().patchTeacherSession({busy:false});
}

export function startTeacherSession(topic:string){
 const clean=topic.trim();
 if(!clean||running)return running;
 const store=useAppStore.getState();
 store.patchTeacherSession({topic:clean,busy:true,error:"",plan:null,lessons:[],summary:null,startedAt:Date.now()});
 controller=new AbortController();
 const signal=controller.signal;
 running=(async()=>{
  try{
   await api2.teacherCurriculumStream(clean,(e:any)=>{
    const s=useAppStore.getState();
    if(e.type==="error"){s.patchTeacherSession({error:e.message||"Teacher session failed"});return}
    if(e.type==="plan"){s.patchTeacherSession({plan:e});return}
    if(e.type==="question"){
     useAppStore.setState(x=>({teacherSession:{...x.teacherSession,lessons:[...x.teacherSession.lessons,{id:e.lesson_id,subtopic:e.subtopic,question:e.question,turns:[]}]}}));
     return;
    }
    if(e.type==="thinking"){
     s.updateTeacherLesson(e.lesson_id,l=>({...l,turns:[...l.turns.filter(t=>!t.thinking),{actor:e.actor,label:e.actor==="teacher"?"API Teacher":"Local AI",thinking:e.detail}]}));
     return;
    }
    if(e.type==="message"){
     s.updateTeacherLesson(e.lesson_id,l=>({...l,turns:[...l.turns.filter(t=>!t.thinking),{actor:e.actor,label:e.label,content:e.content}]}));
     return;
    }
    if(e.type==="lesson_done"){s.updateTeacherLesson(e.lesson_id,l=>({...l,verified:e.verified}));return}
    if(e.type==="done"){s.patchTeacherSession({summary:e});return}
   },signal);
  }catch(e:any){
   if(e?.name!=="AbortError")useAppStore.getState().patchTeacherSession({error:e?.message||"Teacher session failed"});
  }finally{
   controller=null;running=null;
   useAppStore.getState().patchTeacherSession({busy:false});
  }
 })();
 return running;
}
