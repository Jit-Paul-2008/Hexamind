# API-FIRST EXECUTION CHECKLIST

**Phase**: 3.5 API Optimization
**Duration**: 4 weeks
**Cost**: $0
**Goal**: Maximize API capabilities BEFORE database work

---

## IMMEDIATE ACTIONS (Today - April 4, 2026)

### ✅ DONE - State Saved
- [x] Created DEVELOPMENT_STATE_CHECKPOINT.md (complete system state)
- [x] Created FREE_API_INTEGRATION_GUIDE.md (all free APIs with code)
- [x] Created API_INTEGRATION_ROADMAP.md (4-week execution plan)

### ⏳ NEXT - Start Week 1 Implementation

---

## WEEK 1: Research API Foundation

### A1: Add DuckDuckGo (4 hours)
- [ ] Open `ai-service/research.py`
- [ ] Add `search_duckduckgo()` function (from FREE_API_INTEGRATION_GUIDE.md)
- [ ] Modify `build_research_context()` to use DuckDuckGo
- [ ] Test: `python3 -c "import asyncio; from ai_service.research import search_duckduckgo; asyncio.run(search_duckduckgo('AI trends'))"`
- [ ] Expected: 5 web results in <2 seconds
- [ ] Commit: `git commit -m "feat: add DuckDuckGo web search (no key)"`

### A2: Add Wikipedia (3 hours)
- [ ] Add `search_wikipedia()` function (from guide)
- [ ] Combine with DuckDuckGo in `build_research_context()`
- [ ] Test: Verify Wikipedia results return credibility 0.85
- [ ] Commit: `git commit -m "feat: add Wikipedia structured data"`

### A1-A2 Testing (1 hour)
- [ ] Run backend: `npm run dev:backend`
- [ ] Test in browser: Submit a research prompt
- [ ] Verify research sources appear in output
- [ ] Check that both DuckDuckGo and Wikipedia results show

**Week 1 Success Criteria**:
- [ ] DuckDuckGo + Wikipedia returning results
- [ ] Combined research context working
- [ ] Backend health check: 200 OK
- [ ] Git commits made

---

## WEEK 2: Model Diversity

### B1: Expand Ollama Models (2 hours)
- [ ] Run in terminal:
  ```bash
  ollama pull mistral           # Fast reasoning
  ollama pull neural-chat       # Dialogue
  ollama pull dolphin-mixtral   # Complex analysis
  ollama pull orca-mini         # Lightweight
  ```
- [ ] Verify: `ollama list`
- [ ] Add agent-model mapping in `ai-service/agents.py`
- [ ] Test: Each agent uses appropriate model

### B2: Add Hugging Face Fallback (3 hours)
- [ ] Sign up: https://huggingface.co/settings/tokens
- [ ] Create token (free)
- [ ] Add to `.env`: `HUGGINGFACE_API_KEY=hf_***`
- [ ] Add HuggingFaceProvider class to `ai-service/model_provider.py`
- [ ] Implement model fallback chain: Ollama → HF → OpenRouter
- [ ] Test: Force Ollama to fail, verify HF takes over

### B1-B2 Testing (1 hour)
- [ ] Rebuild Docker: `sudo docker compose up -d --build`
- [ ] Test Ollama models work: Run a full pipeline
- [ ] Verify fallback: Kill Ollama, test HF works
- [ ] Restart Ollama

**Week 2 Success Criteria**:
- [ ] Ollama has 4+ models installed
- [ ] Hugging Face provider working
- [ ] Model fallback chain tested
- [ ] No single-point-of-failure for AI

---

## WEEK 3: Testing & Documentation

### C1: Integration Tests (3 hours)
- [ ] Create `ai-service/tests/test_research_apis.py`
- [ ] Add test: `test_duckduckgo_search()`
- [ ] Add test: `test_wikipedia_search()`
- [ ] Add test: `test_combined_research()`
- [ ] Run: `npm run test:backend`
- [ ] Verify: All tests pass

### C2: E2E Pipeline Test (2 hours)
- [ ] Create `tests/e2e/free_api_sources.test.mjs`
- [ ] Test full pipeline with research
- [ ] Verify sources come from free APIs
- [ ] Run: `npm run test:e2e tests/e2e/free_api_sources.test.mjs`

### C3: Documentation (1 hour)
- [ ] Update README.md with "API Sources" section
- [ ] Document how to add Perplexity (optional)
- [ ] Document how to add OpenRouter (optional)
- [ ] Create API_SOURCES.md in docs/

**Week 3 Success Criteria**:
- [ ] All tests passing
- [ ] 100% API code coverage
- [ ] Documentation complete
- [ ] README updated

---

## WEEK 4: User Outreach

### Launch & Feedback (5 days)
- [ ] Create announcement: "ARIA AI Research Platform - Free & Open"
- [ ] Post on: HN, Reddit, Indie Hackers, Twitter
- [ ] Share link: http://localhost:3000 (or production URL)
- [ ] Gather feedback via email/form
- [ ] Track: Which research APIs users value most

**Week 4 Goals**:
- [ ] 5+ users testing
- [ ] Collect feedback on:
  - Research quality (DuckDuckGo vs Wikipedia priority)
  - Model response quality
  - Missing features
  - API reliability

---

## OPTIONAL ENHANCEMENTS (Post Week 4)

### A3: Wikidata Fact-Checking (2 hours)
- [ ] Add `search_wikidata()` to research.py
- [ ] Use for claim verification
- [ ] Mark claims as: verified/contested/unverified
- [ ] **When**: After Week 4 feedback

### B3: Perplexity API (2 hours)
- [ ] Sign up: https://www.perplexity.ai/api
- [ ] Add to .env: `PERPLEXITY_API_KEY=***`
- [ ] Use for high-quality synthesis
- [ ] **When**: If feedback indicates need

### OpenRouter Fallback (2 hours)
- [ ] Add 3rd-tier fallback if HF also overloaded
- [ ] **When**: User testing shows scalability issues

---

## DO NOT DO (Critical — Don't Deviate)

❌ Add database persistence layer
❌ Create migration scripts
❌ Build data models
❌ Setup auth database tables
❌ Implement Stripe payments
❌ Add user accounts system
❌ Create onboarding flows
❌ Add email verification
❌ Scale to production servers

**Reason**: API optimization + user feedback FIRST.
Then (Week 5+): Database and persistence.

---

## DAILY WORKFLOW (During Weeks 1-2)

**Morning (9am-12pm)**:
- Code implementation (4 hours chunks)
- Follow code examples from FREE_API_INTEGRATION_GUIDE.md
- Test as you go

**Afternoon (1pm-4pm)**:
- Testing
- Debug issues
- Commit progress

**Evening (4pm-6pm)**:
- Documentation
- Update progress in memory
- Plan next day

---

## GIT WORKFLOW

```bash
# Main feature branch
git checkout -b feat/free-api-research-integration

# Make changes in chunks
git add ai-service/research.py
git commit -m "feat: add DuckDuckGo API (no key required)"

git add ai-service/research.py
git commit -m "feat: add Wikipedia structured data"

git add ai-service/model_provider.py
git commit -m "feat: add Hugging Face fallback provider"

# More commits for Ollama expansion, tests, etc.

# Create PR for review
git push origin feat/free-api-research-integration

# After approval
git checkout main
git merge feat/free-api-research-integration
git push origin main
```

---

## SUCCESS MILESTONES

### Week 1 ✅
- [ ] DuckDuckGo + Wikipedia APIs working
- [ ] Research context includes free API sources
- [ ] Backend tests passing

### Week 2 ✅
- [ ] Ollama models installed + working
- [ ] Hugging Face provider fallback tested
- [ ] Model diversity working in pipeline

### Week 3 ✅
- [ ] Integration tests passing
- [ ] E2E pipeline tests passing
- [ ] Documentation complete

### Week 4 ✅
- [ ] 5+ users using system
- [ ] Feedback collected
- [ ] Priority list for next phase

**By May 1**: Phase 3.5 complete, ready for Phase 4 (Database)

---

## RESOURCE LINKS

**Documentation Files** (in workspace):
- DEVELOPMENT_STATE_CHECKPOINT.md — Complete system state
- FREE_API_INTEGRATION_GUIDE.md — All API specs + code examples
- API_INTEGRATION_ROADMAP.md — 4-week detailed plan

**External Resources**:
- DuckDuckGo API: https://duckduckgo.com/api (no docs, just HTTP GET)
- Wikipedia API: https://en.wikipedia.org/w/api.php
- Wikidata API: https://www.wikidata.org/wiki/Wikidata:Data_access
- Hugging Face: https://huggingface.co/docs/hub/inference-api
- Perplexity: https://www.perplexity.ai/api
- Ollama: https://ollama.ai/

**Commands to Keep Handy**:
```bash
# Backend
npm run dev:backend

# Tests
npm run test:backend
npm run test:e2e

# Docker
sudo docker compose up -d --build
sudo docker compose logs --tail=100 backend

# Ollama
ollama list
ollama pull <model>
curl http://localhost:11434/api/tags
```

---

## TRACKING PROGRESS

**Current Status**: ✅ Phase 2.75 Complete
**Target Status**: ✅ Phase 3.5 Complete (by May 1)
**Next Phase**: Phase 4 Database (starts May 2)

**Save this file** and follow it day by day.
Update progress daily in `/memories/session/` for continuity.

---

**Remember**: API-first. Users first. Database later. Trust the roadmap.

