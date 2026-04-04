# ARIA API-FIRST PHASE — START HERE

**Your mission**: Maximize API capabilities before touching database

**Read in this order**:
1. This file (5 min overview)
2. API_ASSIGNMENT_MATRIX.md (5 min decision reference)
3. API_INTEGRATION_ROADMAP.md (detailed week-by-week plan)
4. FREE_API_INTEGRATION_GUIDE.md (code examples)
5. API_EXECUTION_CHECKLIST.md (daily execution)

---

## THE BIG PICTURE (in 60 seconds)

**Current State** (April 4, 2026):
- ✅ UI/UX complete (practical dashboard)
- ✅ Auth complete (JWT + bcrypt)
- ✅ Backend running (FastAPI healthy)
- ✅ All containers running (Docker healthy)
- ❌ Research APIs incomplete (only Tavily, paid, optional)
- ❌ No database persistence yet

**Next 4 Weeks**:
1. **Week 1**: Add free research APIs (DuckDuckGo + Wikipedia) — 8 hours
2. **Week 2**: Add model diversity (Ollama + Hugging Face) — 6 hours
3. **Week 3**: Test & document — 6 hours
4. **Week 4**: Seek users + gather feedback — 5 hours

**Total Implementation Time**: ~25 hours over 4 weeks
**Cost**: $0
**Impact**: 10x better research capabilities

---

## WHAT GETS IMPLEMENTED

### What You Add:
✅ DuckDuckGo Web Search (no key, unlimited)
✅ Wikipedia API (no key, unlimited)
✅ Ollama Model Diversity (mistral, dolphin, neural-chat)
✅ Hugging Face Fallback (free tier, 100k req/month)
✅ Wikidata (optional, structured facts)
✅ Perplexity (optional, AI synthesis)

### What Already Works:
✅ FastAPI backend
✅ React frontend
✅ Ollama (local LLM)
✅ JWT authentication
✅ Bcrypt passwords
✅ PostgreSQL (configured, not used yet)
✅ Error visibility
✅ Pipeline streaming

### What You SKIP (Until Phase 4):
❌ Database persistence
❌ Stripe/Payments
❌ User accounts
❌ Email verification
❌ Production deployment
❌ Data migrations

---

## WEEKLY FOCUS

### Week 1: "Research Foundation"
**Goal**: Make the system actually search the web well

**Monday-Tuesday**: DuckDuckGo API (4 hours)
```python
# In ai-service/research.py
async def search_duckduckgo(query: str) -> list[ResearchSource]:
    # Implementation from FREE_API_INTEGRATION_GUIDE.md
    # Returns 5 web search results in <2 seconds
```

**Wednesday**: Wikipedia API (3 hours)
```python
# In ai-service/research.py
async def search_wikipedia(query: str) -> list[ResearchSource]:
    # Implementation from guide
    # Returns 3 high-authority sources
```

**Thursday-Friday**: Test & integrate
```bash
npm run dev:backend
# Test in browser: http://localhost:3000
# Submit research prompt
# Verify DuckDuckGo + Wikipedia results appear
```

---

### Week 2: "Model Resilience"
**Goal**: Never fail due to single model bottleneck

**Monday**: Ollama expansion (2 hours)
```bash
ollama pull mistral           # Fast reasoning
ollama pull dolphin-mixtral   # Complex analysis
ollama pull neural-chat       # Best dialogue
ollama pull orca-mini         # Lightweight
```

**Tuesday-Wednesday**: Hugging Face provider (3 hours)
```python
# In ai-service/model_provider.py
class HuggingFaceProvider:
    async def generate(self, agent_id: str, prompt: str) -> str:
        # Fallback when Ollama busy
        # 100k free requests/month
```

**Thursday-Friday**: Test fallback chain
```bash
# Test Ollama → HF → OpenRouter chain
# Verify each layer works
```

---

### Week 3: "Quality & Documentation"
**Goal**: Prove everything works

**Monday-Tuesday**: Integration tests (3 hours)
```bash
# Create ai-service/tests/test_research_apis.py
npm run test:backend
# All tests pass ✓
```

**Wednesday-Friday**: Update docs, README
```bash
# Update: README.md with API architecture
# Create: API_SOURCES.md in docs/
# Update: .env.example with new keys
```

---

### Week 4: "User Validation"
**Goal**: Get real feedback before database work

**Monday**: Launch announcement
- Hacker News post
- Reddit r/MachineLearning
- Twitter/X
- Indie Hackers

**Tuesday-Friday**: Collect feedback
- What research sources matter?
- Which models work best?
- What features are missing?
- How reliable is it?

---

## PRIORITY DECISION MATRIX

**Do these in this exact order** (don't skip ahead):

```
┌─────────────────────────────────────┐
│ MANDATORY (Week 1) — Cannot Skip    │
├─────────────────────────────────────┤
│ 1. DuckDuckGo API (4 hrs)           │
│ 2. Wikipedia API (3 hrs)             │
│ 3. Ollama models (2 hrs)             │
│ 4. Hugging Face provider (3 hrs)     │
│ 5. Basic tests (4 hrs)               │
├─────────────────────────────────────┤
│ IMPORTANT (Week 2-3) — High Value  │
├─────────────────────────────────────┤
│ 6. Integration tests (3 hrs)         │
│ 7. Wikidata API (2 hrs)              │
│ 8. Documentation (2 hrs)             │
├─────────────────────────────────────┤
│ OPTIONAL (Week 3+) — Nice-to-have  │
├─────────────────────────────────────┤
│ 9. Perplexity API (2 hrs)            │
│ 10. OpenRouter fallback (2 hrs)      │
└─────────────────────────────────────┘

❌ DON'T TOUCH (These come in Phase 4):
   - Database persistence
   - Stripe integration
   - User signup/login
   - Email verification
   - Production scaling
```

---

## YOUR SPECIFIC TODO RIGHT NOW

**Pick one and start today**:

### Option A: 2-Hour Quick Win
```python
# ai-service/research.py
# Add DuckDuckGo API function
# Test it works
# Commit changes
```

### Option B: 3-Hour Setup
```python
# ai-service/model_provider.py
# Add Hugging Face provider
# Get free API key
# Wire fallback chain
```

### Option C: Full Week 1 (8 hours)
```
Monday: DuckDuckGo
Wednesday: Wikipedia
Friday: Test & integrate
```

**I recommend Option C** (full Week 1) to get maximum value fast.

---

## EXACT COMMANDS TO GET STARTED

### 1. Read the reference docs (25 minutes)
```bash
# In VS Code, open these in order:
# 1. API_ASSIGNMENT_MATRIX.md (5 min)
# 2. FREE_API_INTEGRATION_GUIDE.md (15 min)
# 3. API_INTEGRATION_ROADMAP.md (5 min)
```

### 2. Prepare your environment (5 minutes)
```bash
cd /home/Jit-Paul-2008/Desktop/Hexamind

# Start backend development server
npm run dev:backend

# In another terminal, verify it's running
curl http://localhost:8000/health
# Should return: {"status": "ok"}
```

### 3. Start implementing DuckDuckGo (4 hours)
```bash
# Open ai-service/research.py
# Copy the search_duckduckgo() function from FREE_API_INTEGRATION_GUIDE.md
# Paste it into research.py (after existing functions)
# Modify build_research_context() to use it (code in guide)
# Save

# Test in terminal
python3 << 'EOF'
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        r = await client.get('https://api.duckduckgo.com/',
            params={'q': 'machine learning 2025', 'format': 'json'})
        results = r.json()['Results']
        print(f"Found {len(results)} results")
        for i, r in enumerate(results[:3]):
            print(f"{i+1}. {r.get('Title', 'No title')}")

asyncio.run(test())
EOF
```

### 4. Test in the UI (10 minutes)
```bash
# Open browser: http://localhost:3000
# Paste a research prompt: "What are AI breakthroughs in 2025?"
# Submit
# Watch the pipeline execute
# Check: Are results appearing?
# Check: Do you see DuckDuckGo + Wikipedia sources?
```

### 5. Commit (2 minutes)
```bash
git add ai-service/research.py
git commit -m "feat: add DuckDuckGo web search API"
git push origin main
```

---

## DAILY WORKFLOW TEMPLATE

Use this every day during implementation:

### 9:00 AM - Plan (10 min)
- [ ] Open API_EXECUTION_CHECKLIST.md
- [ ] Pick today's task (e.g., "Add DuckDuckGo")
- [ ] Read the implementation section in FREE_API_INTEGRATION_GUIDE.md

### 9:15 AM - Code (4 hours)
- [ ] Open target file (e.g., ai-service/research.py)
- [ ] Copy implementation code from guide
- [ ] Paste and adapt to your needs
- [ ] Save

### 1:15 PM - Test (1 hour)
- [ ] Run backend: `npm run dev:backend` (if not running)
- [ ] Test in terminal or browser
- [ ] Debug any errors
- [ ] Verify it works

### 2:15 PM - Commit (15 min)
- [ ] `git add <files>`
- [ ] `git commit -m "feat: add [API name]"`
- [ ] `git push origin main`

### 2:30 PM - Document (30 min)
- [ ] Update API_EXECUTION_CHECKLIST.md with progress
- [ ] Update /memories/session/ with learnings
- [ ] Plan tomorrow's task

### 3:00 PM onwards - Optional
- [ ] Add tests
- [ ] Update README
- [ ] Optimize performance

---

## RESOURCE MAP

| Need | File | Section |
|------|------|---------|
| "Which API?" | API_ASSIGNMENT_MATRIX.md | API Decision Tree |
| "How implement?" | FREE_API_INTEGRATION_GUIDE.md | 1, 2, 3+ |
| "In what order?" | API_INTEGRATION_ROADMAP.md | Week-by-Week |
| "What's my task?" | API_EXECUTION_CHECKLIST.md | Today's section |
| "Show me code" | FREE_API_INTEGRATION_GUIDE.md | Code blocks |
| "Full system view?" | DEVELOPMENT_STATE_CHECKPOINT.md | All sections |

---

## SUCCESS SIGNALS

### By Friday (Week 1 end) ✅
- [ ] DuckDuckGo returning results in terminal
- [ ] Wikipedia working in browser tests
- [ ] Backend still running healthily
- [ ] Git history shows 2-3 commits

### By Friday (Week 2 end) ✅
- [ ] Ollama has 4 models installed
- [ ] Hugging Face API key added to .env
- [ ] Fallback chain tested
- [ ] 5+ git commits made

### By Friday (Week 3 end) ✅
- [ ] All tests passing
- [ ] README updated
- [ ] API documentation complete
- [ ] Ready for user feedback

### By Friday (Week 4 end) ✅
- [ ] 5+ users testing
- [ ] Feedback collected
- [ ] Phase 4 plan updated
- [ ] Database phase ready to start

---

## IF YOU GET STUCK

**Problem**: DuckDuckGo API returns error
→ Check URL format in FREE_API_INTEGRATION_GUIDE.md § 1.1
→ Test manually: `curl 'https://api.duckduckgo.com/?q=test&format=json'`

**Problem**: Hugging Face API quota exceeded
→ You're on free tier (100k requests/month) — that's plenty
→ Switch to Ollama (no quota) or wait 24 hours
→ Check: https://huggingface.co/settings/billing

**Problem**: Ollama isn't responding
→ Verify: `curl http://localhost:11434/api/tags`
→ If failed: `ollama serve` in a terminal
→ If models missing: `ollama pull mistral`

**Problem**: Tests failing
→ Run one test at a time
→ Check imports are correct
→ Verify all dependencies installed: `pip list | grep httpx`

**For all else**: Check TROUBLESHOOTING.md in workspace

---

## STAYING ON TRACK

**This is a 4-week plan. Don't deviate.**

What helps:
✅ Commit something every day
✅ Update memory daily
✅ Keep this checklist visible
✅ Test as you go
✅ Document as you code

What hurts:
❌ Trying to add database during this phase
❌ Building features not on the checklist
❌ Skipping tests
❌ Not committing regularly
❌ Getting distracted by Phase 5 things

---

## FINAL CHECKLIST

Before you start implementation:

- [ ] Read all 5 documents (1 hour)
- [ ] Backend running: `npm run dev:backend`
- [ ] Browser working: http://localhost:3000
- [ ] Git ready: `git status` = clean
- [ ] Editor open: VS Code with whole workspace visible
- [ ] Memory system ready: `/memories/session/` accessible
- [ ] Checklist ready: API_EXECUTION_CHECKLIST.md bookmarked

---

**You're ready. Start with DuckDuckGo. See you Friday with working research APIs.** 🚀

