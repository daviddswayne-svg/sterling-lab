"""Single LLM entry point for the site's text generation.

One warm model (gemma4:26b, pinned in Ollama) for every stage: no cold loads or model swaps.
Thinking is off by default; it made short structured outputs 5x slower with no quality gain.
"""
import ollama
from .config import OLLAMA_HOST, TEXT_MODEL

_client = None


def client():
    global _client
    if _client is None:
        _client = ollama.Client(host=OLLAMA_HOST)
    return _client


def chat(messages, model=None, **kwargs):
    """ollama chat with think=False by default (falls back for clients that predate `think`)."""
    kwargs.setdefault("think", False)
    try:
        return client().chat(model=model or TEXT_MODEL, messages=messages, **kwargs)
    except TypeError:
        kwargs.pop("think", None)
        return client().chat(model=model or TEXT_MODEL, messages=messages, **kwargs)
