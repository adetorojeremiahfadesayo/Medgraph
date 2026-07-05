"""
MedGraph configuration.

The backend can run in JSON fallback mode for local tests, then activate the
Cognee SDK once credentials and storage settings are available.
"""

from __future__ import annotations

import importlib.util
import os

from dotenv import load_dotenv

load_dotenv()

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-max")

EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", LLM_API_KEY)
EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", LLM_API_BASE)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

COGNEE_CLOUD_API_KEY = os.getenv("COGNEE_CLOUD_API_KEY", "")
COGNEE_CLOUD_BASE_URL = os.getenv("COGNEE_CLOUD_BASE_URL", "https://api.cognee.ai")
COGNEE_ENABLE_SDK = os.getenv("COGNEE_ENABLE_SDK", "false").lower() == "true"
COGNEE_RESET_ON_START = os.getenv("COGNEE_RESET_ON_START", "false").lower() == "true"
COGNEE_SDK_AVAILABLE = importlib.util.find_spec("cognee") is not None
CLOUD_SYNC_ENABLED = bool(COGNEE_CLOUD_API_KEY)

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
COGNEE_DATA_PATH = os.getenv("COGNEE_DATA_PATH", "./cognee_data")


async def setup_cognee() -> dict:
    if not COGNEE_ENABLE_SDK:
        return {
            "enabled": False,
            "reason": "COGNEE_ENABLE_SDK is false; JSON fallback memory is active.",
        }
    if not COGNEE_SDK_AVAILABLE:
        return {
            "enabled": False,
            "reason": "Cognee SDK is not installed in this Python environment.",
        }

    import cognee

    cognee.config.set_llm_provider("openai")
    cognee.config.set_llm_model(LLM_MODEL)
    cognee.config.set_llm_api_key(LLM_API_KEY)
    cognee.config.set_llm_endpoint(LLM_API_BASE)

    cognee.config.set_embedding_provider("openai")
    cognee.config.set_embedding_model(EMBEDDING_MODEL)
    cognee.config.set_embedding_api_key(EMBEDDING_API_KEY)
    cognee.config.set_embedding_endpoint(EMBEDDING_API_BASE)

    if COGNEE_RESET_ON_START and hasattr(cognee, "prune"):
        await cognee.prune.prune_system(metadata=False)

    return {
        "enabled": True,
        "cloud_sync_enabled": CLOUD_SYNC_ENABLED,
        "reset_on_start": COGNEE_RESET_ON_START,
    }
