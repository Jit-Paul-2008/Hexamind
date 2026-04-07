import os
import json
import httpx
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator

logger = logging.getLogger(__name__)

class InferenceProvider:
    """Unified interface for Local (Ollama) and Remote (GCP/OpenRouter) AI."""
    
    def __init__(self, model_name: str, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.model_name = model_name
        # Use native Ollama API by default
        self.base_url = base_url or os.getenv("HEXAMIND_LOCAL_BASE_URL", "http://localhost:11434/api/chat")
        self.api_key = api_key or os.getenv("HEXAMIND_AUTH_TOKEN", "")

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, stream: bool = False) -> str:
        """Single-shot generation via Native Ollama API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=1200.0) as client:
                response = await client.post(
                    f"{self.base_url}",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_ctx": 4096,
                            "num_thread": 8  # Optimize for Xeon concurrency
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()
                # Native Ollama response format: data["message"]["content"]
                return data["message"]["content"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                err_msg = f"Model '{self.model_name}' not found. Please run 'ollama pull {self.model_name}'."
            else:
                err_msg = f"Inference HTTP error: {e}"
            logger.error(err_msg)
            raise Exception(err_msg)
        except Exception as e:
            err_msg = f"Inference failed for {self.model_name}: {str(e)}"
            logger.error(err_msg)
            raise Exception(err_msg)



    async def stream_text(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Streaming generation for the UI."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=1200.0) as client:

                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}" if self.api_key else ""},
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "temperature": 0.3,
                        "stream": True,
                    }
                ) as response:
                    if response.status_code != 200:
                        yield f"Inference Error: {response.status_code} - Streaming failed."
                        return

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        if line == "data: [DONE]":
                            break
                        try:
                            chunk = json.loads(line[6:])
                            content = chunk["choices"][0].get("delta", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.ReadTimeout:
            err_msg = f"Streaming from {self.model_name} timed out after 1200s."
            logger.error(err_msg)
            yield f"\n\nInference Error: {err_msg}"
        except Exception as e:
            err_msg = f"Streaming failed: {str(e)}"
            logger.error(err_msg)
            yield f"\n\nInference Error: {err_msg}"

    async def verify_readiness(self) -> bool:
        """Pings Ollama to ensure the model is pulled and the service is alive."""
        try:
            # Check Ollama root (/api/tags or equivalent) 
            # We'll use a direct ping to the v1/models endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/models")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["id"] for m in data.get("data", [])]
                    if self.model_name in models:
                        return True
            return False
        except Exception:
            return False


def get_provider() -> InferenceProvider:
    """Factory to get the right provider based on config. 
    Defaults to local Ollama with fallback logic for Xeon setups."""
    if os.getenv("HEXAMIND_USE_CLOUD", "0") in {"1", "true", "yes", "on"}:
        return InferenceProvider(
            model_name=os.getenv("HEXAMIND_CLOUD_MODEL", "gpt-4o"),
            base_url=os.getenv("HEXAMIND_CLOUD_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("HEXAMIND_CLOUD_API_KEY")
        )
    
    # Primary: DeepSeek-R1 (14B) for high-fidelity Dual Xeon research
    # We use 14B because the hardware is sufficient (42GB RAM).
    preferred_model = os.getenv("HEXAMIND_LOCAL_MODEL_LARGE", "deepseek-r1:14b")
    
    return InferenceProvider(model_name=preferred_model)



