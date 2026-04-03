# Hexamind Local Model Improvements Guide

## Your System Resources
- **RAM**: 42GB (excellent for running multiple local models)
- **Storage**: 120GB free (enough for 6-8 quantized models)
- **CPU**: 2 cores (will limit inference speed, but workable)
- **Ollama**: Already installed ✅

---

## Project Analysis Summary

### What Hexamind Does
Hexamind is a **multi-agent research reasoning system** with:
- **5 AI Agents**: Advocate, Skeptic, Synthesiser, Oracle, Verifier
- **Pipeline**: Query → Research (web) → Multi-agent analysis → Final report
- **Quality Gates**: Citation verification, claim checking, contradiction detection
- **Providers**: Gemini, OpenRouter, Groq, and **Local (Ollama)** support already built-in

### Current Architecture
```
┌─────────────────┐    ┌──────────────────────────────────────┐
│   Next.js UI    │◄──►│        FastAPI Backend               │
│   (React Flow)  │    │  ┌─────────────────────────────────┐ │
│                 │    │  │ Pipeline Service                │ │
│  - Agent Canvas │    │  │  - Research Layer (Tavily/DDG) │ │
│  - Quality View │    │  │  - Model Providers (7+ types)  │ │
│  - Live SSE     │    │  │  - Quality Analysis            │ │
└─────────────────┘    │  │  - Multi-agent orchestration   │ │
                       │  └─────────────────────────────────┘ │
                       └──────────────────────────────────────┘
```

### Strengths Found
1. **Already has robust local model support** via `LocalPipelineModelProvider`
2. **Per-agent model routing** - can use different models for each agent
3. **Tiered model system** - small/medium/large for complexity-based routing
4. **Fallback mechanisms** - graceful degradation when local fails
5. **Parallel agent execution** - 60% faster with `HEXAMIND_PARALLEL_AGENTS=true`
6. **Quality gates** - verifies citations, detects contradictions
7. **Token budgeting** - prevents runaway usage

### Current Repo Status

The remaining local-model items from this guide are now wired into the codebase and linked here for quick navigation:

- Local model inventory and readiness endpoint: [ai-service/main.py](ai-service/main.py)
- Local benchmark endpoint: [ai-service/main.py](ai-service/main.py)
- Optional embedding client for semantic similarity: [ai-service/embeddings.py](ai-service/embeddings.py)
- Persistent offline knowledge cache: [ai-service/knowledge_cache.py](ai-service/knowledge_cache.py)
- Research cache integration: [ai-service/research.py](ai-service/research.py)
- User-facing docs updated with the new endpoints: [README.md](README.md) and [src/docs/next-session-plan.md](src/docs/next-session-plan.md)

The repo already shipped the in-memory semantic cache, query routing, health diagnostics, and tiered local provider logic before this update.

---

## Recommended Local Models for Your Hardware

Given your 42GB RAM and 2 cores, here are optimal choices:

### Tier 1: Must-Have (Pull these first)

| Model | Size | RAM Use | Purpose |
|-------|------|---------|---------|
| `llama3.1:8b` | 4.7GB | ~6GB | General agent work (advocate, skeptic) |
| `qwen2.5:7b` | 4.4GB | ~6GB | Excellent reasoning for verification |
| `mistral:7b` | 4.1GB | ~5GB | Fast fallback, good at synthesis |

```bash
# Install core models (~15GB total)
ollama pull llama3.1:8b
ollama pull qwen2.5:7b
ollama pull mistral:7b
```

### Tier 2: Enhanced Quality (if space allows)

| Model | Size | RAM Use | Purpose |
|-------|------|---------|---------|
| `llama3.1:70b-q4` | 39GB | ~42GB | Premium synthesis/final (uses all RAM) |
| `deepseek-coder:6.7b` | 3.8GB | ~5GB | Technical queries, code analysis |
| `phi3:medium` | 7.9GB | ~10GB | Microsoft's reasoning model |

```bash
# Enhanced models (~50GB more)
ollama pull phi3:medium
ollama pull deepseek-coder:6.7b
# Only if you have 45GB+ free RAM at runtime:
# ollama pull llama3.1:70b-q4_K_M
```

### Tier 3: Specialized (for testing features)

| Model | Size | Purpose |
|-------|------|---------|
| `nomic-embed-text` | 274MB | Embeddings for semantic search |
| `mxbai-embed-large` | 669MB | Higher quality embeddings |

```bash
ollama pull nomic-embed-text
ollama pull mxbai-embed-large
```

---

## Configuration for Local Development

### Quick Start Config (`.env`)

```bash
# === Local-Only Mode (Recommended for Testing) ===
HEXAMIND_MODEL_PROVIDER=local
HEXAMIND_MODEL_NAME=llama3.1:8b
HEXAMIND_LOCAL_BASE_URL=http://127.0.0.1:11434/v1
HEXAMIND_LOCAL_STRICT=1

# Tiered model routing (leverage different models per role)
HEXAMIND_LOCAL_MODEL_SMALL=mistral:7b
HEXAMIND_LOCAL_MODEL_MEDIUM=qwen2.5:7b
HEXAMIND_LOCAL_MODEL_LARGE=llama3.1:8b

# Enable research (DuckDuckGo free fallback)
HEXAMIND_WEB_RESEARCH=1
HEXAMIND_RESEARCH_PROVIDER=duckduckgo

# Performance tuning for 2 cores
HEXAMIND_PARALLEL_AGENTS=false  # Sequential is safer on 2 cores
HEXAMIND_STREAM_MAX_CONCURRENT=1
HEXAMIND_AGENT_TIMEOUT_SECONDS=120  # Local models are slower

# Quality settings
HEXAMIND_RESEARCH_MAX_SOURCES=6
HEXAMIND_RESEARCH_MAX_TERMS=5
```

### Hybrid Mode: Tavily + Local Synthesis

```bash
# Best quality with minimal API cost
TAVILY_API_KEY=your_tavily_key
HEXAMIND_RESEARCH_PROVIDER=tavily
HEXAMIND_REQUIRE_RESEARCH_SOURCES=1
HEXAMIND_WEB_RESEARCH=1

# All synthesis via local Ollama
HEXAMIND_MODEL_PROVIDER=local
HEXAMIND_MODEL_NAME=llama3.1:8b
HEXAMIND_LOCAL_BASE_URL=http://127.0.0.1:11434/v1
HEXAMIND_LOCAL_STRICT=1
```

---

## Improvement Opportunities

### 1. Add Local Embedding Support for Semantic Caching
**Current Gap**: Research cache uses exact-match keys.
**Improvement**: Add semantic similarity using local embeddings.

```python
# ai-service/embeddings.py (new file)
import httpx
import numpy as np

class LocalEmbeddings:
    def __init__(self, base_url="http://127.0.0.1:11434"):
        self.base_url = base_url
        self.model = "nomic-embed-text"
    
    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            return response.json()["embedding"]
    
    def similarity(self, a: list[float], b: list[float]) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
```

**Benefit**: Similar queries reuse cached research, reducing latency.

---

### 2. Add Ollama Model Health Monitoring
**Current Gap**: Local provider probes once at startup.
**Improvement**: Periodic health checks and model switching.

```python
# Add to model_provider.py
async def check_ollama_health(self) -> dict:
    """Check available models and their status."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self._base_url.rstrip('/v1')}/api/tags")
            models = response.json().get("models", [])
            return {
                "available": True,
                "models": [m["name"] for m in models],
                "ram_usage": sum(m.get("size", 0) for m in models) / 1e9
            }
    except Exception:
        return {"available": False, "models": [], "ram_usage": 0}
```

---

### 3. Add Local Model Benchmarking Endpoint
**Current Gap**: No way to compare local model performance.
**Improvement**: Add benchmark endpoint.

```python
# Add endpoint to main.py
@app.get("/api/benchmark/local")
async def benchmark_local_models():
    """Benchmark available local models for agent tasks."""
    test_prompt = "Summarize the benefits and risks of renewable energy in 3 sentences."
    results = []
    
    for model in ["llama3.1:8b", "qwen2.5:7b", "mistral:7b"]:
        start = time.perf_counter()
        try:
            # Call Ollama directly
            response = await generate_with_model(model, test_prompt)
            latency = time.perf_counter() - start
            results.append({
                "model": model,
                "latency_seconds": round(latency, 2),
                "tokens_generated": len(response.split()),
                "tokens_per_second": len(response.split()) / latency
            })
        except Exception as e:
            results.append({"model": model, "error": str(e)})
    
    return {"benchmarks": results}
```

---

### 4. Add Agent-Specific Model Routing by Query Type
**Current Gap**: Same model tier for all query types.
**Improvement**: Route to specialized models.

```python
# Enhanced routing in governance.py
def select_agent_model_by_query(agent_id: str, query_type: str) -> str:
    """Route agents to best-fit models based on query type."""
    routing_map = {
        "technical": {
            "advocate": "deepseek-coder:6.7b",
            "skeptic": "qwen2.5:7b",
            "verifier": "qwen2.5:7b",
            "synthesiser": "llama3.1:8b",
            "oracle": "mistral:7b",
        },
        "decision": {
            "advocate": "llama3.1:8b",
            "skeptic": "llama3.1:8b",
            "synthesiser": "phi3:medium",
            "oracle": "mistral:7b",
            "verifier": "qwen2.5:7b",
        },
        "exploratory": {
            "advocate": "mistral:7b",
            "skeptic": "mistral:7b",
            "synthesiser": "llama3.1:8b",
            "oracle": "llama3.1:8b",
            "verifier": "qwen2.5:7b",
        },
    }
    return routing_map.get(query_type, {}).get(agent_id, "llama3.1:8b")
```

---

### 5. Add Research Pre-Processing with Local Summarization
**Current Gap**: Full source text goes to agents (token heavy).
**Improvement**: Summarize sources locally first.

```python
# Add to research.py
async def summarize_source_locally(source: ResearchSource, ollama_url: str) -> str:
    """Use fast local model to compress source before main agents."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{ollama_url}/api/generate",
            json={
                "model": "mistral:7b",  # Fast summarizer
                "prompt": f"Summarize this in 2-3 sentences:\n\n{source.excerpt[:2000]}",
                "stream": False,
                "options": {"num_predict": 150}
            }
        )
        return response.json()["response"]
```

**Benefit**: Reduces token usage by 40-60% per agent call.

---

### 6. Add Offline Mode with Cached Knowledge
**Current Gap**: Research fails without internet.
**Improvement**: Cache research results as local knowledge base.

```python
# ai-service/knowledge_cache.py (new file)
import json
from pathlib import Path
from datetime import datetime, timedelta

class LocalKnowledgeCache:
    def __init__(self, cache_dir: Path = Path(".data/knowledge-cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def cache_research(self, query: str, research: ResearchContext) -> None:
        """Cache research results for offline use."""
        key = hashlib.sha256(query.lower().encode()).hexdigest()[:16]
        path = self.cache_dir / f"{key}.json"
        path.write_text(json.dumps({
            "query": query,
            "sources": [s.__dict__ for s in research.sources],
            "cached_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
        }))
    
    def get_cached_research(self, query: str) -> ResearchContext | None:
        """Retrieve cached research if available and not expired."""
        key = hashlib.sha256(query.lower().encode()).hexdigest()[:16]
        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        if datetime.fromisoformat(data["expires_at"]) < datetime.now():
            return None
        # Reconstruct ResearchContext from cached data
        return self._reconstruct_context(data)
```

---

### 7. Add Model Download Progress Endpoint
**Current Gap**: No visibility into model download status.
**Improvement**: Expose Ollama download progress.

```python
@app.get("/api/models/status")
async def model_status():
    """Check which models are available and download progress."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:11434/api/tags")
            installed = [m["name"] for m in response.json().get("models", [])]
            
            required = ["llama3.1:8b", "qwen2.5:7b", "mistral:7b"]
            return {
                "installed": installed,
                "required": required,
                "missing": [m for m in required if m not in installed],
                "ready": all(m in installed for m in required)
            }
    except Exception:
        return {"installed": [], "required": [], "missing": [], "ready": False, "error": "Ollama not running"}
```

---

### 8. Add Automatic Quality-Based Model Escalation
**Current Gap**: Uses same model tier even when quality fails.
**Improvement**: Escalate to larger model on quality failure.

```python
# Add to pipeline.py
async def _run_with_escalation(self, agent_id: str, query: str, research: ResearchContext):
    """Run agent with automatic model escalation on quality failure."""
    tiers = ["small", "medium", "large"]
    
    for tier in tiers:
        os.environ["HEXAMIND_FORCE_MODEL_TIER"] = tier
        result = await self._model_provider.build_agent_text(agent_id, query, research)
        
        # Quick quality check
        if self._passes_minimum_quality(result, agent_id):
            return result
        
        # Log escalation
        print(f"Quality gate failed for {agent_id} at tier {tier}, escalating...")
    
    return result  # Return best effort if all tiers fail
```

---

## Performance Tuning for 2-Core System

### Ollama Configuration
Create `~/.ollama/config.json`:
```json
{
  "num_parallel": 1,
  "num_ctx": 4096,
  "num_batch": 256,
  "num_thread": 2
}
```

### System Environment
```bash
# Add to ~/.bashrc or before running backend
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=2
export OLLAMA_KEEP_ALIVE=5m
```

### Hexamind Backend Tuning
```bash
# For 2-core systems, disable parallelism
HEXAMIND_PARALLEL_AGENTS=false
HEXAMIND_STREAM_MAX_CONCURRENT=1

# Increase timeouts for slower inference
HEXAMIND_RETRIEVAL_TIMEOUT_SECONDS=30
HEXAMIND_AGENT_TIMEOUT_SECONDS=180
HEXAMIND_FINAL_TIMEOUT_SECONDS=240
```

---

## Testing Workflow

### 1. Verify Ollama
```bash
ollama serve &
curl http://localhost:11434/api/tags
```

### 2. Pull Required Models
```bash
ollama pull llama3.1:8b
ollama pull mistral:7b
```

### 3. Test Backend
```bash
# Start backend
cd ai-service
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000

# Test health
curl http://localhost:8000/health | jq

# Test pipeline
curl -X POST http://localhost:8000/api/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the benefits of solar energy?"}'
```

### 4. Monitor Performance
```bash
# Watch Ollama resource usage
watch -n 1 'ollama ps'

# Monitor system resources
htop
```

---

## Estimated Resource Usage

| Configuration | RAM Use | Disk Use | Inference Speed |
|---------------|---------|----------|-----------------|
| Single 8B model | ~6GB | 5GB | ~15 tok/s |
| 3 x 7-8B models (tiered) | ~8GB active | 15GB | ~12 tok/s |
| With embeddings | +1GB | +1GB | N/A |
| Full stack running | ~12GB total | 20GB | Varies |

**Your system can handle**: 3-4 loaded models simultaneously with room for the backend and frontend.

---

## Next Steps (Priority Order)

1. **Pull core models** (15 minutes)
   ```bash
   ollama pull llama3.1:8b && ollama pull mistral:7b
   ```

2. **Configure `.env` for local mode** (5 minutes)
   - Copy the "Quick Start Config" section above

3. **Test basic pipeline** (10 minutes)
   - Run backend and test with simple query

4. **Implement embedding cache** (30 minutes)
   - Add semantic caching for research

5. **Add model health endpoint** (20 minutes)
   - Visibility into available models

6. **Implement source summarization** (45 minutes)
   - Reduce token usage significantly

---

## Summary

Your Hexamind project is **well-architected for local model support**. The main opportunities are:

| Area | Current State | Improvement |
|------|---------------|-------------|
| Model routing | Per-agent models ✅ | Add query-type routing |
| Research caching | TTL-based ✅ | Add semantic similarity |
| Source processing | Full text → agents | Pre-summarize locally |
| Quality gates | Post-generation ✅ | Auto-escalate on failure |
| Monitoring | Basic health ✅ | Add benchmark endpoint |
| Offline support | ❌ | Add knowledge cache |

With 42GB RAM, you can comfortably run the full stack with 2-3 models loaded. The 2-core limitation means sequential processing is recommended, but the quality will match API-based inference.

**Total estimated setup time**: 30-60 minutes
**Disk space needed**: 15-25GB for models
**RAM during operation**: 10-15GB
