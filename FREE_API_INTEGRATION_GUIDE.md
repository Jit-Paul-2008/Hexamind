# FREE API Integration Guide — ARIA Complete Specifications

**Status**: Ready to integrate (no keys required for most)
**Cost**: $0 (all free tier or open-source)
**Priority**: Implement in this order

---

## 1. WEB RESEARCH APIs

### 1.1 DuckDuckGo API (NO KEY REQUIRED)
**Status**: ✅ HIGHEST PRIORITY — Zero setup, no rate limits
**Free Tier**: Unlimited
**Rate Limit**: Reasonable fair use (no published limits)
**Integration Points**: Replace/supplement Tavily in research.py

```python
# Implementation Location: ai-service/research.py → search_web()

import httpx

async def search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """
    Free web search via DuckDuckGo API.
    No API key required. No rate limiting enforced.
    """
    async with httpx.AsyncClient() as client:
        # DuckDuckGo endpoint (no auth needed)
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "max_results": max_results,
            "no_redirect": 1,
            "skip_disambig": 1,
        }
        
        response = await client.get(url, params=params)
        data = response.json()
        
        results = []
        for result in data.get("Results", [])[:max_results]:
            results.append({
                "title": result.get("Title", ""),
                "url": result.get("FirstURL", ""),
                "snippet": result.get("Text", ""),
                "source": "DuckDuckGo",
                "credibility": 0.6  # Medium confidence for web search
            })
        return results

# Usage in pipeline:
# 1. research.py imports search_duckduckgo()
# 2. ResearchService uses it as primary source
# 3. Falls back to Wikipedia if no results
```

**Config**: No changes needed. Works as-is.
**Testing**: `python3 -c "import asyncio; from research import search_duckduckgo; asyncio.run(search_duckduckgo('AI adoption 2025'))"`

---

### 1.2 Wikipedia API (NO KEY REQUIRED)
**Status**: ✅ HIGH PRIORITY — Structured knowledge base
**Free Tier**: Unlimited
**Rate Limit**: 200 requests/second (very generous)
**Integration Points**: Structured facts, definitions, historical context

```python
# Implementation Location: ai-service/research.py → extract_wiki_context()

import httpx

async def search_wikipedia(query: str, max_results: int = 3) -> list[dict]:
    """
    Free structured knowledge from Wikipedia.
    No API key required. High authority source.
    """
    async with httpx.AsyncClient() as client:
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "srsearch": query,
            "srprop": "snippet|size|timestamp",
            "srlimit": max_results,
        }
        
        search_response = await client.get(url, params=params)
        search_data = search_response.json()
        
        results = []
        for page in search_data.get("query", {}).get("search", [])[:max_results]:
            # Get full page extract
            extract_params = {
                "action": "query",
                "format": "json",
                "prop": "extracts|info|pageimages",
                "exintro": True,
                "explaintext": True,
                "titles": page.get("title"),
                "piprop": "thumbnail|name",
                "iiprop": "url",
                "pithumbsize": 344,
            }
            
            extract_response = await client.get(url, params=extract_params)
            extract_data = extract_response.json()
            
            pages = extract_data.get("query", {}).get("pages", {})
            for page_id, page_content in pages.items():
                if page_id != "-1":  # Skip missing pages
                    results.append({
                        "title": page_content.get("title", ""),
                        "url": f"https://en.wikipedia.org/wiki/{page_content.get('title', '').replace(' ', '_')}",
                        "snippet": page_content.get("extract", "")[:500],
                        "source": "Wikipedia",
                        "credibility": 0.85,  # High credibility
                        "image": page_content.get("thumbnail", {}).get("source", "")
                    })
        
        return results

# Usage in pipeline:
# 1. Use for factual verification
# 2. Excellent for historical context, definitions
# 3. Add to research sources with credibility 0.85
```

**Config**: No changes needed.
**Testing**: `python3 -c "import asyncio; from research import search_wikipedia; asyncio.run(search_wikipedia('Machine Learning'))"`

---

### 1.3 Perplexity Sonar (FREE TIER)
**Status**: ⏳ MEDIUM PRIORITY — Better than both, but needs key
**Free Tier**: Requires free account, then unlimited (rate-limited)
**Rate Limit**: 3 requests/minute on free tier
**Integration Points**: Higher-quality synthesis

```
Sign up: https://www.perplexity.ai/api
Free API Key: Yes (after sign-up)
Keep Quota: 1000 queries/month on free
Cost: $0 for MVP
```

```python
# Implementation Location: ai-service/research.py → search_perplexity()

import httpx
import os

async def search_perplexity(query: str) -> dict:
    """
    Free AI-powered search via Perplexity API.
    Requires free API key (1000 queries/month).
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return None  # Skip if key not provided
    
    async with httpx.AsyncClient() as client:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        payload = {
            "model": "sonar-mini-online",  # Free model
            "messages": [
                {
                    "role": "user",
                    "content": f"Search the web and provide a concise, factual answer to: {query}"
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500,
        }
        
        response = await client.post(url, json=payload, headers=headers)
        data = response.json()
        
        return {
            "answer": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
            "source": "Perplexity",
            "credibility": 0.8,
        }

# Add to .env:
# PERPLEXITY_API_KEY=*** (optional)

# Usage in pipeline:
# 1. If key available, use as primary synthesis
# 2. Falls back to DuckDuckGo + Wikipedia
```

**Config**: Add `PERPLEXITY_API_KEY=` to .env (optional, leave empty for MVP)
**Testing**: `python3 -c "import asyncio; from research import search_perplexity; asyncio.run(search_perplexity('Latest AI news'))"`

---

### 1.4 Wikidata API (NO KEY REQUIRED)
**Status**: ⏳ MEDIUM PRIORITY — Structured data, relationships
**Free Tier**: Unlimited
**Rate Limit**: 10 requests/second
**Integration Points**: Fact checking, entity relationships, structured claims

```python
# Implementation Location: ai-service/research.py → extract_wikidata_facts()

import httpx

async def search_wikidata(query: str) -> dict:
    """
    Structured knowledge from Wikidata.
    Great for: entity relationships, facts, claims with dates.
    No API key required.
    """
    async with httpx.AsyncClient() as client:
        url = "https://www.wikidata.org/w/api.php"
        
        # First: Search for entity
        search_params = {
            "action": "wbsearchentities",
            "search": query,
            "format": "json",
            "language": "en",
            "limit": 1,
        }
        
        search_response = await client.get(url, params=search_params)
        search_data = search_response.json()
        
        entity_id = None
        for entity in search_data.get("search", []):
            entity_id = entity.get("id")
            break
        
        if not entity_id:
            return None
        
        # Second: Get entity details
        detail_params = {
            "action": "wbgetentities",
            "ids": entity_id,
            "format": "json",
            "props": "info|claims|descriptions",
        }
        
        detail_response = await client.get(url, params=detail_params)
        detail_data = detail_response.json()
        
        return {
            "entity_id": entity_id,
            "claims": detail_data.get("entities", {}).get(entity_id, {}).get("claims", {}),
            "descriptions": detail_data.get("entities", {}).get(entity_id, {}).get("descriptions", {}),
            "source": "Wikidata",
            "credibility": 0.75,
        }

# Usage: Entity relationships, fact checking
```

**Config**: No changes needed.

---

## 2. AI MODEL APIs (Free Tier)

### 2.1 Ollama (Already Integrated)
**Status**: ✅ ACTIVE — Already in use
**Free**: Yes (self-hosted, no API costs)
**Models Available**:
```
ollama list  # See installed models
ollama pull mistral  # Download new models
ollama pull neural-chat
ollama pull dolphin-mixtral
```

**Current Usage**: src/lib/api/pipeline.ts calls `LOCALHOST:11434`
**To Optimize**:
```bash
# Add more diverse models for different tasks
ollama pull mistral        # Fast reasoning
ollama pull neural-chat    # Dialogue
ollama pull dolphin-mixtral # Complex analysis
ollama pull orca-mini      # Lightweight

# Use per-agent:
# Advocate: mistral (strong reasoning)
# Skeptic: orca (critical analysis)
# Synthesiser: neural-chat (dialogue)
# Oracle: dolphin-mixtral (forecasting)
```

---

### 2.2 Hugging Face Inference API (FREE TIER)
**Status**: ⏳ HIGH PRIORITY — Fallback when Ollama overloaded
**Free Tier**: 100,000 requests/month (plenty for MVP)
**Rate Limit**: Bursty but generous
**Setup**: https://huggingface.co/settings/tokens → Create token

```python
# Implementation Location: ai-service/model_provider.py → add_huggingface_provider()

import httpx
import os

class HuggingFaceProvider:
    """Free API access to 1000+ open models on Hugging Face."""
    
    def __init__(self):
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.base_url = "https://api-inference.huggingface.co/models"
    
    async def generate(self, model_id: str, prompt: str, max_tokens: int = 500):
        """
        model_id examples:
        - mistralai/Mistral-7B-Instruct-v0.1
        - meta-llama/Llama-2-70b-chat-hf
        - tiiuae/falcon-7b-instruct
        - EleutherAI/gpt-j-6b
        """
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/{model_id}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "inputs": prompt,
                "parameters": {"max_length": max_tokens},
            }
            
            response = await client.post(url, json=payload, headers=headers)
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("generated_text", "")
            
            return None

# Add to .env:
# HUGGINGFACE_API_KEY=hf_*** (get from https://huggingface.co/settings/tokens)

# Strategy:
# 1. Try Ollama first (fastest, free)
# 2. Fall back to Hugging Face if Ollama busy
# 3. Fall back to OpenRouter if both busy
```

**Models to use**:
```json
{
  "fast": "mistralai/Mistral-7B-Instruct-v0.1",
  "strong": "meta-llama/Llama-2-70b-chat-hf",
  "fast-alternative": "tiiuae/falcon-7b-instruct",
  "lightweight": "EleutherAI/gpt-neox-20b"
}
```

---

### 2.3 OpenRouter API (FREE TIER)
**Status**: ⏳ MEDIUM PRIORITY — Multi-model fallback, free credits
**Free Tier**: $5 free credits (enough for 100-200k tokens)
**Rate Limit**: Very generous on free tier
**Setup**: https://openrouter.ai/ → Create account → Copy key

```python
# Implementation Location: ai-service/model_provider.py → add_openrouter_provider()

import httpx
import os

class OpenRouterProvider:
    """Free API with $5 credits + free models."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    async def generate(self, model: str, messages: list, temperature: float = 0.7):
        """
        Free model examples:
        - gpt-3.5-turbo (free tier limit)
        - mistral-tiny
        - mistral-small
        - neural-chat-7b (free tier)
        - orca-2-13b (free tier, excellent)
        """
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            
            response = await client.post(self.base_url, json=payload, headers=headers)
            data = response.json()
            
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            
            return None

# Add to .env:
# OPENROUTER_API_KEY=sk-or-*** (get from https://openrouter.ai/)

# Free models (no credit cost):
free_models = [
    "mistralai/mistral-7b-instruct",
    "meta-llama/orca-2-13b",
    "nousresearch/nous-hermes-2-mixtral-8x7b-dpo",
]

# Paid models (use $5 credits):
paid_models = [
    "meta-llama/llama-2-70b-chat",
    "mistralai/mixtral-8x7b-instruct",
    "gpt-3.5-turbo",
]
```

---

## 3. DATA & EMBEDDINGS

### 3.1 Sentence Transformers (LOCAL, NO API)
**Status**: ✅ Ready to use — No API key needed
**Free**: Yes (open-source)
**Speed**: Fast (runs locally)
**Use Case**: Semantic search, relevance scoring

```python
# Already available for local use
# Installation: pip install sentence-transformers

from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, free

query_embedding = model.encode("machine learning trends")
source_embeddings = [
    model.encode("AI is transforming industry"),
    model.encode("Deep learning advances"),
]

# Calculate semantic similarity (no API call)
similarities = model.similarity(query_embedding, source_embeddings)
```

**Integration**: Add to ai-service/embeddings.py (already partially there)

---

### 3.2 Hugging Face Embeddings API (FREE)
**Status**: ⏳ Optional — If local embeddings insufficient
**Free Tier**: Same as inference API (100k requests/month)
**Use Case**: Backup embeddings provider

```python
import httpx
import os

async def get_embeddings_huggingface(texts: list[str]) -> list:
    """Cloud-hosted embeddings if local unavailable."""
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    
    url = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={"inputs": texts}, headers=headers)
        return response.json()
```

---

## 4. STORAGE & ARTIFACTS

### 4.1 Supabase (FREE TIER)
**Status**: ⏳ LATER (Phase 4+) — When artifacts needed
**Free Tier**: 500MB storage, PostgreSQL included
**Setup**: https://supabase.com
**Cost**: $0 for MVP

```python
# Future integration: ai-service/storage.py
# Not needed yet (use local filesystem for now)

# When needed:
from supabase import create_client

supabase = create_client(
    supabase_url="https://<project>.supabase.co",
    supabase_key=os.getenv("SUPABASE_KEY")
)

# Upload artifact
supabase.storage.from_("artifacts").upload(
    file_path="report_123.docx",
    file=open("report.docx", "rb")
)
```

---

### 4.2 Firebase (FREE TIER)
**Status**: ⏳ LATER — Cloud Firestore + Storage
**Free Tier**: 1GB storage, 50k reads/day
**Setup**: https://firebase.google.com
**Cost**: $0 for MVP

---

## 5. MONITORING & OBSERVABILITY

### 5.1 Grafana Cloud (FREE TIER)
**Status**: ⏳ LATER (Phase 5) — Production monitoring
**Free Tier**: 10k metrics/month
**Setup**: https://grafana.cloud
**Cost**: $0 for MVP

```python
# Future: Deploy Prometheus metrics to Grafana Cloud
# Currently: Local only (Prometheus + Grafana containers exist)
```

---

## 6. IMPLEMENTATION ROADMAP

### Week 1 (Immediate)
1. ✅ Add DuckDuckGo API (no setup)
2. ✅ Add Wikipedia API (no setup)
3. ✅ Test combined research sources

### Week 2
4. Add Hugging Face Inference (free key signup)
5. Add Ollama model diversity (mistral, dolphin, neural-chat)
6. Test model fallback chain: Ollama → HF → OpenRouter

### Week 3
7. Add Wikidata (structured facts)
8. Optional: Add Perplexity (if signup done)
9. Build user-facing research source visualization

### Week 4+
10. Seek users, gather feedback
11. **THEN** add database persistence
12. **THEN** add Supabase/Firebase storage

---

## 7. PRIORITY MATRIX

| API | Setup Time | Value | Dependency | Priority |
|-----|-----------|-------|-----------|----------|
| DuckDuckGo | <5min | High | None | 1 (NOW) |
| Wikipedia | <5min | High | None | 1 (NOW) |
| Ollama Models | 10min | High | None | 2 (THIS WEEK) |
| Hugging Face | 15min | Medium | HF signup | 2 (THIS WEEK) |
| Perplexity | 20min | Medium | Perplexity signup | 3 (OPTIONAL) |
| OpenRouter | 15min | Medium | OpenRouter signup | 3 (OPTIONAL) |
| Wikidata | 5min | Medium | None | 2 (THIS WEEK) |
| Supabase | 30min | Low | Not yet needed | 4 (PHASE 4) |
| Grafana Cloud | 20min | Low | Not yet needed | 4 (PHASE 5) |

---

## 8. CONFIGURATION SUMMARY

**Update .env with**:
```bash
# FREE (no signup needed)
NEXT_PUBLIC_API_URL=http://localhost:8000
OLLAMA_BASE_URL=http://localhost:11434

# FREE (signup required, optional)
HUGGINGFACE_API_KEY=hf_***
PERPLEXITY_API_KEY=***
OPENROUTER_API_KEY=sk-or-***
```

---

## 9. TESTING EACH API

```bash
# Test DuckDuckGo
python3 -c "
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        r = await client.get('https://api.duckduckgo.com/', 
            params={'q': 'AI 2025', 'format': 'json'})
        print(r.json())

asyncio.run(test())
"

# Test Wikipedia
python3 -c "
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        r = await client.get('https://en.wikipedia.org/w/api.php',
            params={'action': 'query', 'srsearch': 'AI', 'format': 'json'})
        print(r.json())

asyncio.run(test())
"

# Test Ollama (if running)
curl http://localhost:11434/api/tags

# Test Hugging Face (if key set)
curl -H "Authorization: Bearer YOUR_KEY" \
  https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1 \
  -X POST \
  -d '{"inputs":"Hello world"}'
```

---

**Status**: Ready to implement
**Cost**: $0 (all free tier)
**Setup time**: 4-6 hours for all APIs
**Value**: 10x richer research capabilities without database complexity

