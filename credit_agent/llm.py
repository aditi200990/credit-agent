"""Optional LLM client for any OpenAI-compatible chat endpoint.

Works with OpenAI, Azure OpenAI, Mistral, Groq, vLLM, or a local Ollama server.
Configure with environment variables; if none are set, the agent runs fully
offline and writes the memo from a template.

    CREDITAGENT_LLM_BASE_URL   e.g. http://localhost:11434/v1  (Ollama)
    CREDITAGENT_LLM_MODEL      e.g. mistral
    CREDITAGENT_LLM_API_KEY    optional for local servers
"""
from __future__ import annotations

import json
import os
import urllib.request


def is_configured() -> bool:
    return bool(os.getenv("CREDITAGENT_LLM_BASE_URL") and os.getenv("CREDITAGENT_LLM_MODEL"))


def chat(system: str, user: str, temperature: float = 0.1, timeout: int = 60) -> str:
    base = os.environ["CREDITAGENT_LLM_BASE_URL"].rstrip("/")
    payload = {
        "model": os.environ["CREDITAGENT_LLM_MODEL"],
        "temperature": temperature,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    headers = {"Content-Type": "application/json"}
    if key := os.getenv("CREDITAGENT_LLM_API_KEY"):
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(f"{base}/chat/completions", data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"].strip()
