import os
import json
import httpx
import re
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator

from usage_tracking import record_llm_call_started, record_llm_completion_tokens

logger = logging.getLogger(__name__)

def get_optimal_thread_count() -> int:
    """Detects CPU cores and returns a balanced thread count for Ollama."""
    try:
        cores = os.cpu_count() or 2
        # Use 50% of cores for hyperthreading balance, allow down to 1 on single-core systems
        optimal = max(1, cores // 2)
        # On 2-core systems, use 1 thread to avoid context switch thrashing
        if cores == 2:
            return 1
        # On 4+ core systems, use at least 2 threads
        return max(2, optimal)
    except Exception:
        return 1

class InferenceProvider:
    """Unified interface for Local (Ollama) and Remote (GCP/OpenRouter) AI."""
    
    # Static counters for persistent session tracking
    TOTAL_TOKENS_OUT = 0
    TOTAL_TOKENS_IN = 0
    API_CALL_COUNT = 0
    def __init__(self, model_name: str, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.model_name = model_name
        # Use native Ollama API by default
        self.base_url = base_url or os.getenv("HEXAMIND_LOCAL_BASE_URL", "http://localhost:11434/api/chat")
        # Ensure base_url is the root for native API calls
        if self.base_url.endswith("/v1"):
             self.base_url = self.base_url.replace("/v1", "/api/chat")
        self.api_key = api_key or os.getenv("HEXAMIND_AUTH_TOKEN", "")

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, stream: bool = False, max_tokens: int = 1500) -> str:
        """Single-shot generation via Native Ollama API with Token Tracking."""
        InferenceProvider.API_CALL_COUNT += 1
        prompt_tokens_estimated = int(len(prompt.split()) * 1.35)
        InferenceProvider.TOTAL_TOKENS_IN += prompt_tokens_estimated
        if system_prompt:
            prompt_tokens_estimated += int(len(system_prompt.split()) * 1.35)
            InferenceProvider.TOTAL_TOKENS_IN += int(len(system_prompt.split()) * 1.35)
        provider_name = "cloud" if os.getenv("HEXAMIND_USE_CLOUD", "0") in {"1", "true", "yes", "on"} else "local-ollama"
        record_llm_call_started(prompt_tokens_estimated=prompt_tokens_estimated, provider=provider_name)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=2400.0) as client:
                response = await client.post(
                    f"{self.base_url}",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_ctx": 4096,
                            "num_thread": get_optimal_thread_count(),
                            "num_predict": max_tokens,
                            "repetition_penalty": 1.1,
                            "top_p": 0.9
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()
                # Native Ollama response format: data["message"]["content"]
                content = data["message"]["content"]
                
                # Robustly strip thinking bounds (handles partial or multiple <think> tags)
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                content = re.sub(r'<think>.*', '', content, flags=re.DOTALL) # Catch cutoff thinking
                
                # Cleanup dangling tags and normalize whitespace
                content = content.replace('<think>', '').replace('</think>', '').strip()
                
                # Increment output tokens
                completion_tokens_estimated = int(len(content.split()) * 1.45)
                InferenceProvider.TOTAL_TOKENS_OUT += completion_tokens_estimated
                record_llm_completion_tokens(completion_tokens_estimated)
                return content
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



    async def stream_text(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 2000) -> AsyncGenerator[str, None]:
        """Streaming generation for the UI using Native Ollama API."""
        InferenceProvider.API_CALL_COUNT += 1
        prompt_tokens_estimated = int(len(prompt.split()) * 1.35)
        if system_prompt:
            prompt_tokens_estimated += int(len(system_prompt.split()) * 1.35)
        InferenceProvider.TOTAL_TOKENS_IN += prompt_tokens_estimated
        streamed_output_tokens_estimated = 0
        provider_name = "cloud" if os.getenv("HEXAMIND_USE_CLOUD", "0") in {"1", "true", "yes", "on"} else "local-ollama"
        record_llm_call_started(prompt_tokens_estimated=prompt_tokens_estimated, provider=provider_name)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=2400.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": 0.3,
                            "num_ctx": 4096,
                            "num_thread": get_optimal_thread_count(),
                            "num_predict": max_tokens,
                            "repetition_penalty": 1.1,
                            "top_p": 0.9
                        }
                    }
                ) as response:
                    if response.status_code != 200:
                        yield f"Inference Error: {response.status_code} - Streaming failed."
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            # Native Ollama stream format: chunk["message"]["content"]
                            if "message" in chunk and "content" in chunk["message"]:
                                content = chunk["message"]["content"]
                                if content:
                                    chunk_tokens = int(len(content.split()) * 1.45)
                                    streamed_output_tokens_estimated += chunk_tokens
                                    InferenceProvider.TOTAL_TOKENS_OUT += chunk_tokens
                                    yield content
                            if chunk.get("done"):
                                record_llm_completion_tokens(streamed_output_tokens_estimated)
                                break
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
            # We need the root endpoint for /api/tags
            root_url = self.base_url.replace("/api/chat", "")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{root_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    if self.model_name in models:
                        return True
            return False
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
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
    
    # Primary: DeepSeek-R1 (7B) for balanced Dual Xeon research
    # Shifting from 14B to 7B to optimize for 2CPU throughput.
    preferred_model = os.getenv("HEXAMIND_LOCAL_MODEL_LARGE", "deepseek-r1:7b")
    
    return InferenceProvider(model_name=preferred_model)



