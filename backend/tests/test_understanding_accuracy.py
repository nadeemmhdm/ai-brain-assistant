from app import understanding, brain

def test_normalize_preserves_meaningful_content():
    assert understanding.normalize("  explain   CVE-2026-1234  ") == "explain CVE-2026-1234"

def test_followup_retrieval_uses_recent_user_context():
    recent=[{"role":"user","content":"Explain zero trust networking"},{"role":"assistant","content":"..."}]
    q=understanding.retrieval_query("how does it work?",recent)
    assert "zero trust networking" in q and "how does it work?" in q

def test_standalone_query_is_not_rewritten_by_rule_layer():
    q="Explain how TLS certificate validation works"
    assert understanding.retrieval_query(q,[]) == q
