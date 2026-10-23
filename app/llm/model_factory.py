"""
Model factory — keeps Gemini model IDs in one place.

The agent orchestrator should never hardcode a model name. It calls
`get_chat_model()` which reads from settings. Switching models only requires
updating .env.

We intentionally do NOT support `gemini-3.6-flash` or `gemini-embedding-2`
(those are not real model names). For embeddings, use the local BGE model
configured in app.rag.embeddings.
"""

from __future__ import annotations

from app.core.config import get_settings

# Whitelist of chat models we know exist and support function calling.
# If the user sets GEMINI_MODEL to something not in this list, we still
# try it but log a warning so they can correct the .env.
SUPPORTED_CHAT_MODELS = {
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash-8b",
}


def get_chat_model() -> str:
    settings = get_settings()
    model = settings.gemini_model
    if model not in SUPPORTED_CHAT_MODELS:
        from app.core.logging import get_logger
        get_logger(__name__).warning(
            "unsupported_chat_model",
            model=model,
            supported=sorted(SUPPORTED_CHAT_MODELS),
        )
    return model