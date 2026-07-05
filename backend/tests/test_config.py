import importlib
import sys
import asyncio
from types import SimpleNamespace
from pathlib import Path

from backend.services.memory import load_backend_env


def test_config_imports_even_when_cognee_sdk_is_not_installed():
    config = importlib.import_module("backend.config")

    assert config.APP_PORT == 8000
    assert isinstance(config.CLOUD_SYNC_ENABLED, bool)


def test_backend_env_loader_reads_backend_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_API_KEY=qwen-test-key\nCOGNEE_ENABLE_SDK=true\n", encoding="utf-8")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("COGNEE_ENABLE_SDK", raising=False)

    load_backend_env(env_file)

    assert Path(env_file).exists()
    assert len(__import__("os").environ["LLM_API_KEY"]) == len("qwen-test-key")
    assert __import__("os").environ["COGNEE_ENABLE_SDK"] == "true"


def test_setup_cognee_uses_current_sdk_setters(monkeypatch):
    config = importlib.import_module("backend.config")
    calls = []

    class FakeCogneeConfig:
        def set_llm_provider(self, value):
            calls.append(("set_llm_provider", value))

        def set_llm_model(self, value):
            calls.append(("set_llm_model", value))

        def set_llm_api_key(self, value):
            calls.append(("set_llm_api_key", value))

        def set_llm_endpoint(self, value):
            calls.append(("set_llm_endpoint", value))

        def set_embedding_provider(self, value):
            calls.append(("set_embedding_provider", value))

        def set_embedding_model(self, value):
            calls.append(("set_embedding_model", value))

        def set_embedding_api_key(self, value):
            calls.append(("set_embedding_api_key", value))

        def set_embedding_endpoint(self, value):
            calls.append(("set_embedding_endpoint", value))

        def set_llm_config(self, value):
            raise AssertionError("old config dict API should not be used")

        def set_embedding_config(self, value):
            raise AssertionError("old config dict API should not be used")

    fake_cognee = SimpleNamespace(config=FakeCogneeConfig())
    monkeypatch.setitem(sys.modules, "cognee", fake_cognee)
    monkeypatch.setattr(config, "COGNEE_ENABLE_SDK", True)
    monkeypatch.setattr(config, "COGNEE_SDK_AVAILABLE", True)
    monkeypatch.setattr(config, "LLM_API_KEY", "fake-llm-key")
    monkeypatch.setattr(config, "EMBEDDING_API_KEY", "fake-embedding-key")

    result = asyncio.run(config.setup_cognee())

    assert result["enabled"] is True
    assert ("set_llm_provider", "openai") in calls
    assert ("set_llm_model", config.LLM_MODEL) in calls
    assert ("set_llm_api_key", "fake-llm-key") in calls
    assert ("set_llm_endpoint", config.LLM_API_BASE) in calls
    assert ("set_embedding_provider", "openai") in calls
    assert ("set_embedding_model", config.EMBEDDING_MODEL) in calls
    assert ("set_embedding_api_key", "fake-embedding-key") in calls
    assert ("set_embedding_endpoint", config.EMBEDDING_API_BASE) in calls
