# EXACTLY WHAT FREE API(S) TO USE WHERE — Complete Reference

**Document**: API Assignment Matrix  
**Purpose**: Answer "which API goes where" for architects/implementers
**Updated**: April 4, 2026

---

## SYSTEM ARCHITECTURE MAP

```
┌─────────────────────────────────────────────────────────┐
│                   ARIA FRONTEND (React)                  │
│              http://localhost:3000                        │
└──────────────────┬──────────────────────────────────────┘
                   │ HTTPS (internal)
                   ↓
┌─────────────────────────────────────────────────────────┐
│                   ARIA BACKEND (FastAPI)                 │
│              http://localhost:8000                        │
│                                                           │
│  Core Routes:                           External APIs:
│  • /api/pipeline/start                  • DuckDuckGo
│  • /api/pipeline/{id}/stream            • Wikipedia API
│  • /api/pipeline/{id}/quality           • Ollama (local)
│  • /api/auth/*                          • Hugging Face API
│  • /api/cases/*                         • Wikidata API
│  • /api/projects/*                      • Perplexity (optional)
│                                         • OpenRouter (optional)
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┼──────────┬──────────┐
        ↓          ↓          ↓          ↓
    [DuckDuckGo] [Wikipedia] [Ollama]  [HF Inference]
    [Wikidata]   [Perplexity] [Local DB] [OpenRouter]
```

---

## THE COMPLETE API MATRIX

### LAYER 1: Research & Knowledge Retrieval

| Stage | API | Role | Cost | Setup | Priority |
|-------|-----|------|------|-------|----------|
| **Primary Research** | DuckDuckGo | Web search results | $0 | None | 1️⃣ NOW |
| | URL | `https://api.duckduckgo.com/` | | |
| | Key? | No | | |
| | Speed | <2 sec | | |
| | Credibility | 0.6 | | |
| **Structured Facts** | Wikipedia | High-authority encyclopedic | $0 | None | 1️⃣ NOW |
| | URL | `https://en.wikipedia.org/w/api.php` | | |
| | Key? | No | | |
| | Speed | <2 sec | | |
| | Credibility | 0.85 | | |
| **Entity Relationships** | Wikidata | Structured claims, relationships | $0 | None | 2️⃣ WEEK 2 |
| | URL | `https://www.wikidata.org/w/api.php` | | |
| | Key? | No | | |
| | Speed | <1 sec | | |
| | Credibility | 0.75 | | |
| **High-Quality Synthesis** | Perplexity API | AI-powered web search → answer | $0/month | Signup | 3️⃣ OPTIONAL |
| | URL | `https://api.perplexity.ai/chat/completions` | | (free tier) |
| | Key? | Yes (free) | | |
| | Speed | 5-10 sec | | |
| | Credibility | 0.8 | | |

**Code Location**: `ai-service/research.py`
**Implementation**: See FREE_API_INTEGRATION_GUIDE.md § 1

---

### LAYER 2: LLM / AI Model Generation

| Stage | Provider | Model | Cost | Setup | Priority |
|-------|----------|-------|------|-------|----------|
| **Agent Text Generation** | Ollama (local) | mistral, dolphin, etc. | $0 | Download | 1️⃣ NOW |
| | Type | Local, ~7-12B params | | |
| | Speed | 2-5 sec/response | | |
| | Fallback Chain | Primary | | |
| **Fallback #1** | Hugging Face API | Mistral-7B, Llama-2, etc. | $0/month | Free key | 1️⃣ NOW |
| | URL | `https://api-inference.huggingface.co/models/` | | |
| | Quota | 100k requests/month | | |
| | Speed | 3-8 sec/response | | |
| | Fallback Chain | Secondary | | |
| **Fallback #2** | OpenRouter | gpt-3.5, mistral, etc. | $0/month | Free signup | 2️⃣ OPTIONAL |
| | URL | `https://openrouter.ai/api/v1/chat/completions` | | + $5 credits |
| | Model Quality | Diverse (many models) | | |
| | Speed | 3-10 sec/response | | |
| | Fallback Chain | Tertiary | | |
| **Embeddings** | Sentence Transformers | all-MiniLM-L6-v2 | $0 | Local pip | 1️⃣ NOW |
| | Type | Local semantic search | | |
| | Speed | <100ms | | |

**Code Location**: `ai-service/model_provider.py`, `agents.py`
**Implementation**: See FREE_API_INTEGRATION_GUIDE.md § 2

---

### LAYER 3: Data Persistence (Use When Needed, Not Now)

| Component | Technology | Cost | Status | Phase |
|-----------|-----------|------|--------|-------|
| Development DB | SQLite | $0 | ✅ Ready | Phase 3 |
| Production DB | PostgreSQL | $0* | ✅ Configured | Phase 3+ |
| Knowledge Cache | In-memory | $0 | ✅ Active | Phase 2 |
| Document Storage | Local filesystem | $0 | ✅ Ready | Phase 2 |
| Cloud Storage | Supabase (free tier) | $0/month | ⏳ Later | Phase 4 |
| Cloud Storage | Firebase (free tier) | $0/month | ⏳ Later | Phase 4 |

*PostgreSQL is free open-source; hosting cost separate
**Code Location**: `ai-service/database/connection.py`
**Status**: NOT NEEDED YET — Skip this for now

---

### LAYER 4: Authentication & Secrets (Already Configured)

| Component | Technology | Cost | Status |
|-----------|-----------|------|--------|
| JWT Secret | Auto-generated (openssl) | $0 | ✅ Done |
| Password Hashing | bcrypt | $0 | ✅ Active |
| Session Management | In-memory + JWT | $0 | ✅ Working |
| CORS & Rate Limiting | FastAPI middleware | $0 | ✅ Active |

**Code Location**: `ai-service/main.py`, middleware
**Implementation**: COMPLETE — No changes needed

---

### LAYER 5: Monitoring & Observability (Use Later)

| Component | Technology | Cost | Status | Phase |
|-----------|-----------|------|--------|-------|
| Metrics Collection | Prometheus | $0 | ✅ Configured | Phase 5 |
| Metrics Visualization | Grafana | $0 | ✅ Configured | Phase 5 |
| Cloud Metrics | Grafana Cloud (free tier) | $0/month | ⏳ Later | Phase 5 |
| Error Tracking | Sentry (free tier) | $0/month | ⏳ Future | Phase 5 |
| Log Aggregation | ELK/Loki | $0 | ⏳ Future | Phase 5 |

**Status**: NOT NEEDED NOW — Skip for MVP

---

## THE GOLDEN PRIORITY LIST

**Follow this order ONLY. Don't skip ahead.**

### Phase 3.5 Week 1 (IMMEDIATE)

```
Priority 1: DuckDuckGo + Wikipedia
├─ Cost: $0
├─ Setup: 5 minutes
├─ Impact: 80% research quality boost
├─ Code file: ai-service/research.py
└─ Checklist:
   ✓ Add async function search_duckduckgo()
   ✓ Add async function search_wikipedia()
   ✓ Wire into build_research_context()
   ✓ Test: Full pipeline returns results
   ✓ Commit: "feat: add free research APIs"
```

---

### Phase 3.5 Week 2 (SECOND)

```
Priority 2: Ollama Model Diversity
├─ Cost: $0
├─ Setup: 20 minutes (+ download time)
├─ Impact: Better agent specialization
├─ Code file: ai-service/agents.py, model_provider.py
└─ Checklist:
   ✓ ollama pull mistral
   ✓ ollama pull dolphin-mixtral
   ✓ ollama pull neural-chat
   ✓ Map agents to best model
   ✓ Test: Each agent uses its model
   ✓ Commit: "feat: expand Ollama model diversity"

Priority 3: Hugging Face Fallback
├─ Cost: $0 (free tier)
├─ Setup: 15 minutes (signup)
├─ Impact: Never fail due to Ollama overload
├─ Code file: ai-service/model_provider.py
└─ Checklist:
   ✓ Sign up: https://huggingface.co/settings/tokens
   ✓ Create free token
   ✓ Add to .env: HUGGINGFACE_API_KEY=hf_***
   ✓ Add HuggingFaceProvider class
   ✓ Wire fallback chain
   ✓ Test: Force Ollama down, verify HF works
   ✓ Commit: "feat: add Hugging Face fallback provider"
```

---

### Phase 3.5 Week 3 (THIRD)

```
Priority 4: Comprehensive Testing
├─ Cost: $0
├─ Setup: 5 minutes
├─ Impact: Confidence in API reliability
├─ Code file: ai-service/tests/test_research_apis.py
└─ Checklist:
   ✓ Write test_duckduckgo_search()
   ✓ Write test_wikipedia_search()
   ✓ Write test_model_fallback()
   ✓ Run: npm run test:backend
   ✓ All tests pass
   ✓ Commit: "test: add comprehensive API tests"

Priority 5: Documentation
├─ Cost: $0
├─ Setup: 10 minutes
├─ Impact: User understanding
└─ Checklist:
   ✓ Update README with "Research Sources" section
   ✓ Document API sources + credibility
   ✓ Explain fallback chain
   ✓ Create API_SOURCES.md in docs/
```

---

### Phase 3.5 Week 4 (FOURTH)

```
Priority 6: User Feedback
├─ Cost: $0
├─ Setup: 1 hour
├─ Impact: Real validation
└─ Actions:
   ✓ Post on Hacker News, Reddit, Twitter
   ✓ Collect 5+ user feedback
   ✓ Rate: Which APIs matter most?
   ✓ Plan Phase 4 based on feedback

AFTER THIS: Phase 4 (Database) begins
```

---

## API DECISION TREE: How to Pick the Right API

### "I need to search the web"
→ **DuckDuckGo** (fast, no key, primary)
→ Fallback: **Wikipedia** (high authority)
→ Optional: **Perplexity** (AI synthesis, needs key)

### "I need facts about entities"
→ **Wikipedia** (primary, 0.85 credibility)
→ **Wikidata** (structured relationships)
→ Optional: **Perplexity** (synthesis)

### "I need to generate agent response"
→ **Ollama** (fast, local, primary)
→ **Hugging Face** (fallback #1, free API)
→ **OpenRouter** (fallback #2, diverse models)

### "I need semantic search / embeddings"
→ **Sentence Transformers** (local, fast)
→ Optional: **Hugging Face Inference** (backup)

### "I need to store data long-term"
→ **NOT NOW** — Use in-memory for MVP
→ Phase 4: **PostgreSQL** (local) or **Supabase** (free cloud)

### "I need to monitor performance"
→ **Prometheus + Grafana** (local, free)
→ Phase 5: **Grafana Cloud** (free tier, 10k metrics)

---

## COSTS ACROSS PHASES

### Phase 3.5 (API Optimization) — NOW
```
DuckDuckGo API:        $0/month (unlimited)
Wikipedia API:         $0/month (unlimited)
Ollama (local):        $0/month (self-hosted)
Sentence Transformers: $0/month (local)
Total:                 $0/month ✅
```

### Phase 4 (Database) — IF NEEDED
```
PostgreSQL:            $0/month (self-hosted) or $15+/mo (managed)
SQLite:                $0/month (local)
Supabase (free tier):  $0/month (500MB storage)
Total:                 $0-15/month
```

### Phase 5 (Monitoring) — IF SCALING
```
Prometheus + Grafana:  $0/month (local)
Grafana Cloud:         $0/month (free tier, 10k metrics)
Total:                 $0/month
```

**Bottom Line**: Entire MVP stays at **$0/month** through Phase 4.

---

## ENVIRONMENT VARIABLES NEEDED

### Right Now (Phase 3.5)
```bash
# .env file

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Backend
API_HOST=0.0.0.0
API_PORT=8000
DATABASE_URL=sqlite+aiosqlite:///./aria.db

# JWT
JWT_SECRET_KEY=***auto-generated***

# AI Models - Already configured
OLLAMA_BASE_URL=http://localhost:11434

# Optional (add when signing up)
HUGGINGFACE_API_KEY=hf_***
PERPLEXITY_API_KEY=***
OPENROUTER_API_KEY=sk-or-***
```

---

## FINAL QUICK REFERENCE

**What to implement THIS WEEK**:
1. Add DuckDuckGo API ✅
2. Add Wikipedia API ✅
3. Expand Ollama models ✅
4. Add Hugging Face provider ✅
5. Write tests ✅

**What NOT to touch**:
- ❌ Database schema
- ❌ Stripe/payments
- ❌ User accounts
- ❌ Email verification
- ❌ Production scaling

**Files to modify**:
- `ai-service/research.py` — Add DuckDuckGo + Wikipedia
- `ai-service/model_provider.py` — Add HF fallback
- `ai-service/agents.py` — Map agents to models
- `ai-service/tests/` — Add integration tests
- `.env` — Add optional keys (HF, Perplexity)

**By May 1, 2026**:
- [ ] All Phase 3.5 APIs implemented
- [ ] 5+ users testing system
- [ ] Feedback gathered
- [ ] Ready for Phase 4 (Database)

---

**This is your north star. Follow it exactly. Reference this daily.**

