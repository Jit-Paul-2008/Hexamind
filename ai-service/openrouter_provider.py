"""
OpenRouter API Provider
Free tier: free models + starter credits
Provides tertiary fallback LLM access when local and HF are unavailable
"""

from __future__ import annotations

import os
from typing import Optional

import httpx


class OpenRouterProvider:
    """OpenRouter chat-completions provider for tertiary fallback."""

    MODEL_RECOMMENDATIONS = {
        "advocate": "google/gemini-2.0-flash-exp:free",
        "skeptic": "meta-llama/llama-3.1-8b-instruct:free",
        "synthesiser": "mistralai/mistral-7b-instruct:free",
        "oracle": "google/gemini-2.0-flash-exp:free",
        "verifier": "meta-llama/llama-3.1-8b-instruct:free",
    }

    def __init__(self, api_key: Optional[str] = None, timeout_seconds: float = 35.0) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "").strip()
        self.available = bool(self.api_key)
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def generate(
        self,
        agent_id: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 700,
    ) -> str | None:
        if not self.available:
            return None

        model = self.MODEL_RECOMMENDATIONS.get(agent_id, "google/gemini-2.0-flash-exp:free")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://hexamind.local",
            "X-Title": "Hexamind",
        }
        payload = {
            "model": model,
            "temperature": max(0.0, min(1.0, temperature)),
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": "You are a concise, evidence-backed assistant."},
                {"role": "user", "content": prompt},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                if response.status_code in {401, 402, 403, 429}:
                    return None
                response.raise_for_status()
                data = response.json()

            choices = data.get("choices") or []
            if not choices:
                return None
            message = choices[0].get("message") or {}
            content = message.get("content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
            return None
        except Exception:
            return None

    def health_check(self) -> dict[str, object]:
        return {
            "provider": "openrouter",
            "available": self.available,
            "api_key_set": bool(self.api_key),
            "free_tier": "Free models + starter credits",
            "supported_agents": list(self.MODEL_RECOMMENDATIONS.keys()),
        }


_or_provider: OpenRouterProvider | None = None


def get_openrouter_provider() -> OpenRouterProvider:
    global _or_provider
    if _or_provider is None:
        _or_provider = OpenRouterProvider()
    return _or_provider
