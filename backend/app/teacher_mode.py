"""Interactive local-student/cloud-teacher learning loop."""
import asyncio, json, re, httpx
from . import cloud_training, llm_client, brain

def _cloud_json_sync(messages):
    _,cfg,key=cloud_training._active()
    url=cfg["base_url"].rstrip("/")+"/chat/completions"
    with httpx.Client(timeout=90,follow_redirects=False) as client:
        r=client.post(url,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
          json={"model":cfg["model"],"messages":messages,"temperature":0.1})
    r.raise_for_status()
    raw=r.json()["choices"][0]["message"]["content"].strip()
    m=re.search(r"\{.*\}",raw,re.S)
    if not m: raise RuntimeError("Teacher did not return structured JSON")
    parsed = json.loads(m.group(0))\n    if not isinstance(parsed, dict): raise RuntimeError("Teacher returned invalid structured JSON")\n    return parsed\n\nasync def _cloud_json(messages):\n    return await asyncio.to_thread(_cloud_json_sync, messages)

async def lesson(topic:str,question:str)->dict:
    student=(await llm_client.complete("main",[
      {"role":"system","content":"You are the local student model. Answer accurately and concisely."},
      {"role":"user","content":question}], "medium")).strip()
    review=await _cloud_json([
      {"role":"system","content":"You are a strict AI teacher. Return JSON only: {correct:boolean, feedback:string, corrected_answer:string}. Do not claim certainty when unsure."},
      {"role":"user","content":f"Topic: {topic}\nQuestion: {question}\nLocal student's answer: {student}"}])
    feedback=str(review.get("feedback",""))[:8000]
    corrected=str(review.get("corrected_answer",""))[:12000]
    retry=student
    if not bool(review.get("correct")):
        retry=(await llm_client.complete("main",[
          {"role":"system","content":"You are the local student. Learn from the teacher feedback for this turn. Produce a corrected answer; do not merely repeat the feedback."},
          {"role":"user","content":f"Question: {question}\nYour first answer: {student}\nTeacher feedback: {feedback}\nTeacher proposed correction: {corrected}"}],"medium")).strip()
    final=await _cloud_json([
      {"role":"system","content":"Validate the student's revised answer. Return JSON only: {verified:boolean, feedback:string, canonical_answer:string}. Set verified=false if materially wrong, incomplete, or uncertain."},
      {"role":"user","content":f"Topic: {topic}\nQuestion: {question}\nRevised local answer: {retry}"}])
    verified=bool(final.get("verified"))
    canonical=str(final.get("canonical_answer") or retry).strip()[:16000]
    kid=None
    if verified and canonical:
        kid=brain.add_knowledge(topic,"Teacher Mode",question,canonical,
          "Validated through local-student/cloud-teacher review loop.",[],
          verification_status="teacher_verified",
          conflict={"provenance":"cloud_teacher","provider":cloud_training.status()["active_provider"],
                    "note":"Teacher-model validation; not independent web-source verification."})
    return {"topic":topic,"question":question,"student_answer":student,"review":review,
            "student_retry":retry,"final_review":final,"verified":verified,"brain_id":kid,
            "provider":cloud_training.status()["active_provider"]}

def confidence_grade(percent:int)->str:
    return "A" if percent>=85 else "B" if percent>=70 else "C" if percent>=50 else "D"

async def curriculum(topic:str)->dict:
    """Topic-only autonomous curriculum. Cloud sees generated lesson material only."""
    topic=topic.strip()[:200]
    plan=await _cloud_json([
      {"role":"system","content":"Design a compact factual curriculum. Return JSON only: {summary:string, subtopics:[{name:string, questions:[string]}]}. Use 4-8 subtopics and 2-4 concrete questions each. Prioritize current knowledge where facts can change. Never request or infer user identity, chats, files, memories, credentials, or private data."},
      {"role":"user","content":f"Public learning topic: {topic}"}])
    subs=plan.get("subtopics") if isinstance(plan.get("subtopics"),list) else []
    results=[]; saved=0; total=0
    for sub in subs[:8]:
        name=str(sub.get("name","")).strip()[:200]
        qs=sub.get("questions") if isinstance(sub.get("questions"),list) else []
        lessons=[]
        for q in qs[:4]:
            q=str(q).strip()[:4000]
            if not q: continue
            total+=1
            r=await lesson(f"{topic} / {name}",q)
            if r["verified"]: saved+=1
            lessons.append(r)
        if lessons: results.append({"name":name,"lessons":lessons})
    pct=round(saved*100/total) if total else 0
    return {"topic":topic,"summary":str(plan.get("summary",""))[:4000],"subtopics":results,
            "verified":saved,"total":total,"confidence":{"percent":pct,"grade":confidence_grade(pct)},
            "provider":cloud_training.status()["active_provider"],
            "privacy":"Only generated topic curriculum and local lesson answers were sent to the configured API teacher."}
