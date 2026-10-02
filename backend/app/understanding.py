"""Local query-understanding helpers.

No network/API calls. The original user message is never replaced in storage;
the normalized form is only an additional retrieval/search signal.
"""
import re
from . import llm_client

SPACE=re.compile(r"\s+")
FOLLOWUP=re.compile(r"^(it|that|this|they|them|he|she|there|same|again|why|how|what about|and)\b",re.I)

def normalize(text:str)->str:
    text=text.strip().replace("\u200b","")
    text=SPACE.sub(" ",text)
    return text[:8000]

def retrieval_query(text:str, recent:list[dict])->str:
    q=normalize(text)
    if len(q.split())>=5 and not FOLLOWUP.search(q): return q
    prior=[m.get("content","") for m in recent[-4:] if m.get("role")=="user" and m.get("content")]
    if prior: return f"{prior[-1][:500]} | follow-up: {q}"
    return q

async def clarify_query(text:str,recent:list[dict],model_online:bool)->str:
    """Cheap local rewrite for noisy/ambiguous wording; preserves meaning."""
    q=retrieval_query(text,recent)
    if not model_online or len(q)>1800: return q
    raw=await llm_client.complete("agent",[
      {"role":"system","content":"Rewrite the user's request as one precise retrieval query. Preserve names, numbers, language and intent. Resolve pronouns only from the supplied recent context. Do not answer. Output only the rewritten query."},
      {"role":"user","content":f"Recent context: {recent[-4:]}\nUser request: {text}"}
    ],"off")
    out=normalize(raw)
    return out if 3<=len(out)<=1200 else q
