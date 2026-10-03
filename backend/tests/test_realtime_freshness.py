from app import research

def test_english_current_is_fresh():
    assert research.needs_fresh_web("Who is the current Prime Minister of India?")

def test_malayalam_current_is_fresh():
    assert research.needs_fresh_web("ഇപ്പോഴത്തെ ഇന്ത്യയുടെ പ്രധാനമന്ത്രി ആരാണ്?")

def test_manglish_current_is_fresh():
    assert research.needs_fresh_web("ippo current prime minister aara?")

def test_static_question_not_forced_fresh():
    assert not research.needs_fresh_web("Explain binary search")

def test_fresh_query_never_uses_saved_recall(monkeypatch):
    monkeypatch.setattr(research.brain, "search_knowledge", lambda *a, **k: [{
        "score": .99, "updated_at": 99999999999, "source_ids": [], "verification_status": "verified",
        "question": "old", "answer": "stale"
    }])
    assert research.recall("current prime minister of India") is None
