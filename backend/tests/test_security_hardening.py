import os
from app import search, model_manager

def test_ssrf_rejects_local_targets():
    assert not search.is_public_http_url("http://127.0.0.1:8000/private")
    assert not search.is_public_http_url("http://localhost/private")
    assert not search.is_public_http_url("file:///etc/passwd")

def test_model_list_does_not_expose_import_paths(monkeypatch, tmp_path):
    model = tmp_path / "safe.gguf"
    model.write_bytes(b"GGUFtest")
    monkeypatch.setattr(model_manager, "_imports", lambda: {"safe.gguf": str(model)})
    monkeypatch.setattr(model_manager.settings, "models_dir", str(tmp_path / "models"))
    rows = model_manager.list_local()
    assert rows and rows[0]["filename"] == "safe.gguf"
    assert "path" not in rows[0]
