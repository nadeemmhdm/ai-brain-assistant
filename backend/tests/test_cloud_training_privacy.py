from app import cloud_training

def test_provider_catalog_has_single_active_contract():
    assert set(cloud_training.PROVIDERS)=={"openai","ollama_cloud","compatible"}

def test_custom_provider_requires_https():
    try:
        cloud_training.configure("compatible",active=False,base_url="http://example.com/v1")
        assert False
    except ValueError:
        pass

def test_cloud_module_has_no_chat_or_memory_imports():
    import inspect
    src=inspect.getsource(cloud_training)
    assert "from . import chat" not in src
    assert "from . import memory" not in src
    assert "conversations" not in src
    assert "messages" not in src
