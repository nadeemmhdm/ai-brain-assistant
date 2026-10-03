"""Interactive local-student/cloud-teacher learning loop."""
import json, re, httpx
from . import cloud_training, llm_client, brain

def _cloud_json(messages):
    _,cfg,key=cloud_training._active()
    url=cfg["base_url"].rstrip("/")+"/chat/completions"
    with httpx.Client(timeout=90,follow_redirects=False) as client:
        r=client.post(url,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
          json={"model":cfg["model"],"messages":messages,"temperature":0.1})
    r.raise_for_status()
    raw=r.json()["choices"][0]["message"]["content"].strip()
    m=re.search(r"\{.*\}",raw,re.S)
    if not m: raise RuntimeError("Teacher did not return structured JSON")
    return json.loads(m.group(0))

async def lesson(topic:str,question:str)->dict:
    student=(await llm_client.complete("main",[
      {"role":"system","content":"You are the local student model. Answer accurately and concisely."},
      {"role":"user","content":question}], "medium")).strip()
    review=_cloud_json([
      {"role":"system","content":"You are a strict AI teacher. Return JSON only: {correct:boolean, feedback:string, corrected_answer:string}. Do not claim certainty when unsure."},
      {"role":"user","content":f"Topic: {topic}\nQuestion: {question}\nLocal student's answer: {student}"}])
    feedback=str(review.get("feedback",""))[:8000]
    corrected=str(review.get("corrected_answer",""))[:12000]
    retry=student
    if not bool(review.get("correct")):
        retry=(await llm_client.complete("main",[
          {"role":"system","content":"You are the local student. Learn from the teacher feedback for this turn. Produce a corrected answer; do not merely repeat the feedback."},
          {"role":"user","content":f"Question: {question}\nYour first answer: {student}\nTeacher feedback: {feedback}\nTeacher proposed correction: {corrected}"}],"medium")).strip()
    final=_cloud_json([
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
