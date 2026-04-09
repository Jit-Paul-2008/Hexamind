"""
Hugging Face Inference API Provider
Free tier: 100k requests/month
Provides fallback LLM access when Ollama is overloaded
"""

from __future__ import annotations

import os
import asyncio
from typing import Optional
import httpx


class HuggingFaceInferenceProvider:
    """Free Hugging Face API for LLM inference fallback."""
    
    # Model recommendations for different agent roles
    MODEL_RECOMMENDATIONS = {
        "advocate": "mistralai/Mistral-7B-Instruct-v0.2",  # Strong reasoning
        "skeptic": "meta-llama/Llama-2-70b-chat-hf",  # Critical analysis
        "synthesiser": "tiiuae/falcon-7b-instruct",  # Dialogue & synthesis
        "oracle": "EleutherAI/gpt-neox-20b",  # Forecasting
        "verifier": "teknium/OpenHermes-2.5-Mistral-7B",  # Verification
    }
    
    def __init__(self, api_key: Optional[str] = None, timeout_seconds: float = 30.0):
        """
        Initialize Hugging Face provider.
        
        Args:
            api_key: HuggingFace API token (from https://huggingface.co/settings/tokens)
                    If None, will try to read from HUGGINGFACE_API_KEY env var
            timeout_seconds: HTTP timeout for API requests
        """
        self.api_key = api_key or os.getenv("HUGGINGFACE_API_KEY", "").strip()
        self.available = bool(self.api_key)
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://api-inference.huggingface.co/models"
    
    async def generate(
        self,
        agent_id: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> Optional[str]:
        """
        Generate text using Hugging Face API.
        
        Args:
            agent_id: Which agent is requesting (for model selection)
            prompt: Input prompt/query
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated text or None if failed/unavailable
        """
        if not self.available:
            return None
        
        # Select appropriate model for agent
        model_id = self.MODEL_RECOMMENDATIONS.get(agent_id, "mistralai/Mistral-7B-Instruct-v0.2")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                url = f"{self.base_url}/{model_id}"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "HexamindAI/1.0",
                }
                
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_tokens,
                        "temperature": max(0.0, min(1.0, temperature)),
                        "top_p": 0.95,
                    },
                }
                
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 429:
                    # Rate limited - that's okay, fallback will handle
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                # Handle response format: list of dicts with generated_text
                if isinstance(data, list) and len(data) > 0:
                    result = data[0].get("generated_text", "")
                    if isinstance(result, str) and result:
                        return result
                
                # Handle direct generated_text response
                if isinstance(data, dict):
                    result = data.get("generated_text", "")
                    if isinstance(result, str) and result:
                        return result
                
                return None
        
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError):
            # Network error - that's okay, fallback will handle
            return None
        except Exception:
            # Any other error - silent fallback
            return None
    
    def health_check(self) -> dict:
        """Return health status of this provider."""
        return {
            "provider": "huggingface",
            "available": self.available,
            "api_key_set": bool(self.api_key),
            "free_tier": "100k requests/month",
            "supported_agents": list(self.MODEL_RECOMMENDATIONS.keys()),
        }


# Singleton instance
_hf_provider: Optional[HuggingFaceInferenceProvider] = None


def get_huggingface_provider() -> HuggingFaceInferenceProvider:
    """Get or create Hugging Face provider instance."""
    global _hf_provider
    if _hf_provider is None:
        _hf_provider = HuggingFaceInferenceProvider()
    return _hf_provider
