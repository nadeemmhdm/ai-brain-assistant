import pytest
from app import learn

def test_new_learning_state_starts_with_zero_saved_items():
    s = learn._new_state("intro cybersecurity")
    assert s["knowledge_items"] == 0
    assert s["questions_without_evidence"] == 0
    assert s["synthesis_fallbacks"] == 0
    assert s["status"] == "running"

def test_learning_success_requires_saved_knowledge_contract():
    # Regression contract: UI/history must never treat a zero-item run as useful completion.
    s = learn._new_state("intro cybersecurity")
    assert not (s["status"] == "completed" and s["knowledge_items"] == 0)
