"""LLM client for OpenAI-compatible endpoints (M6).

Talks to local vLLM and frontier providers through the same chat-completions
interface, so swapping providers is configuration (blueprint §5, model-agnostic
serving). Supports non-streaming and token streaming. Network-free in tests:
inject a fake `transport`/caller.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


class LLMClient:
    """Minimal async OpenAI-compatible chat client."""

    def __init__(self, base_url: str, provider: str = "local", api_key: str | None = None,
                 timeout: float = 30.0) -> None:
        self._base = base_url.rstrip("/")
        self._provider = provider
        self._api_key = api_key
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    async def chat(self, messages: list[dict], model: str, *, max_tokens: int = 512,
                   temperature: float = 0.2) -> LLMResponse:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base}/v1/chat/completions", json=payload, headers=self._headers()
            )
            resp.raise_for_status()
            data = resp.json()
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            text=choice,
            model=model,
            provider=self._provider,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
        )

    async def stream(self, messages: list[dict], model: str, *, max_tokens: int = 512,
                     temperature: float = 0.2) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST", f"{self._base}/v1/chat/completions", json=payload, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line[len("data:"):].strip()
                    if chunk == "[DONE]":
                        break
                    yield chunk
