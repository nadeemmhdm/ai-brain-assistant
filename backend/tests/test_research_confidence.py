from app.research import confidence

def test_single_domain_is_never_high_confidence():
    c = confidence([0.95, 0.90], ["A"], 1)
    assert c["percent"] <= 55

def test_general_web_only_is_capped():
    c = confidence([0.95, 0.90, 0.85], ["C", "C", "C"], 3)
    assert c["percent"] <= 59

def test_snippet_only_evidence_is_penalized():
    full = confidence([0.8, 0.75], ["A", "B"], 2, 0)
    snippet = confidence([0.8, 0.75], ["A", "B"], 2, 2)
    assert snippet["percent"] < full["percent"]

def test_no_evidence_is_zero():
    assert confidence([], [], 0)["percent"] == 0
