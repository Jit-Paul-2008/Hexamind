# Free API Setup And Smoke Test

## Goal

Connect free-tier APIs, run 2 research tasks, and verify that quality outputs are usable for grad and professor-level workflows.

## Step 1: Backend Env

Set these in `.env`:

```bash
HEXAMIND_MODEL_PROVIDER=gemini
HEXAMIND_MODEL_NAME=gemini-2.0-flash
GOOGLE_API_KEY=your_google_ai_studio_free_key

HEXAMIND_COST_MODE=free
HEXAMIND_TOKEN_MODE=smart
HEXAMIND_WEB_RESEARCH=1
HEXAMIND_AUTO_REGENERATE_ON_FAIL=1
HEXAMIND_RESEARCH_AUDIENCE=auto

HEXAMIND_RESEARCH_MAX_SOURCES=10
HEXAMIND_MAX_SOURCES_PER_DOMAIN=2
HEXAMIND_RESEARCH_MAX_TERMS=10
HEXAMIND_RESEARCH_MAX_HITS_PER_TERM=8
HEXAMIND_RESEARCH_FETCH_CONCURRENCY=5
HEXAMIND_RESEARCH_MIN_RELEVANCE=0.24
```

Optional lower-cost mode:

```bash
HEXAMIND_TOKEN_MODE=lean
HEXAMIND_RESEARCH_MAX_SOURCES=8
HEXAMIND_RESEARCH_MAX_TERMS=8
```

## Step 2: Frontend Env

Set these in `.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Step 3: Run Stack

Backend:

```bash
python3 -m uvicorn main:app --app-dir ai-service --host 127.0.0.1 --port 8000
```

Frontend:

```bash
npm run dev
```

## Step 4: Run Two Validation Queries

Query A (grad-compatible applied topic):

```text
What are the most effective interventions to reduce student dropout in first-year engineering programs?
```

Query B (professor-level unknown/complex topic):

```text
Evaluate whether retrieval-augmented multi-agent research systems can outperform single-model systems on novel interdisciplinary policy questions under evidence uncertainty.
```

## Step 5: Pass Criteria

For each query, check quality panel and report body:

1. `overallScore >= 70`
2. `citationCount >= 4` when sources exist
3. `uniqueDomains >= 3` when enough sources exist
4. claim verification rate at least `0.5`
5. contradiction handling appears in report when conflicts exist

## Step 6: Cost/Quality Tuning

If too expensive:

1. Switch `HEXAMIND_TOKEN_MODE=lean`
2. Reduce `HEXAMIND_RESEARCH_MAX_TERMS` by 2
3. Reduce `HEXAMIND_RESEARCH_MAX_HITS_PER_TERM` by 1
4. Keep `HEXAMIND_RESEARCH_AUDIENCE=auto` to preserve adaptive rigor

If quality drops too much:

1. Switch `HEXAMIND_TOKEN_MODE=smart` (or `max-quality`)
2. Restore `HEXAMIND_RESEARCH_MAX_SOURCES=10`
3. Keep auto-regeneration enabled
