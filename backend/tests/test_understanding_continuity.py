from app import understanding

def turns():
    return [
      {"role":"user","content":"Who is the current prime minister?"},
      {"role":"assistant","content":"The current prime minister is Example A."},
    ]

def test_correction_uses_assistant_turn():
    q=understanding.retrieval_query("That is wrong. The correct answer is Example B.",turns())
    assert "assistant: The current prime minister is Example A." in q
    assert "Example B" in q

def test_short_followup_uses_recent_dialogue():
    q=understanding.retrieval_query("Why?",turns())
    assert "current prime minister" in q
    assert "current user follow-up: Why?" in q

def test_correction_detection():
    assert understanding.is_correction("That answer is wrong")
    assert understanding.is_correction("അത് തെറ്റാണ്")
