import pytest
from app import llm_client

def test_main_reasoning_prompt_never_requests_visible_thinking_tags():
    prompt = llm_client.build_system_prompt("base", "medium", "main")
    assert "<thinking>" not in prompt
    assert "final user-visible answer" in prompt

def test_agent_keeps_legacy_tagged_protocol():
    prompt = llm_client.build_system_prompt("base", "medium", "agent")
    assert "<thinking>" in prompt

def test_split_thinking_keeps_normal_visible_answer():
    thought, answer = llm_client.split_thinking("Normal visible answer")
    assert thought is None
    assert answer == "Normal visible answer"
