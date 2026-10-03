"""Privacy-scoped cloud teacher providers for dataset distillation.

This module is deliberately NOT part of chat, memory, search, or normal Brain
retrieval. It can only receive one explicitly approved dataset item at a time.
Provider responses are saved locally; provider keys stay in the encrypted vault.
"""
import httpx
from urllib.parse import urlparse
from . import vault, db, dataset

PROVIDERS = {
    "openai": {"label": "OpenAI API", "base_url": "https://api.openai.com/v1", "default_model": "gpt-5.6-luna"},
    "ollama_cloud": {"label": "Ollama Cloud", "base_url": "https://ollama.com/v1", "default_model": "gpt-oss:120b-cloud"},
    "compatible": {"label": "OpenAI-compatible Cloud", "base_url": "", "default_model": ""},
}
ALLOWED_CONFIG = {"active", "model", "base_url"}
PREFIX = "cloud_teacher_"

def chat_completions_url(cfg):
    """Return a canonical OpenAI-compatible chat endpoint, including legacy config repair."""
    base=(cfg.get("base_url") or "").strip().rstrip("/")
    provider=cfg.get("provider")
    # Older builds allowed Ollama's native /api/chat endpoint to be saved as a base URL.
    # Teacher Mode uses the OpenAI-compatible protocol, so repair it transparently.
    if provider=="ollama_cloud":
        if base in {"https://ollama.com/api/chat","https://ollama.com/api"}:
            base="https://ollama.com/v1"
        elif base=="https://ollama.com":
            base="https://ollama.com/v1"
    if base.endswith("/chat/completions"):
        return base
    return base+"/chat/completions"

def _key(provider): return f"{PREFIX}key:{provider}"
def _cfg_key(provider): return f"{PREFIX}cfg:{provider}"

def _load_cfg(provider):
    with db.get_conn() as conn:
        row=conn.execute("SELECT value FROM kv_settings WHERE key=?",(_cfg_key(provider),)).fetchone()
    saved=db.loads(row["value"]) if row else {}
    meta=PROVIDERS[provider]
    return {"provider":provider,"label":meta["label"],"active":bool(saved.get("active",False)),
            "model":saved.get("model") or meta["default_model"],"base_url":saved.get("base_url") or meta["base_url"],
            "key_set":vault.has(_key(provider))}

def status():
    rows=[_load_cfg(p) for p in PROVIDERS]
    active=next((x["provider"] for x in rows if x["active"]),None)
    return {"active_provider":active,"providers":rows,
            "privacy":"Cloud training sends only explicitly approved dataset examples. Teacher Mode sends the topic/curriculum and local lesson answers needed for validation. Chat history, memory, the Brain database and local files are not automatically attached."}

def configure(provider, *, active=False, model="", base_url="", api_key=None):
    if provider not in PROVIDERS: raise ValueError("Unsupported training provider")
    if provider=="compatible":
        u=urlparse(base_url)
        if u.scheme!="https" or not u.netloc: raise ValueError("Custom cloud base URL must use HTTPS")
    if active:
        with db.get_conn() as conn:
            for p in PROVIDERS:
                cfg=_load_cfg(p); cfg["active"]=False
                conn.execute("INSERT INTO kv_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                             (_cfg_key(p),db.dumps({"active":False,"model":cfg["model"],"base_url":cfg["base_url"]})))
    cfg={"active":bool(active),"model":model.strip() or PROVIDERS[provider]["default_model"],
         "base_url":base_url.strip() or PROVIDERS[provider]["base_url"]}
    with db.get_conn() as conn:
        conn.execute("INSERT INTO kv_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (_cfg_key(provider),db.dumps(cfg)))
    if api_key is not None:
        if api_key.strip(): vault.put(_key(provider),api_key.strip())
        else: vault.delete(_key(provider))
    return _load_cfg(provider)

def clear_key(provider):
    if provider not in PROVIDERS: raise ValueError("Unsupported training provider")
    vault.delete(_key(provider))

def _active():
    s=status(); p=s["active_provider"]
    if not p: raise RuntimeError("No cloud training provider is active")
    cfg=_load_cfg(p)
    key=vault.get(_key(p))
    if not key: raise RuntimeError("The active cloud training provider has no API key")
    return p,cfg,key

def refine_example(instruction:str,input_text:str,output:str)->str:
    """Send ONLY this approved training example; no ambient app context is accessible."""
    _,cfg,key=_active()
    prompt=("Improve the following LOCAL AI training example for accuracy, clarity and concise instruction-following. "
            "Return only the improved response. Do not add private facts or infer user identity.\n\n"
            f"Instruction: {instruction[:4000]}\nInput: {input_text[:4000]}\nCurrent response: {output[:8000]}")
    url=chat_completions_url(cfg)
    with httpx.Client(timeout=60,follow_redirects=False) as client:
        r=client.post(url,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                      json={"model":cfg["model"],"messages":[{"role":"system","content":"You are a dataset teacher. Output only the improved answer."},
                                                            {"role":"user","content":prompt}],"temperature":0.2})
    r.raise_for_status()
    text=r.json()["choices"][0]["message"]["content"].strip()
    if not text: raise RuntimeError("Cloud teacher returned an empty response")
    return text[:16000]

def distill_dataset(dataset_id:str, create_copy:bool=True)->dict:
    source_dataset_id = dataset_id
    derived = dataset.clone_dataset(dataset_id) if create_copy else None
    if derived:
        dataset_id = derived["id"]
    records=dataset.export_jsonl(dataset_id)
    if not records: raise RuntimeError("Dataset has no approved items")
    changed=0
    with db.get_conn() as conn:
        items=conn.execute("SELECT id,instruction,input,output FROM dataset_items WHERE dataset_id=? AND approved=1",(dataset_id,)).fetchall()
    for item in items:
        improved=refine_example(item["instruction"],item["input"],item["output"])
        with db.get_conn() as conn:
            conn.execute("UPDATE dataset_items SET output=? WHERE id=?",(improved,item["id"]))
        changed+=1
    return {"ok":True,"dataset_id":dataset_id,"source_dataset_id":source_dataset_id,"derived_dataset":bool(derived),
            "refined_items":changed,"stored":"local","provider":status()["active_provider"]}
