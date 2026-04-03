# Hexamind API Improvements & Power-Maxing Ideas

> A comprehensive list of refinements, optimizations, and advanced features to improve token efficiency, agent customization, and overall system power.

---

## 1. Token Optimization Strategies

### 1.1 Prompt Engineering Optimizations

| Strategy | Current State | Improvement | Estimated Token Savings |
|----------|---------------|-------------|------------------------|
| **Shared Instruction Deduplication** | Each agent has full system prompt with repeated instructions | Extract common instructions to a single "base prompt" module, inject agent-specific deltas only | 30-40% per agent call |
| **Dynamic Prompt Pruning** | Full prompts sent regardless of query complexity | For simple queries, use minimal prompts; for complex ones, inject additional guidance | 15-25% for simple queries |
| **Citation Format Simplification** | `"Citations Used"` section + inline `[S1]` | Use inline-only citations, drop redundant section | 5-10% per agent |
| **Section Header Compression** | `"## Opportunity Thesis"`, `"## Strategic Upside"` | Use compact headers: `"## Thesis"`, `"## Upside"` in prompts; expand in post-processing | 3-5% |

**Implementation Idea:**
```python
# Instead of:
prompts = {
    "advocate": "You are ADVOCATE in ARIA research-paper mode. Focus on evidence-backed benefits...[400 chars]",
    "skeptic": "You are SKEPTIC in ARIA research-paper mode. Focus on failure modes...[400 chars]",
}

# Use:
BASE_PROMPT = "You are {agent} in ARIA mode. RULE: Every claim cites [Sx]. Keep focused."
DELTA_PROMPTS = {
    "advocate": "Focus: benefits, upside, strategic value. Sections: Thesis, Upside, Logic, Action.",
    "skeptic": "Focus: risks, failure modes, worst-case. Sections: Risks, Triggers, Mitigations.",
}
# Final: BASE_PROMPT.format(agent=id) + " " + DELTA_PROMPTS[id]  # ~60% shorter
```

### 1.2 Context Window Management

| Strategy | Description | Token Impact |
|----------|-------------|--------------|
| **Source Excerpt Compression** | Current: 600 chars per source. Use extractive summarization to 200 chars | 60% reduction in research context |
| **Agent Output Chaining** | Currently passing all 5 agent outputs to final stage. Pass only diffs/summaries | 40-50% reduction in final stage |
| **Semantic Deduplication** | Sources often overlap. Hash sentence embeddings, skip near-duplicates | 10-20% reduction |
| **Query-Aware Pruning** | If query is about "risks", heavily truncate advocate output before final | Variable, up to 25% |

**Implementation Idea - Compressed Agent Passing:**
```python
# Current (token-heavy):
agent_outputs = {
    "advocate": "[full 800 word output]",
    "skeptic": "[full 800 word output]",
    ...
}

# Optimized:
agent_outputs = {
    "advocate": summarize(advocate_output, max_words=150),
    "skeptic": summarize(skeptic_output, max_words=150),
    "advocate_full": advocate_output,  # kept in memory, not sent to API
}
# Only summaries go to final composition; full text injected post-hoc if needed
```

### 1.3 Caching & Memoization Enhancements

| Enhancement | Current | Proposed |
|-------------|---------|----------|
| **Prompt Hash Cache** | None | Cache API responses by `hash(system_prompt + user_prompt[:500])`. TTL: 1 hour. |
| **Semantic Query Cache** | Exact-match on query string | Use embedding similarity (cosine > 0.95) for cache hits |
| **Agent Output Cache** | None | Cache agent outputs per `(query_hash, agent_id, research_hash)` |
| **Research Pre-Fetch** | On-demand | Background-fetch trending/common queries to warm cache |

**Token Savings Estimate:** 20-50% for repeated/similar queries.

### 1.4 Model Selection Optimization

| Strategy | Description |
|----------|-------------|
| **Tiered Model Assignment** | Use cheaper/smaller models for simpler agents (advocate, skeptic) and premium models for complex ones (synthesiser, final) |
| **Query Routing** | Simple yes/no queries → 8B model; complex comparative analysis → 70B model |
| **Speculative Decoding** | Use small model to draft, large model to verify/refine (reduces total tokens if draft is often accepted) |

**Proposed Config:**
```env
# Tiered assignment (smaller = cheaper)
HEXAMIND_AGENT_MODEL_ADVOCATE=llama-3.1-8b-instant      # Fast, cheap
HEXAMIND_AGENT_MODEL_SKEPTIC=llama-3.1-8b-instant       # Fast, cheap
HEXAMIND_AGENT_MODEL_SYNTHESISER=llama-3.1-70b          # Complex reasoning
HEXAMIND_AGENT_MODEL_ORACLE=mixtral-8x7b                # Good speculation
HEXAMIND_AGENT_MODEL_VERIFIER=llama-3.1-8b-instant      # Rule-based checking
HEXAMIND_AGENT_MODEL_FINAL=llama-3.1-70b                # Premium composition
```

---

## 2. Agent Fine-Tuning & Custom API Keys

### 2.1 Per-Agent Fine-Tuning Architecture

**Current Limitation:** All agents use the same base model with different prompts.

**Proposed Solution:** Fine-tune separate LoRA adapters per agent role.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Base Model (Llama 3.1 8B)                    │
├───────────────┬───────────────┬───────────────┬─────────────────┤
│   LoRA:       │   LoRA:       │   LoRA:       │   LoRA:         │
│   Advocate    │   Skeptic     │   Synthesiser │   Verifier      │
│   (optimism)  │   (criticism) │   (balance)   │   (fact-check)  │
└───────────────┴───────────────┴───────────────┴─────────────────┘
```

**Implementation Steps:**
1. Collect 500-1000 examples of ideal agent outputs per role
2. Fine-tune LoRA adapters (rank 8-16) on each dataset
3. Deploy via vLLM or Ollama with adapter hot-swapping
4. Config: `HEXAMIND_AGENT_ADAPTER_ADVOCATE=adapters/advocate-v2.safetensors`

**Benefits:**
- 50-70% shorter prompts (role internalized in weights)
- More consistent output style
- Better domain alignment

### 2.2 Per-Agent API Key Assignment

**Use Case:** Different billing, rate limits, or providers per agent.

**Proposed Config:**
```env
# Global fallback
OPENROUTER_API_KEY=sk-global-key

# Per-agent overrides
HEXAMIND_AGENT_API_KEY_ADVOCATE=sk-advocate-dedicated-key
HEXAMIND_AGENT_API_KEY_SKEPTIC=sk-skeptic-dedicated-key
HEXAMIND_AGENT_API_KEY_SYNTHESISER=sk-synthesiser-premium-key
HEXAMIND_AGENT_API_KEY_FINAL=sk-final-high-limit-key

# Per-agent provider override
HEXAMIND_AGENT_PROVIDER_ADVOCATE=groq
HEXAMIND_AGENT_PROVIDER_SYNTHESISER=openrouter
HEXAMIND_AGENT_PROVIDER_FINAL=gemini
```

**Implementation:**
```python
def get_agent_config(agent_id: str) -> tuple[str, str, str]:
    """Returns (api_key, base_url, model) for agent."""
    provider = os.getenv(f"HEXAMIND_AGENT_PROVIDER_{agent_id.upper()}", DEFAULT_PROVIDER)
    api_key = os.getenv(f"HEXAMIND_AGENT_API_KEY_{agent_id.upper()}", get_default_key(provider))
    model = os.getenv(f"HEXAMIND_AGENT_MODEL_{agent_id.upper()}", DEFAULT_MODEL)
    return api_key, PROVIDER_URLS[provider], model
```

### 2.3 Agent Hot-Swap & A/B Testing

**Concept:** Run multiple agent versions simultaneously, compare outputs.

```python
@dataclass
class AgentVersion:
    id: str
    adapter_path: str | None
    prompt_version: str
    traffic_weight: float  # 0.0 - 1.0

AGENT_VERSIONS = {
    "advocate": [
        AgentVersion("advocate-v1", None, "v1", 0.7),
        AgentVersion("advocate-v2-finetuned", "lora/advocate-v2", "v2", 0.3),
    ]
}

def select_agent_version(agent_id: str) -> AgentVersion:
    versions = AGENT_VERSIONS[agent_id]
    return random.choices(versions, weights=[v.traffic_weight for v in versions])[0]
```

---

## 3. Parallel & Async Optimizations

### 3.1 Parallel Agent Execution

**Current:** Sequential execution (Advocate → Skeptic → Synthesiser → Oracle → Verifier → Final)

**Proposed:** Parallel-then-merge pattern:

```
         ┌─► Advocate  ──┐
Query ──►├─► Skeptic   ──┼──► Synthesiser ──► Final
         ├─► Oracle    ──┤
         └─► Verifier  ──┘
```

**Implementation:**
```python
async def run_parallel_agents(query: str, research: ResearchContext):
    # Phase 1: Independent agents (parallel)
    results = await asyncio.gather(
        build_agent_text("advocate", query, research),
        build_agent_text("skeptic", query, research),
        build_agent_text("oracle", query, research),
        build_agent_text("verifier", query, research),
    )
    
    # Phase 2: Dependent agent (needs phase 1 outputs)
    synthesis = await build_agent_text("synthesiser", query, research, prior_outputs=results)
    
    # Phase 3: Final composition
    return await compose_final_answer(query, {**results, "synthesiser": synthesis}, research)
```

**Benefit:** ~60% faster wall-clock time (4 parallel calls instead of 5 sequential).

### 3.2 Speculative Agent Execution

**Concept:** Start expensive agents early with estimated inputs, cancel if estimation diverges.

```python
async def speculative_synthesis(query, research, advocate_partial):
    """Start synthesis with partial advocate output, update as more arrives."""
    synthesis_task = asyncio.create_task(
        build_agent_text("synthesiser", query, research, 
                        advocate_estimate=advocate_partial)
    )
    
    full_advocate = await stream_advocate_output(query, research)
    
    if divergence(advocate_partial, full_advocate) > 0.3:
        synthesis_task.cancel()
        return await build_agent_text("synthesiser", query, research, 
                                      advocate=full_advocate)
    return await synthesis_task
```

### 3.3 Streaming Token Budget

**Current:** Fixed token budgets per stage.

**Proposed:** Dynamic reallocation based on streaming output.

```python
class StreamingTokenBudget:
    def __init__(self, total_budget: int):
        self.total = total_budget
        self.used = 0
        self.agent_budgets = {}
    
    def allocate_agent(self, agent_id: str, estimated_need: int) -> int:
        remaining = self.total - self.used
        allocated = min(estimated_need, remaining * 0.3)  # Max 30% per agent
        self.agent_budgets[agent_id] = allocated
        return allocated
    
    def release_unused(self, agent_id: str, actual_used: int):
        allocated = self.agent_budgets[agent_id]
        self.used += actual_used
        # Unused tokens return to pool for later agents
        self.total += (allocated - actual_used) * 0.8  # 80% recovery
```

---

## 4. Quality & Output Enhancements

### 4.1 Adaptive Quality Gates

**Current:** Fixed section requirements.

**Proposed:** Query-aware quality criteria.

```python
def get_quality_requirements(query: str, research: ResearchContext) -> QualityGate:
    complexity = research.workflow_profile.complexity_score
    
    if "compare" in query.lower() or "vs" in query.lower():
        return QualityGate(
            required_sections=["Comparison Matrix", "Tradeoff Analysis"],
            min_sources=4,
            min_citations=6,
        )
    elif complexity < 0.3:
        return QualityGate(
            required_sections=["Summary", "Key Points"],
            min_sources=2,
            min_citations=2,
        )
    else:
        return DEFAULT_QUALITY_GATE
```

### 4.2 Self-Correction Loop

**Concept:** If output fails quality gate, auto-retry with feedback.

```python
MAX_RETRIES = 2

async def compose_with_correction(query, agent_outputs, research):
    for attempt in range(MAX_RETRIES + 1):
        result = await compose_final_answer(query, agent_outputs, research)
        quality = validate_output(result, query, research)
        
        if quality.passed:
            return result
        
        # Inject correction feedback into next attempt
        correction_prompt = f"""
        Previous output failed quality check:
        - Missing sections: {quality.missing_sections}
        - Citation count: {quality.citation_count} (need {quality.min_citations})
        - Issues: {quality.issues}
        
        Please regenerate addressing these gaps.
        """
        agent_outputs["_correction"] = correction_prompt
    
    return result  # Return best effort after retries
```

### 4.3 Citation Verification Pipeline

**Concept:** Post-process citations to verify claims match sources.

```python
async def verify_citations(report: str, sources: list[ResearchSource]) -> VerificationResult:
    citations = extract_citations(report)  # [(claim, source_id), ...]
    
    results = []
    for claim, source_id in citations:
        source = find_source(sources, source_id)
        match = await verify_claim_against_source(claim, source.excerpt)
        results.append(CitationVerification(claim, source_id, match.score, match.issues))
    
    return VerificationResult(
        verified_count=sum(1 for r in results if r.score > 0.7),
        total_citations=len(citations),
        issues=[r for r in results if r.score < 0.5],
    )
```

---

## 5. Advanced Architecture Patterns

### 5.1 Agent Memory & State

**Current:** Stateless agents, no memory of past queries.

**Proposed:** Session-level memory for continuity.

```python
class AgentMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.query_history: list[str] = []
        self.key_facts: list[str] = []
        self.user_preferences: dict = {}
        self.past_outputs: dict[str, str] = {}
    
    def get_context_injection(self, agent_id: str) -> str:
        if not self.query_history:
            return ""
        
        return f"""
        CONTEXT: User previously asked about: {', '.join(self.query_history[-3:])}
        Known preferences: {self.user_preferences}
        Maintain consistency with prior analysis.
        """

# Usage:
memory = AgentMemory(session_id)
memory.query_history.append(query)
context = memory.get_context_injection("synthesiser")
prompt = base_prompt + context
```

### 5.2 Hierarchical Agent Orchestration

**Current:** Flat agent structure, fixed execution order.

**Proposed:** Dynamic agent graphs based on query type.

```python
AGENT_GRAPHS = {
    "comparative": ["advocate", "skeptic", ("oracle", "verifier"), "synthesiser", "final"],
    "simple_question": ["oracle", "final"],  # Skip most agents
    "risk_analysis": ["skeptic", "verifier", "oracle", "final"],
    "opportunity_scan": ["advocate", "oracle", "final"],
}

def select_agent_graph(query: str, research: ResearchContext) -> list:
    if "compare" in query.lower() or "vs" in query.lower():
        return AGENT_GRAPHS["comparative"]
    if research.workflow_profile.complexity_score < 0.3:
        return AGENT_GRAPHS["simple_question"]
    if "risk" in query.lower():
        return AGENT_GRAPHS["risk_analysis"]
    return AGENT_GRAPHS["comparative"]  # Default
```

### 5.3 Retrieval-Augmented Generation (RAG) Integration

**Current:** Web research only.

**Proposed:** Multi-source RAG with domain-specific indexes.

```python
class MultiSourceRAG:
    def __init__(self):
        self.sources = {
            "web": InternetResearcher(),
            "academic": ArxivSearcher(),
            "medical": PubMedSearcher(),
            "legal": LegalDatabaseSearcher(),
            "internal": VectorDBSearcher("company_docs"),
        }
    
    def select_sources(self, query: str) -> list[str]:
        # Route based on query domain
        if any(kw in query.lower() for kw in ["paper", "study", "research"]):
            return ["academic", "web"]
        if any(kw in query.lower() for kw in ["medical", "clinical", "patient"]):
            return ["medical", "academic"]
        return ["web"]
    
    async def research(self, query: str) -> ResearchContext:
        selected = self.select_sources(query)
        results = await asyncio.gather(*[
            self.sources[s].search(query) for s in selected
        ])
        return merge_research_contexts(results)
```

---

## 6. Cost & Billing Optimizations

### 6.1 Token Budgeting System

```python
@dataclass
class TokenBudget:
    total_limit: int = 50000  # Per session
    research_limit: int = 10000
    agent_limit: int = 8000  # Per agent
    final_limit: int = 15000
    
    used: int = 0
    
    def can_afford(self, estimated_tokens: int) -> bool:
        return self.used + estimated_tokens <= self.total_limit
    
    def charge(self, actual_tokens: int):
        self.used += actual_tokens
        logger.info(f"Token usage: {self.used}/{self.total_limit}")

# Enforce budget in API calls:
async def build_agent_text(agent_id, query, research, budget: TokenBudget):
    estimated = estimate_tokens(query, research)
    if not budget.can_afford(estimated):
        return generate_budget_exceeded_fallback(agent_id, query)
    
    result = await call_api(...)
    budget.charge(count_tokens(result))
    return result
```

### 6.2 Cost-Aware Model Selection

```python
MODEL_COSTS = {  # $ per 1M tokens
    "llama-3.1-8b": 0.05,
    "llama-3.1-70b": 0.90,
    "gemini-2.0-flash": 0.15,
    "gpt-4-turbo": 10.00,
}

def select_cheapest_capable_model(task_complexity: float, budget_remaining: float) -> str:
    affordable = [
        model for model, cost in MODEL_COSTS.items()
        if cost <= budget_remaining / 10000  # Assume 10k tokens
    ]
    
    if task_complexity > 0.7:
        # Need capable model
        return max(affordable, key=lambda m: MODEL_COSTS[m])
    else:
        # Use cheapest
        return min(affordable, key=lambda m: MODEL_COSTS[m])
```

### 6.3 Batching & Request Coalescing

**Concept:** Combine multiple user queries into single API calls.

```python
class RequestBatcher:
    def __init__(self, batch_window_seconds: float = 0.5):
        self.pending: list[tuple[str, asyncio.Future]] = []
        self.window = batch_window_seconds
    
    async def add_request(self, prompt: str) -> str:
        future = asyncio.Future()
        self.pending.append((prompt, future))
        
        if len(self.pending) == 1:
            asyncio.create_task(self._flush_after_window())
        
        return await future
    
    async def _flush_after_window(self):
        await asyncio.sleep(self.window)
        batch = self.pending.copy()
        self.pending.clear()
        
        # Single API call with all prompts
        results = await batch_api_call([p for p, _ in batch])
        
        for (_, future), result in zip(batch, results):
            future.set_result(result)
```

---

## 7. Observability & Debugging

### 7.1 Token Usage Dashboard

```python
@dataclass
class TokenUsageReport:
    session_id: str
    query: str
    stages: dict[str, StageUsage]
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    
@dataclass
class StageUsage:
    stage: str  # research, advocate, skeptic, ...
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float

def generate_usage_report(session: PipelineSession) -> TokenUsageReport:
    # Aggregate from all stages
    ...
```

### 7.2 Prompt Version Tracking

```python
# Track prompt changes over time
PROMPT_VERSIONS = {
    "advocate-v1": {
        "text": "You are ADVOCATE...",
        "created_at": "2024-01-15",
        "performance_score": 0.82,
    },
    "advocate-v2": {
        "text": "You are ADVOCATE (optimized)...",
        "created_at": "2024-02-20",
        "performance_score": 0.89,
    },
}

def log_prompt_performance(version: str, output_quality: float):
    # Feed into A/B testing analysis
    ...
```

### 7.3 Automated Regression Testing

```python
TEST_CASES = [
    {"query": "Compare React vs Vue for enterprise apps", "expected_sections": ["Comparison", "Tradeoffs"]},
    {"query": "What are the risks of microservices?", "expected_sections": ["Risks", "Mitigations"]},
]

async def run_regression_suite():
    results = []
    for case in TEST_CASES:
        output = await run_pipeline(case["query"])
        quality = validate_output(output, case)
        results.append({"case": case["query"], "passed": quality.passed, "issues": quality.issues})
    
    return results
```

---

## 8. Security & Multi-Tenancy

### 8.1 Per-Tenant API Key Isolation

```python
class TenantConfig:
    tenant_id: str
    api_keys: dict[str, str]  # provider -> key
    rate_limits: dict[str, int]  # endpoint -> rpm
    token_budget: int
    allowed_models: list[str]
    
TENANTS = {
    "tenant_a": TenantConfig(..., api_keys={"groq": "key_a"}),
    "tenant_b": TenantConfig(..., api_keys={"openrouter": "key_b"}),
}

def get_tenant_config(request: Request) -> TenantConfig:
    tenant_id = request.headers.get("X-Tenant-ID")
    return TENANTS[tenant_id]
```

### 8.2 PII Redaction Pipeline

```python
import re

PII_PATTERNS = [
    (r'\b[\w.-]+@[\w.-]+\.\w+\b', '[EMAIL]'),
    (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]'),
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),
]

def redact_pii(text: str) -> str:
    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text

# Apply before sending to API:
sanitized_query = redact_pii(user_query)
result = await call_api(sanitized_query)
```

---

## 9. Implementation Priority Matrix

| Improvement | Impact | Effort | Priority |
|-------------|--------|--------|----------|
| Prompt deduplication (1.1) | High | Low | 🔥 P0 |
| Parallel agent execution (3.1) | High | Medium | 🔥 P0 |
| Per-agent model assignment (1.4) | High | Low | 🔥 P0 |
| Research context compression (1.2) | Medium | Medium | 🟡 P1 |
| Semantic query cache (1.3) | Medium | Medium | 🟡 P1 |
| Per-agent API keys (2.2) | Medium | Low | 🟡 P1 |
| Agent fine-tuning (2.1) | Very High | High | 🟢 P2 |
| Self-correction loop (4.2) | Medium | Medium | 🟢 P2 |
| Hierarchical agent graphs (5.2) | High | High | 🟢 P2 |
| Token budgeting system (6.1) | Medium | Low | 🟡 P1 |
| Multi-source RAG (5.3) | Very High | Very High | 🔵 P3 |

---

## 10. Quick Wins (Implement Today)

1. **Add per-agent model config** - Just env vars, already partially supported
2. **Parallelize independent agents** - `asyncio.gather()` 4 agents
3. **Compress agent output summaries** - Reduce final stage input by 40%
4. **Implement prompt fingerprinting** - Already have `prompt_registry.py`, just integrate
5. **Add token counting to audit log** - Visibility into spend

---

## 11. Future Vision: Hexamind 2.0

```
┌────────────────────────────────────────────────────────────────────┐
│                         HEXAMIND 2.0                               │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │  Fine-Tuned │  │  Fine-Tuned │  │  Fine-Tuned │                │
│  │  Advocate   │  │   Skeptic   │  │ Synthesiser │  ... (LoRA)   │
│  │   LoRA      │  │    LoRA     │  │    LoRA     │                │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                │
│         │                │                │                        │
│         └────────┬───────┴────────┬───────┘                        │
│                  ▼                                                 │
│         ┌─────────────────┐                                        │
│         │ Dynamic Router  │◄── Query Complexity Scorer            │
│         │ (Model Selector)│◄── Cost Budget Tracker                │
│         └────────┬────────┘◄── A/B Traffic Splitter               │
│                  │                                                 │
│         ┌────────┴────────┐                                        │
│         ▼                 ▼                                        │
│  ┌─────────────┐   ┌─────────────┐                                │
│  │ Cheap/Fast  │   │  Premium    │                                │
│  │  Provider   │   │  Provider   │                                │
│  │   (Groq)    │   │  (Gemini)   │                                │
│  └─────────────┘   └─────────────┘                                │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Shared Services                          │  │
│  │  • Semantic Cache (Redis + Embeddings)                      │  │
│  │  • Token Budget Tracker (per-tenant)                        │  │
│  │  • Prompt Version Registry                                  │  │
│  │  • Quality Gate Validator                                   │  │
│  │  • Usage Analytics Dashboard                                │  │
│  └─────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

---

*Document generated: 2026-04-03*
*Based on analysis of: ai-service/, src/lib/, config/*
