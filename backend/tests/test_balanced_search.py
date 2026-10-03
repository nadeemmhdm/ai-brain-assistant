from app import research

def test_freshness_multilingual():
    assert research.needs_fresh_web("current prime minister")
    assert research.needs_fresh_web("ഇപ്പോഴത്തെ പ്രധാനമന്ത്രി")
    assert research.needs_fresh_web("ippo latest model")

def test_quick_has_current_and_history_lanes():
    q=research._balanced_queries("Python", "quick")
    assert len(q)==2 and "current latest" in q[0] and "history background" in q[1]

def test_deep_has_multiple_current_and_history_lanes():
    q=research._balanced_queries("Python", "deep")
    assert len(q)==4
    assert sum("current" in x for x in q)>=2
    assert sum(("history" in x or "origin" in x) for x in q)>=2
