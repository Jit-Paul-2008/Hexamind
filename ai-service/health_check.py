import os
import sys
import asyncio
import httpx
from pathlib import Path

# Add parent dir to path for imports
sys.path.append(str(Path(__file__).resolve().parent))

from inference_provider import get_optimal_thread_count, get_provider
from agent_model_config import AGENT_MODEL_SPECIALIZATION

async def check_ollama():
    print("🔍 [HEALTH] Checking Ollama Service...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                print("✅ [HEALTH] Ollama is alive.")
                models = [m["name"] for m in response.json().get("models", [])]
                return models
            else:
                print(f"❌ [HEALTH] Ollama returned {response.status_code}")
    except Exception as e:
        print(f"❌ [HEALTH] Ollama connectivity failed: {e}")
    return None

async def check_models(installed_models):
    required = set()
    for config in AGENT_MODEL_SPECIALIZATION.values():
        required.add(config.primary_ollama_model)
    
    print(f"🔍 [HEALTH] Checking required models: {list(required)}")
    missing = []
    for r in required:
        if not any(r in m for m in installed_models):
            missing.append(r)
    
    if not missing:
        print("✅ [HEALTH] All models present.")
    else:
        print(f"⚠️  [HEALTH] Missing models: {missing}")
        print("💡 [HEALTH] Action: 'ollama pull' the missing models.")

async def check_inference():
    print("🔍 [HEALTH] Testing Inference Pipeline...")
    try:
        provider = get_provider()
        print(f"📡 [HEALTH] Using model: {provider.model_name}")
        response = await provider.generate_text("Say 'HEXAMIND_READY'", max_tokens=10)
        if "HEXAMIND_READY" in response.upper():
            print("✅ [HEALTH] Inference verified.")
        else:
            print(f"⚠️  [HEALTH] Unexpected inference response: {response}")
    except Exception as e:
        print(f"❌ [HEALTH] Inference failed: {e}")

def check_resources():
    cores = os.cpu_count() or 1
    optimal = get_optimal_thread_count()
    print(f"🔍 [HEALTH] CPU Cores: {cores}")
    print(f"🔍 [HEALTH] Thread Allocation: {optimal}")
    if optimal > cores:
        print("⚠️  [HEALTH] Resource over-allocation detected.")
    else:
        print("✅ [HEALTH] Thread affinity is balanced.")

async def main():
    print("="*50)
    print("      HEXAMIND v8.5+ SYSTEM HEALTH Audit")
    print("="*50)
    
    check_resources()
    models = await check_ollama()
    if models:
        await check_models(models)
        await check_inference()
    
    print("="*50)
    print("Audit Complete.")

if __name__ == "__main__":
    asyncio.run(main())
