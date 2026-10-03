"""Turn-aware local query understanding for continuous conversations."""
import re
from . import llm_client
SPACE=re.compile(r"\s+")
FOLLOWUP=re.compile(r"^(it|that|this|they|them|he|she|there|same|again|why|how|what about|and|no|yes|correct|wrong|actually)\b",re.I)
CORRECTION=re.compile(r"\b(wrong|incorrect|not correct|that's not|that is not|actually|correct answer|correction|തെറ്റ്|തെറ്റാണ്|ശരിയായ|അല്ല)\b",re.I)

def normalize(text:str)->str:
    return SPACE.sub(" ",text.strip().replace("\u200b",""))[:8000]

def recent_turn_context(recent:list[dict],limit:int=6)->str:
    turns=[]
    for m in recent[-limit:]:
        role=m.get("role"); text=normalize(m.get("content",""))
        if role in ("user","assistant") and text: turns.append(f"{role}: {text[:700]}")
    return "\n".join(turns)

def is_correction(text:str)->bool:
    return bool(CORRECTION.search(normalize(text)))

def retrieval_query(text:str,recent:list[dict])->str:
    q=normalize(text)
    contextual=len(q.split())<8 or bool(FOLLOWUP.search(q)) or is_correction(q)
    if not contextual: return q
    ctx=recent_turn_context(recent,4)
    return f"{ctx}\ncurrent user follow-up: {q}" if ctx else q

async def clarify_query(text:str,recent:list[dict],model_online:bool)->str:
    q=retrieval_query(text,recent)
    if not model_online or len(q)>2600: return q
    ctx=recent_turn_context(recent,6)
    raw=await llm_client.complete("agent",[
      {"role":"system","content":"Rewrite the current user turn as one precise retrieval query using recent USER AND ASSISTANT turns. Preserve corrections, names, numbers, negations, language and intent. If the user says the assistant was wrong, include the claim being corrected. Do not answer. Output only the rewritten query."},
      {"role":"user","content":f"Recent conversation:\n{ctx}\n\nCurrent user turn: {text}"}
    ],"off")
    out=normalize(raw)
    return out if 3<=len(out)<=1600 else q
