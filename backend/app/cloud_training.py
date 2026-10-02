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
            "privacy":"Only explicitly approved dataset examples are sent. Chat, memory, Brain DB and local files are never attached."}

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
    url=cfg["base_url"].rstrip("/")+"/chat/completions"
    with httpx.Client(timeout=60,follow_redirects=False) as client:
        r=client.post(url,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                      json={"model":cfg["model"],"messages":[{"role":"system","content":"You are a dataset teacher. Output only the improved answer."},
                                                            {"role":"user","content":prompt}],"temperature":0.2})
    r.raise_for_status()
    text=r.json()["choices"][0]["message"]["content"].strip()
    if not text: raise RuntimeError("Cloud teacher returned an empty response")
    return text[:16000]

def distill_dataset(dataset_id:str)->dict:
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
    return {"ok":True,"dataset_id":dataset_id,"refined_items":changed,"stored":"local"}
