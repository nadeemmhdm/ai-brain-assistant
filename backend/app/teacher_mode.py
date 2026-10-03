"""Interactive local-student/cloud-teacher learning loop."""
import asyncio, json, re, httpx
from . import cloud_training, llm_client, brain

def _cloud_json_sync(messages):
    _,cfg,key=cloud_training._active()
    url=cloud_training.chat_completions_url(cfg)
    with httpx.Client(timeout=90,follow_redirects=False) as client:
        r=client.post(url,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
          json={"model":cfg["model"],"messages":messages,"temperature":0.1})
    r.raise_for_status()
    raw=r.json()["choices"][0]["message"]["content"].strip()
    m=re.search(r"\{.*\}",raw,re.S)
    if not m: raise RuntimeError("Teacher did not return structured JSON")
    parsed = json.loads(m.group(0))
    if not isinstance(parsed, dict): raise RuntimeError("Teacher returned invalid structured JSON")
    return parsed

async def _cloud_json(messages):
    return await asyncio.to_thread(_cloud_json_sync, messages)

async def lesson(topic:str,question:str)->dict:
    student=(await llm_client.complete("main",[
      {"role":"system","content":"You are the local student model. Answer accurately and concisely."},
      {"role":"user","content":question}], "medium")).strip()
    review=await _cloud_json([
      {"role":"system","content":"You are a strict AI teacher. Return JSON only: {correct:boolean, feedback:string, corrected_answer:string}. Do not claim certainty when unsure."},
      {"role":"user","content":f"Topic: {topic} | Question: {question} | Local student's answer: {student}"}])
    feedback=str(review.get("feedback",""))[:8000]
    corrected=str(review.get("corrected_answer",""))[:12000]
    retry=student
    if not bool(review.get("correct")):
        retry=(await llm_client.complete("main",[
          {"role":"system","content":"You are the local student. Learn from the teacher feedback for this turn. Produce a corrected answer; do not merely repeat the feedback."},
          {"role":"user","content":f"Question: {question} | Your first answer: {student} | Teacher feedback: {feedback} | Teacher proposed correction: {corrected}"}],"medium")).strip()
    final=await _cloud_json([
      {"role":"system","content":"Validate the student's revised answer. Return JSON only: {verified:boolean, feedback:string, canonical_answer:string}. Set verified=false if materially wrong, incomplete, or uncertain."},
      {"role":"user","content":f"Topic: {topic} | Question: {question} | Revised local answer: {retry}"}])
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

TEACHER_PLAN_PROMPT = (
    "Design a bounded factual curriculum for the supplied public topic. Return JSON only: "
    "{summary:string, subtopics:[{name:string, question:string}]}. "
    "Return EXACTLY 5 distinct subtopics, each with ONE comprehensive factual question. "
    "Do not include a definition/overview subtopic because the system teaches that first. "
    "Choose the five most important dimensions needed to understand the topic. "
    "Prioritize current knowledge where facts can change. Never request or infer user identity, "
    "chats, files, memories, credentials, or private data."
)

FINAL_VALIDATION_PROMPT = (
    "You are the final strict AI teacher and knowledge editor. Validate the revised student answer "
    "against what you taught in this lesson. Return JSON only: "
    "{verified:boolean, feedback:string, canonical_answer:string}. "
    "If verified, canonical_answer must be a polished, accurate, standalone knowledge note that "
    "fully answers the question and consolidates the useful factual teaching/corrections from this "
    "lesson. Remove conversational wording, repetition, grading language and uncertainty that is "
    "not part of the fact itself. Do not add unsupported facts. If materially wrong, incomplete, "
    "or uncertain, set verified=false."
)

def _bounded_plan(plan: dict, topic: str) -> list[dict]:
    raw = plan.get("subtopics") if isinstance(plan.get("subtopics"), list) else []
    out = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()[:200]
        q = str(item.get("question") or "").strip()
        if not q:
            qs = item.get("questions") if isinstance(item.get("questions"), list) else []
            q = str(qs[0]).strip() if qs else ""
        key = name.casefold()
        if not name or not q or key in seen:
            continue
        seen.add(key)
        out.append({"name": name, "question": q[:4000]})
        if len(out) == 5:
            break
    if len(out) != 5:
        raise RuntimeError(
            f"API Teacher must return exactly 5 valid subtopics for '{topic}'. "
            "Please retry the Teacher session."
        )
    return out

async def _run_lesson(topic: str, subtopic: str, question: str) -> dict:
    student = (await llm_client.complete("main", [
        {"role": "system", "content": "You are the local student model. Answer accurately and concisely."},
        {"role": "user", "content": question},
    ], "medium")).strip()
    review = await _cloud_json([
        {"role": "system", "content": (
            "You are a strict AI teacher. Teach the important factual material needed to answer the "
            "question, then assess the student's answer. Return JSON only: "
            "{correct:boolean, feedback:string, corrected_answer:string}. "
            "corrected_answer should consolidate the accurate lesson content. Do not claim certainty when unsure."
        )},
        {"role": "user", "content": f"Topic: {topic} | Subtopic: {subtopic} | Question: {question} | Local student's answer: {student}"},
    ])
    feedback = str(review.get("feedback", ""))[:8000]
    corrected = str(review.get("corrected_answer", ""))[:12000]
    retry = student
    if not bool(review.get("correct")):
        retry = (await llm_client.complete("main", [
            {"role": "system", "content": (
                "You are the local student. Learn all useful factual points from the teacher feedback "
                "and proposed correction. Produce one complete corrected answer."
            )},
            {"role": "user", "content": (
                f"Question: {question} | Your first answer: {student} | "
                f"Teacher feedback: {feedback} | Teacher proposed correction: {corrected}"
            )},
        ], "medium")).strip()
    final = await _cloud_json([
        {"role": "system", "content": FINAL_VALIDATION_PROMPT},
        {"role": "user", "content": (
            f"Topic: {topic} | Subtopic: {subtopic} | Question: {question} | "
            f"First student answer: {student} | Teacher feedback: {feedback} | "
            f"Teacher correction: {corrected} | Revised student answer: {retry}"
        )},
    ])
    verified = bool(final.get("verified"))
    canonical = str(final.get("canonical_answer") or "").strip()[:16000]
    kid = None
    if verified and canonical:
        kid = brain.add_knowledge(
            topic, subtopic, question, canonical,
            (canonical[:200] + "...") if len(canonical) > 200 else canonical, [],
            verification_status="teacher_verified",
            conflict={
                "provenance": "cloud_teacher",
                "provider": cloud_training.status()["active_provider"],
                "note": "Teacher-model validation; not independent web-source verification.",
            },
        )
    return {
        "topic": topic, "subtopic": subtopic, "question": question,
        "student_answer": student, "review": review, "student_retry": retry,
        "final_review": final, "verified": verified, "brain_id": kid,
        "canonical_answer": canonical,
        "provider": cloud_training.status()["active_provider"],
    }

async def lesson(topic:str,question:str)->dict:
    return await _run_lesson(topic, "Teacher Mode", question)

async def curriculum(topic:str)->dict:
    """Exactly one foundation lesson plus five bounded subtopic lessons."""
    topic = topic.strip()[:200]
    plan = await _cloud_json([
        {"role": "system", "content": TEACHER_PLAN_PROMPT},
        {"role": "user", "content": f"Public learning topic: {topic}"},
    ])
    subs = _bounded_plan(plan, topic)
    lessons = []
    foundation = await _run_lesson(
        topic, "Foundation", f"What is {topic}? Explain its definition, purpose, and essential context."
    )
    lessons.append({"name": "Foundation", "lessons": [foundation]})
    saved = 1 if foundation["verified"] else 0
    for sub in subs:
        r = await _run_lesson(topic, sub["name"], sub["question"])
        saved += 1 if r["verified"] else 0
        lessons.append({"name": sub["name"], "lessons": [r]})
    total = 6
    pct = round(saved * 100 / total)
    return {
        "topic": topic, "summary": str(plan.get("summary", ""))[:4000], "subtopics": lessons,
        "verified": saved, "total": total,
        "confidence": {"percent": pct, "grade": confidence_grade(pct)},
        "provider": cloud_training.status()["active_provider"],
        "privacy": "Only generated topic curriculum and local lesson answers were sent to the configured API teacher.",
    }

async def curriculum_events(topic: str):
    """Yield exactly 6 visible lessons: foundation + five subtopics."""
    topic = topic.strip()[:200]
    yield {"type": "status", "stage": "planning", "detail": "API Teacher is understanding the topic and building five subtopics…"}
    plan = await _cloud_json([
        {"role": "system", "content": TEACHER_PLAN_PROMPT},
        {"role": "user", "content": f"Public learning topic: {topic}"},
    ])
    subs = _bounded_plan(plan, topic)
    lessons = [
        {"name": "Foundation", "question": f"What is {topic}? Explain its definition, purpose, and essential context."},
        *subs,
    ]
    yield {
        "type": "plan", "topic": topic, "summary": str(plan.get("summary", ""))[:4000],
        "subtopics": [{"name": x["name"], "questions": [x["question"]]} for x in lessons],
    }
    saved = 0
    total = len(lessons)
    for index, spec in enumerate(lessons):
        lesson_id = str(index)
        name, q = spec["name"], spec["question"]
        yield {"type": "question", "lesson_id": lesson_id, "subtopic": name, "question": q}
        yield {"type": "thinking", "lesson_id": lesson_id, "actor": "student", "detail": "Local AI is thinking…"}
        student = (await llm_client.complete("main", [
            {"role": "system", "content": "You are the local student model. Answer accurately and concisely."},
            {"role": "user", "content": q},
        ], "medium")).strip()
        yield {"type": "message", "lesson_id": lesson_id, "actor": "student", "label": "Local AI", "content": student}

        yield {"type": "thinking", "lesson_id": lesson_id, "actor": "teacher", "detail": "API Teacher is teaching and reviewing…"}
        review = await _cloud_json([
            {"role": "system", "content": (
                "You are a strict AI teacher. Teach all important factual material for this lesson and "
                "assess the student's answer. Return JSON only: "
                "{correct:boolean, feedback:string, corrected_answer:string}. "
                "corrected_answer must consolidate the accurate lesson content."
            )},
            {"role": "user", "content": f"Topic: {topic} | Subtopic: {name} | Question: {q} | Local student's answer: {student}"},
        ])
        feedback = str(review.get("feedback", ""))[:8000]
        corrected = str(review.get("corrected_answer", ""))[:12000]
        teacher_text = feedback + (f"\n\nCorrection: {corrected}" if corrected and corrected != student else "")
        yield {"type": "message", "lesson_id": lesson_id, "actor": "teacher", "label": "API Teacher", "content": teacher_text}

        retry = student
        if not bool(review.get("correct")):
            yield {"type": "thinking", "lesson_id": lesson_id, "actor": "student", "detail": "Local AI is learning from the teacher…"}
            retry = (await llm_client.complete("main", [
                {"role": "system", "content": "Learn all factual points from the teacher and produce one complete corrected answer."},
                {"role": "user", "content": f"Question: {q} | First answer: {student} | Feedback: {feedback} | Correction: {corrected}"},
            ], "medium")).strip()
            yield {"type": "message", "lesson_id": lesson_id, "actor": "student", "label": "Local AI · retry", "content": retry}

        yield {"type": "thinking", "lesson_id": lesson_id, "actor": "teacher", "detail": "API Teacher is editing and validating the final knowledge…"}
        final = await _cloud_json([
            {"role": "system", "content": FINAL_VALIDATION_PROMPT},
            {"role": "user", "content": (
                f"Topic: {topic} | Subtopic: {name} | Question: {q} | First student answer: {student} | "
                f"Teacher feedback: {feedback} | Teacher correction: {corrected} | Revised student answer: {retry}"
            )},
        ])
        verified = bool(final.get("verified"))
        canonical = str(final.get("canonical_answer") or "").strip()[:16000]
        kid = None
        if verified and canonical:
            kid = brain.add_knowledge(
                topic, name, q, canonical,
                (canonical[:200] + "...") if len(canonical) > 200 else canonical, [],
                verification_status="teacher_verified",
                conflict={
                    "provenance": "cloud_teacher",
                    "provider": cloud_training.status()["active_provider"],
                    "note": "Teacher-model validation; not independent web-source verification.",
                },
            )
            saved += 1
        final_text = canonical or str(final.get("feedback") or "Validation completed.")[:12000]
        yield {"type": "message", "lesson_id": lesson_id, "actor": "teacher", "label": "API Teacher · final knowledge", "content": final_text}
        yield {"type": "lesson_done", "lesson_id": lesson_id, "verified": verified, "brain_id": kid}

    pct = round(saved * 100 / total) if total else 0
    yield {
        "type": "done", "topic": topic, "verified": saved, "total": total,
        "confidence": {"percent": pct, "grade": confidence_grade(pct)},
        "provider": cloud_training.status()["active_provider"],
    }
