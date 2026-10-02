import pytest
from app import llm_client

@pytest.mark.asyncio
async def test_visible_recovery_keeps_selected_main(monkeypatch):
    seen = {}
    async def fake_complete(which, messages, reasoning_level, max_tokens=None):
        seen.update(which=which, level=reasoning_level, max_tokens=max_tokens, messages=messages)
        return "visible reply"
    monkeypatch.setattr(llm_client, "complete", fake_complete)
    out = await llm_client.recover_visible_answer("main", "Hi")
    assert out == "visible reply"
    assert seen["which"] == "main"
    assert seen["level"] == "off"
    assert seen["max_tokens"] == 512
    assert "visible answer text only" in seen["messages"][0]["content"]
