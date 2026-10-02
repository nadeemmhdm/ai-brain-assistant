from app import llm_client

def test_main_reasoning_never_requires_thinking_tags():
    prompt = llm_client.build_system_prompt("BASE", "medium", "main")
    assert "<thinking>" not in prompt
    assert "output only the final user-visible answer" in prompt

def test_agent_reasoning_keeps_legacy_split_protocol():
    prompt = llm_client.build_system_prompt("BASE", "medium", "agent")
    assert "<thinking>" in prompt
    assert "</thinking>" in prompt

def test_reasoning_off_has_no_special_protocol():
    assert llm_client.build_system_prompt("BASE", "off", "main") == "BASE"
