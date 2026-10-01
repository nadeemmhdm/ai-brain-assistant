"""Run with:  cd backend && pip install pytest && pytest -q"""
import os, sys, tempfile
os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from fastapi.testclient import TestClient
from main import app
from app import downloads, identity, actions, verify, version, teach, model_manager, google_api, llm_client

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_settings_whitelist_blocks_secrets(client):
    assert client.put("/api/settings", json={"key": "auth_password_hash", "value": "x"}).status_code == 400
    assert "auth_password_hash" not in client.get("/api/settings").json()
    assert client.get("/api/settings").json()["ai_name"] == "Nila"

def test_hf_url_validation():
    assert downloads.hf_url("Qwen/Qwen2.5-0.5B-Instruct-GGUF", "model.gguf").startswith("https://huggingface.co/")
    for bad in ("../x", "a/b", ""):
        with pytest.raises(ValueError):
            downloads.hf_url("Qwen/Qwen2.5-0.5B-Instruct-GGUF", bad)
    with pytest.raises(ValueError):
        downloads.hf_url("../../etc", "a.gguf")
    with pytest.raises(ValueError):
        downloads.start("model", "https://evil.example.com/a.gguf", "/tmp/a.gguf")

def test_identity():
    assert "Nadeem" in identity.identity_answer("who created you?", "Nila")
    assert "instagram.com/n4d.eem" in identity.identity_answer("your instagram", "Nila")
    assert "Qwen" not in identity.identity_answer("are you qwen?", "Nila")
    assert identity.identity_answer("how do I sort a list", "Nila") is None

def test_intents_and_time():
    d = actions.detect("create a google meet called Sync tomorrow at 3pm with a@b.io", -330)
    assert d["action"] == "meet.invite" and d["params"]["start"].startswith(("2", "3")) and d["params"]["attendees"] == ["a@b.io"]
    assert actions.detect("what is the capital of France") is None
    assert actions.detect("Draft an email to x@y.com about lunch")["action"] == "gmail.draft"

def test_permissions(client):
    assert not actions.has_grant("meet.create", "c1")
    actions.add_grant("meet.create", "chat", "c1")
    assert actions.has_grant("meet.create", "c1") and not actions.has_grant("meet.create", "c2")
    actions.add_grant("gmail.read", "always", None)
    assert actions.has_grant("gmail.read", "anything")
    for g in actions.list_grants():
        actions.revoke(g["id"])
    assert not actions.has_grant("gmail.read", "anything")
    # executing without a token / grant is refused
    r = client.post("/api/google/execute", json={"action": "gmail.read", "grant": "standing"})
    assert r.status_code == 403

def test_google_confirm_gates():
    with pytest.raises(google_api.GoogleError):
        google_api.send_draft("d", False)
    with pytest.raises(google_api.GoogleError):
        google_api.trash_message("m", False)
    with pytest.raises(google_api.GoogleError):
        google_api._raw(["not-an-email"], "s", "b")

def test_oauth_url_uses_pkce_and_state(monkeypatch):
    monkeypatch.setattr(google_api.settings, "google_client_id", "id"); monkeypatch.setattr(google_api.settings, "google_client_secret", "sec")
    u = google_api.auth_url()
    assert "code_challenge_method=S256" in u and "state=" in u and "client_secret" not in u
    with pytest.raises(google_api.GoogleError):
        google_api.handle_callback("code", "forged-state")

def test_versions():
    assert version.is_newer("v0.3.0-beta.1", "0.2.0-beta.1") and not version.is_newer("0.2.0-beta.1", "0.2.0-beta.1")
    assert version.is_newer("0.3.0", "0.3.0-beta.9")

def test_verify_numbers():
    assert verify.unsupported_numbers("Opened in 1901 [1]", "opened in 1889") == ["1901"]
    assert verify.unsupported_numbers("Opened in 1889", "opened in 1889") == []

def test_model_import(tmp_path, client):
    good = tmp_path / "m.gguf"; good.write_bytes(b"GGUF" + b"\0" * 64)
    assert model_manager.import_model(str(good))["mode"] == "link"
    assert any(m["filename"] == "m.gguf" and m["imported"] for m in model_manager.list_local())
    bad = tmp_path / "x.gguf"; bad.write_bytes(b"NOPE")
    with pytest.raises(ValueError): model_manager.import_model(str(bad))
    with pytest.raises(ValueError): model_manager.import_model(str(tmp_path / "a.txt"))
    assert client.post("/api/model/load", json={"role": "main", "filename": "../../etc/passwd"}).status_code == 400

def test_teach_and_search(client):
    assert client.post("/api/brain/teach", json={"topic": "Tea", "question": "What is oolong?", "answer": "A partially oxidised tea."}).status_code == 200
    assert client.post("/api/brain/import", json={"topic": "Notes", "title": "Doc", "text": "Para one.\n\nPara two."}).json()["chunks"] >= 1
    hits = client.get("/api/brain/knowledge", params={"query": "oolong tea"}).json()
    assert hits and hits[0]["question"] == "What is oolong?"
    assert client.post("/api/brain/watch", json={"topic": "Python", "interval_hours": 24}).status_code == 200

def test_memory_and_hash_stability(client):
    from app import brain
    a = brain.embed("hello persistent world"); b = brain._hash_embed("hello persistent world")
    assert abs(float(a @ b) - 1.0) < 1e-5 or brain.embedding_signature().startswith("st")
    assert client.post("/api/memory", json={"content": "I prefer metric units"}).status_code == 200

def test_think_splitter():
    sp = llm_client.ThinkSplitter(); out = []
    for ch in ["Hi <thi", "nking>plan", "</thin", "king>done"]:
        out += sp.feed(ch)
    out += sp.flush()
    assert "".join(t for k, t in out if k == "thinking") == "plan" and "".join(t for k, t in out if k == "answer") == "Hi done"

def test_chat_identity_shortcut_and_history(client):
    cid = client.post("/api/conversations", json={}).json()["id"]
    r = client.post("/api/chat", json={"conversation_id": cid, "message": "Who is your developer?"})
    assert "Nadeem" in r.text and "event: done" in r.text
    msgs = client.get(f"/api/conversations/{cid}/messages").json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    forked = client.post(f"/api/conversations/{cid}/fork", json={"message_id": msgs[0]["id"]}).json()
    assert len(client.get(f"/api/conversations/{forked['id']}/messages").json()) == 1
    assert client.get("/api/conversations", params={"q": "developer"}).json()

def test_no_search_needed_regex():
    from app.routers.chat import _NO_SEARCH_NEEDED
    assert _NO_SEARCH_NEEDED.match("2000+4000") and _NO_SEARCH_NEEDED.match("what is 12*7?")
    assert _NO_SEARCH_NEEDED.match("hello!") and not _NO_SEARCH_NEEDED.match("who founded Grok")

def test_skills_seeded_and_crud(client):
    from app import skills
    skills.seed()
    names = {s["name"] for s in client.get("/api/skills").json()}
    assert {"Summarize", "Explain simply", "Fix grammar", "Make concise", "Debug this", "Action items", "Pros and cons", "Mock interviewer", "Write tests"}.issubset(names)
    sid = client.post("/api/skills", json={"name": "My skill", "instructions": "Be extra terse."}).json()["id"]
    assert client.put(f"/api/skills/{sid}", json={"name": "My skill 2", "instructions": "Be terse.", "description": ""}).status_code == 200
    builtin_id = next(s["id"] for s in client.get("/api/skills").json() if s["builtin"])
    assert client.delete(f"/api/skills/{builtin_id}").status_code == 400
    assert client.delete(f"/api/skills/{sid}").status_code == 200

def test_mcp_catalog_and_missing_path(client):
    cat = client.get("/api/mcp/catalog").json()
    keys = {c["key"] for c in cat}
    assert {"filesystem", "fetch", "git", "sequential-thinking", "memory", "time", "sqlite", "everything"} == keys
    assert client.post("/api/mcp/install", json={"key": "filesystem"}).status_code == 400  # needs a path
    r = client.post("/api/mcp/install", json={"key": "fetch"})
    assert r.status_code == 200
    sid = r.json()["id"]
    servers = client.get("/api/mcp/servers").json()
    assert any(s["id"] == sid and s["trusted"] for s in servers)
    assert client.delete(f"/api/mcp/servers/{sid}").status_code == 200

def test_auto_learn_rejects_bad_input(client):
    assert client.post("/api/learn", json={"topic": "  "}).status_code == 400
    assert client.post("/api/learn", json={"topic": "x" * 300}).status_code == 400

def test_search_error_is_honest(monkeypatch):
    from app import search
    def boom(q, max_results=8):
        raise RuntimeError("blocked")
    monkeypatch.setattr(search, "duckduckgo_search", boom)
    monkeypatch.setitem(search.PROVIDERS, "duckduckgo", boom)
    import pytest as _pytest
    with _pytest.raises(search.SearchError):
        search.search("today's weather", use_cache=False)

def test_translate_parse_and_resolve():
    from app.routers.chat import _parse_translate
    from app import translate
    assert _parse_translate("to French: hello there") == ("French", "hello there")
    assert _parse_translate("hola to English") == ("English", "hola")
    assert _parse_translate("nothing here") is None
    assert translate.resolve_code("French") == "fr"
    assert translate.resolve_code("klingon") is None

def test_translate_skill_seeded_and_endpoints(client):
    from app import skills
    skills.seed()
    tr = next(s for s in client.get("/api/skills").json() if s["name"] == "Translate")
    assert tr["kind"] == "translate"
    status = client.get("/api/translate/status").json()
    assert "available" in status and "languages" in status
    assert client.post("/api/translate", json={"text": "hi", "to_code": "fr"}).status_code in (200, 400)  # 400 if the optional package isn't installed in this env

def test_source_trust_expanded():
    from app.search import classify_source
    assert classify_source("https://nvd.nist.gov/vuln/1")[0] == "A"
    assert classify_source("https://cve.mitre.org/x")[0] == "A"
    assert classify_source("https://owasp.org/x")[0] == "B"
    assert classify_source("https://exploit-db.com/x")[0] == "B"

def test_persona_allows_security_topics():
    from app.routers.chat import persona_prompt
    p = persona_prompt(False)
    assert "vulnerability scanning" in p.lower() or "cybersecurity" in p.lower()
    assert "never deflect" in p.lower() and "confident" in p.lower()

def test_chat_google_not_connected(client):
    cid = client.post("/api/conversations", json={}).json()["id"]
    r = client.post("/api/chat", json={"conversation_id": cid, "message": "check my emails"})
    assert "Google" in r.text
