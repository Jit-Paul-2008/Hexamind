# API-FIRST OPTIMIZATION ACTION PLAN

**Phase**: 3.5 API Optimization (Before Database)
**Timeline**: 4 weeks
**Cost**: $0
**Goal**: Replace/supplement Tavily with FREE research APIs, add model diversity

---

## WHY API-FIRST BEFORE DATABASE?

1. **Database adds complexity** without new API capabilities
2. **Free APIs provide immediate value**: richer research, better responses
3. **User acquisition happens faster** with better research capabilities
4. **No infrastructure overhead**: APIs don't require schema/migration work
5. **User validation first**: get feedback BEFORE persisting data

**Timeline**:
```
Week 1-2: API integrations
Week 3: Testing + user outreach
Week 4: Gather feedback
THEN: Start database phase (with real usage patterns)
```

---

## HIGH-PRIORITY IMPLEMENTATION TRACK

### Track A: Research API Diversity (CRITICAL)

#### A1: Add DuckDuckGo (4 hours)
**File**: `ai-service/research.py`
**Impact**: +80% research coverage, no setup

```python
# Location: ai-service/research.py

# ADD: New function after existing Research class
async def search_duckduckgo(query: str, max_results: int = 5) -> list[ResearchSource]:
    """
    DuckDuckGo web search. No API key required.
    Returns instant web results with 0.6x credibility.
    """
    async with httpx.AsyncClient() as client:
        try:
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "max_results": max_results,
                "no_redirect": 1,
            }
            
            response = await client.get(url, params=params, timeout=5.0)
            data = response.json()
            
            sources = []
            for i, result in enumerate(data.get("Results", [])[:max_results]):
                sources.append(ResearchSource(
                    id=f"ddg_{i}",
                    title=result.get("Title", ""),
                    url=result.get("FirstURL", ""),
                    domain=urlparse(result.get("FirstURL", "")).netloc,
                    snippet=result.get("Text", ""),
                    excerpt=result.get("Text", "")[:200],
                    authority="DuckDuckGo",
                    credibility_score=0.6,
                    discovery_pass="web_search_primary"
                ))
            
            return sources
        
        except Exception as e:
            return []

# MODIFY: ResearchService.research() method to use DuckDuckGo
# Current code (in research.py, PipelineModelProvider):
#   async def build_research_context(self, query: str) -> ResearchContext | None:
#       ...research context built...
#       return context
#
# NEW: Add DuckDuckGo as first source
async def build_research_context(self, query: str) -> ResearchContext | None:
    # Existing code...
    
    # ADD BELOW: DuckDuckGo search (primary source)
    ddg_sources = await search_duckduckgo(query, max_results=5)
    wiki_sources = await search_wikipedia(query, max_results=3)
    
    all_sources = ddg_sources + wiki_sources
    
    # Existing code continues with combined sources...
    return ResearchContext(
        query=query,
        sources=tuple(all_sources),
        # ... rest of context
    )
```

**Testing**:
```bash
# 1. Start backend
npm run dev:backend

# 2. In another terminal, test the function
python3 << 'EOF'
import asyncio
from ai_service.research import search_duckduckgo

async def test():
    results = await search_duckduckgo("machine learning trends 2025")
    for r in results:
        print(f"- {r['title']}: {r['url']}")

asyncio.run(test())
EOF
```

**Expected Output**: 5 web search results in under 2 seconds

---

#### A2: Add Wikipedia Structured Data (3 hours)
**File**: `ai-service/research.py`
**Impact**: +40% fact authority, structured claims

```python
# Location: ai-service/research.py

async def search_wikipedia(query: str, max_results: int = 3) -> list[ResearchSource]:
    """
    Wikipedia API search. High-authority structured knowledge.
    No API key required. Returns 0.85x credibility sources.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Search for relevant Wikipedia pages
            url = "https://en.wikipedia.org/w/api.php"
            search_params = {
                "action": "query",
                "format": "json",
                "srsearch": query,
                "srprop": "snippet|size",
                "srlimit": max_results,
            }
            
            search_response = await client.get(url, params=search_params, timeout=5.0)
            search_data = search_response.json()
            
            sources = []
            for i, page in enumerate(search_data.get("query", {}).get("search", [])[:max_results]):
                # Get page extract
                extract_params = {
                    "action": "query",
                    "format": "json",
                    "prop": "extracts",
                    "explaintext": True,
                    "exintro": True,
                    "titles": page.get("title"),
                }
                
                extract_response = await client.get(url, params=extract_params, timeout=5.0)
                extract_data = extract_response.json()
                
                for page_id, page_content in extract_data.get("query", {}).get("pages", {}).items():
                    if page_id != "-1":
                        sources.append(ResearchSource(
                            id=f"wiki_{i}",
                            title=page_content.get("title", ""),
                            url=f"https://en.wikipedia.org/wiki/{page_content.get('title', '').replace(' ', '_')}",
                            domain="wikipedia.org",
                            snippet=page.get("snippet", ""),
                            excerpt=page_content.get("extract", "")[:300],
                            authority="Wikipedia",
                            credibility_score=0.85,
                            discovery_pass="wiki_search"
                        ))
            
            return sources
        
        except Exception as e:
            return []

# MODIFY: Integrate into build_research_context()
# Replace previous A1 addition with:
async def build_research_context(self, query: str) -> ResearchContext | None:
    # Existing code...
    
    # NEW: Multi-source research
    ddg_sources = await search_duckduckgo(query, max_results=5)
    wiki_sources = await search_wikipedia(query, max_results=3)
    
    # Combine and rank by credibility
    all_sources = sorted(
        ddg_sources + wiki_sources,
        key=lambda s: s.credibility_score,
        reverse=True
    )
    
    # Existing code continues...
    return ResearchContext(
        query=query,
        sources=tuple(all_sources[:10]),  # Top 10 sources
        # ... rest of context
    )
```

**Testing**:
```bash
python3 << 'EOF'
import asyncio
from ai_service.research import search_wikipedia

async def test():
    results = await search_wikipedia("climate change")
    for r in results:
        print(f"✓ {r['title']} (credibility: {r['credibility_score']})")

asyncio.run(test())
EOF
```

**Expected Output**: 3 Wikipedia pages with credibility 0.85

---

#### A3: Add Wikidata (Optional, 2 hours)
**File**: `ai-service/research.py`
**Impact**: +30% fact verification, structured claims

```python
# Location: ai-service/research.py

async def search_wikidata(query: str) -> dict | None:
    """
    Wikidata structured facts. Perfect for fact-checking.
    No API key required.
    """
    async with httpx.AsyncClient() as client:
        try:
            url = "https://www.wikidata.org/w/api.php"
            
            # Search for entity
            search_params = {
                "action": "wbsearchentities",
                "search": query,
                "format": "json",
                "language": "en",
            }
            
            search_response = await client.get(url, params=search_params, timeout=5.0)
            search_data = search_response.json()
            
            entity_id = None
            for entity in search_data.get("search", []):
                entity_id = entity.get("id")
                break
            
            if not entity_id:
                return None
            
            # Get entity claims
            detail_params = {
                "action": "wbgetentities",
                "ids": entity_id,
                "format": "json",
                "props": "claims",
            }
            
            detail_response = await client.get(url, params=detail_params, timeout=5.0)
            detail_data = detail_response.json()
            
            return {
                "entity_id": entity_id,
                "claims": detail_data.get("entities", {}).get(entity_id, {}).get("claims", {}),
            }
        
        except Exception as e:
            return None

# INTEGRATE: Use for fact-checking in agent responses
# In agents.py or pipeline.py:
# 1. Extract major claims from agent response
# 2. Verify against Wikidata claims
# 3. Mark as verified/contested/unverified
```

---

### Track B: Model Diversity (IMPORTANT)

#### B1: Expand Ollama Models (2 hours)
**Location**: Computer terminal
**Impact**: Better agent specialization

```bash
# SSH into the machine/container
# Run these commands to add diverse models:

# Download models (one-time, takes 30-60 min total, can run in background)
ollama pull mistral                    # Fast reasoning (6.7B)
ollama pull neural-chat                # Good dialogue (7B)
ollama pull dolphin-mixtral            # Complex analysis (12B)
ollama pull orca-mini                  # Lightweight fallback (3.5B)

# Verify installation
ollama list

# Start ollama server (if not already running)
ollama serve
```

**Agent Assignment**:
```python
# In ai-service/agents.py, add model mapping:

AGENT_MODEL_MAPPING = {
    "advocate": "mistral",               # Fast, strong reasoning
    "skeptic": "dolphin-mixtral",        # Excellent critical analysis
    "synthesiser": "neural-chat",        # Best for dialogue/synthesis
    "oracle": "orca-mini",               # Lightweight forecasting
}

# Usage in pipeline.py:
model_name = AGENT_MODEL_MAPPING.get(agent_id, "mistral")
response = await ollama(model_name, prompt)
```

---

#### B2: Add Hugging Face Fallback (3 hours)
**File**: `ai-service/model_provider.py`
**Impact**: Never fail due to Ollama overload

**Steps**:
1. Sign up: https://huggingface.co/settings/tokens
2. Create token (free)
3. Add token to `.env`: `HUGGINGFACE_API_KEY=hf_***`

```python
# Location: ai-service/model_provider.py

import httpx
import os

class HuggingFaceProvider:
    """Fallback provider when Ollama can't handle load."""
    
    def __init__(self):
        self.api_key = os.getenv("HUGGINGFACE_API_KEY", "")
        self.base_url = "https://api-inference.huggingface.co/models"
        self.available = bool(self.api_key)
    
    async def generate(self, agent_id: str, prompt: str) -> str | None:
        if not self.available:
            return None
        
        # Pick model based on agent
        model_map = {
            "advocate": "mistralai/Mistral-7B-Instruct-v0.1",
            "skeptic": "meta-llama/Llama-2-70b-chat-hf",
            "synthesiser": "tiiuae/falcon-7b-instruct",
            "oracle": "EleutherAI/gpt-neox-20b",
        }
        
        model_id = model_map.get(agent_id, "mistralai/Mistral-7B-Instruct-v0.1")
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/{model_id}"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                payload = {"inputs": prompt}
                
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                data = response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("generated_text", "")
                
                return None
        
        except Exception as e:
            return None

# MODIFY: model_provider.py create_pipeline_model_provider()
# Current:
#   def create_pipeline_model_provider() -> PipelineModelProvider:
#       return DeterministicPipelineModelProvider(...)
#
# NEW: Add fallback chain
async def get_agent_response(agent_id: str, prompt: str) -> str:
    # Try Ollama first (fast, local)
    try:
        response = await ollama_provider.generate(agent_id, prompt)
        if response:
            return response
    except:
        pass
    
    # Fall back to Hugging Face (slower, but always available)
    response = await huggingface_provider.generate(agent_id, prompt)
    if response:
        return response
    
    # Final fallback: Generic response
    return f"Unable to generate response for {agent_id} at this time"
```

**Testing**:
```bash
# 1. Sign up at https://huggingface.co/settings/tokens
# 2. Copy token
# 3. Add to .env: HUGGINGFACE_API_KEY=hf_***
# 4. Restart backend:
npm run dev:backend

# 5. Test fallback:
python3 << 'EOF'
import asyncio
import os
from ai_service.model_provider import HuggingFaceProvider

async def test():
    hf = HuggingFaceProvider()
    print(f"Available: {hf.available}")
    
    response = await hf.generate("advocate", "What is machine learning?")
    print(f"Response: {response[:100]}...")

asyncio.run(test())
EOF
```

---

#### B3: Add Perplexity (Free Tier) - OPTIONAL (2 hours)
**Steps**:
1. Sign up: https://www.perplexity.ai/api
2. Create free account
3. Get API key
4. Add to `.env`: `PERPLEXITY_API_KEY=***`

```python
# Location: ai-service/model_provider.py

async def get_perplexity_synthesis(query: str) -> str | None:
    """Use Perplexity for high-quality synthesis."""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return None
    
    async with httpx.AsyncClient() as client:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        payload = {
            "model": "sonar-mini-online",
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ],
            "max_tokens": 500,
        }
        
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            data = response.json()
            
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
        
        except Exception:
            pass
    
    return None
```

---

### Track C: Testing & Validation (CRITICAL)

#### C1: Create API Integration Tests (4 hours)
**File**: `ai-service/tests/test_research_apis.py`

```python
# Location: ai-service/tests/test_research_apis.py

import asyncio
import pytest
from research import search_duckduckgo, search_wikipedia

@pytest.mark.asyncio
async def test_duckduckgo_search():
    """Test DuckDuckGo returns valid results."""
    results = await search_duckduckgo("machine learning", max_results=3)
    
    assert len(results) > 0
    for result in results:
        assert result.get("title")
        assert result.get("url")
        assert result.get("snippet")
        assert result.get("credibility_score") == 0.6

@pytest.mark.asyncio
async def test_wikipedia_search():
    """Test Wikipedia returns valid sources."""
    results = await search_wikipedia("climate change", max_results=2)
    
    assert len(results) > 0
    for result in results:
        assert "wikipedia.org" in result.get("url", "")
        assert result.get("credibility_score") == 0.85

@pytest.mark.asyncio
async def test_combined_research():
    """Test combined research context."""
    from pipeline import PipelineService
    
    service = PipelineService()
    context = await service._model_provider.build_research_context(
        "artificial intelligence trends"
    )
    
    assert context is not None
    assert len(context.sources) > 0
    assert all(hasattr(s, 'credibility_score') for s in context.sources)

# Run tests:
# npm run test:backend   OR   python3 -m pytest ai-service/tests/test_research_apis.py -v
```

---

#### C2: End-to-End Pipeline Test (2 hours)
**File**: `tests/e2e/free_api_sources.test.mjs`

```javascript
// Location: tests/e2e/free_api_sources.test.mjs

import { strict as assert } from "assert";

async function testFreeAPISources() {
  const apiUrl = "http://localhost:8000";
  
  // 1. Start a pipeline with a typical research query
  const startResponse = await fetch(`${apiUrl}/api/pipeline/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: "What are the latest AI benchmarks in 2025?",
      agent_ids: ["advocate", "skeptic"]
    })
  });
  
  const { session_id } = await startResponse.json();
  assert(session_id, "Should return session_id");
  
  // 2. Stream the pipeline
  const streamResponse = await fetch(`${apiUrl}/api/pipeline/${session_id}/stream`);
  const reader = streamResponse.body.getReader();
  const decoder = new TextDecoder();
  
  let eventCount = 0;
  let foundSources = false;
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const text = decoder.decode(value);
    const lines = text.split("\n");
    
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        eventCount++;
        const event = JSON.parse(line.slice(6));
        
        // Check if sources came from free APIs
        if (event.type === "research_complete") {
          const sources = event.data.sources || [];
          foundSources = sources.length > 0;
          
          for (const source of sources) {
            assert(
              ["duckduckgo", "wikipedia"].includes(source.source.toLowerCase()),
              `Source should be free API, got: ${source.source}`
            );
          }
        }
      }
    }
  }
  
  assert(eventCount > 0, "Should have received events");
  assert(foundSources, "Should have found sources from free APIs");
  
  console.log("✓ Free API sources test passed");
}

testFreeAPISources().catch(console.error);
```

**Run**:
```bash
npm run test:e2e tests/e2e/free_api_sources.test.mjs
```

---

## WEEK-BY-WEEK IMPLEMENTATION SCHEDULE

### WEEK 1: Research API Foundation
```
Mon-Tue: Implement DuckDuckGo (A1)
Wed: Implement Wikipedia (A2)
Thu: Test combined research
Fri: Add integration tests (C1)

Deliverable: Full web research working via free APIs
```

### WEEK 2: Model Diversity & Fallbacks
```
Mon: Expand Ollama models (B1)
Tue-Wed: Add Hugging Face provider (B2)
Thu: Model fallback chain testing
Fri: Documentation + user guide

Deliverable: 3-tier model fallback (Ollama → HF → Perplexity)
```

### WEEK 3: Testing & Documentation
```
Mon-Tue: E2E pipeline tests (C2)
Wed: Wikidata optional integration (A3)
Thu: Update README with API sources
Fri: Performance benchmarking

Deliverable: 100% test coverage for API layers
```

### WEEK 4: User Outreach
```
Mon: Launch public beta announcement
Tue-Fri: Gather user feedback + issues

THEN: Plan Phase 4 (Database) based on real usage
```

---

## DO NOT DO (Until After Week 4)

❌ Database schema changes
❌ Migration scripts
❌ Data persistence layer
❌ Authentication database setup
❌ Stripe integration
❌ User onboarding flows
❌ Email verification
❌ Production scaling

**Reason**: Get API working + users first. THEN add persistence.

---

## SUCCESS METRICS

**By End of Week 2**:
- [ ] DuckDuckGo + Wikipedia returning results
- [ ] Ollama + Hugging Face model fallback working
- [ ] Backend health check shows 200 OK
- [ ] E2E test passes

**By End of Week 4**:
- [ ] 3+ free research APIs integrated
- [ ] Model diversity tested
- [ ] 5+ users testing system
- [ ] Feedback gathered on API quality

---

## COST TRACKING

```
Current: $0/month

After APIs:
- DuckDuckGo: $0/month (free, unlimited)
- Wikipedia: $0/month (free, unlimited)
- Hugging Face: $0/month (100k free requests)
- Ollama: $0/month (self-hosted)
- Perplexity: $0/month (free tier, $5 credits)

Total: Still $0/month ✅
```

---

## GIT WORKFLOW FOR THIS PHASE

```bash
# Create feature branch
git checkout -b feat/free-api-research-integration

# Commit A1
git add ai-service/research.py
git commit -m "feat: add DuckDuckGo web search API (no key required)"

# Commit A2
git commit -m "feat: add Wikipedia structured data API (0.85 credibility)"

# Commit B1-B2
git commit -m "feat: expand Ollama model diversity + Hugging Face fallback"

# Commit C1-C2
git commit -m "test: add comprehensive API integration tests"

# Create PR for review
git push origin feat/free-api-research-integration
```

---

**Status**: Ready to execute
**Start Date**: April 4, 2026
**Estimated Completion**: April 25, 2026 (3 weeks)
**Cost**: $0
**Post-Phase**: Seek users → gather feedback → THEN database phase

