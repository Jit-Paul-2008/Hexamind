# Public Demo Rollout (Cloud-Only)

This guide makes Hexamind publicly usable with a shareable link on any device.
No local model runtime is required for users.

## Target Architecture

- Frontend: Vercel (public web URL)
- Backend: Render `hexamind-api` (public API URL)
- Database: Render PostgreSQL (`hexamind-db`)
- LLM + Retrieval: OpenRouter + Tavily (API-only)

## 1. Backend Deploy (Render)

Use `render.yaml` from repo root.

Required secret env vars in Render service `hexamind-api`:

- `OPENROUTER_API_KEY`
- `TAVILY_API_KEY`
- Optional: `GOOGLE_API_KEY`, `GROQ_API_KEY`, `HUGGINGFACE_API_KEY`

Optional multi-key pools (comma-separated) for burst smoothing:

- `OPENROUTER_API_KEYS`
- `TAVILY_API_KEYS`
- `GOOGLE_API_KEYS`
- `GROQ_API_KEYS`

Cloud-only runtime envs already set in `render.yaml`:

- `HEXAMIND_MODEL_PROVIDER=openrouter`
- `HEXAMIND_STRICT_PROVIDER=1`
- `HEXAMIND_DISABLE_FAILSAFE_FALLBACK=1`
- `HEXAMIND_WEB_RESEARCH=1`
- `HEXAMIND_RESEARCH_PROVIDER=tavily`
- `HEXAMIND_REQUIRE_RESEARCH_SOURCES=1`
- `HEXAMIND_HARD_FAIL_ON_NO_SOURCES=0`
- `HEXAMIND_PARALLEL_AGENTS=1`

This ensures API-backed generation/research and prevents local deterministic fallback masking provider failures.

## 2. Frontend Deploy (Vercel)

Create Vercel project from this repo.

Set environment variable in Vercel (Production + Preview):

- `NEXT_PUBLIC_API_BASE_URL=https://<your-render-api-domain>`

Optional compatibility var:

- `NEXT_PUBLIC_API_URL=https://<your-render-api-domain>`

Then redeploy frontend so Next.js bakes the public API URL at build time.

## 3. CORS for Public Frontend

Backend reads CORS from:

- `HEXAMIND_CORS_ORIGINS`

Set it to your public frontend origins, comma-separated, for example:

- `https://hexamind.vercel.app,https://your-custom-domain.com`

If unset, backend falls back to `*`.

## 4. Smoke Tests (Post-Deploy)

Replace `<api>` and `<web>` with deployed domains.

```bash
curl https://<api>/health
curl https://<api>/api/agents
curl -X POST https://<api>/api/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"query":"How should small teams harden APIs in 2026?"}'
```

In browser:

- Open `https://<web>`
- Submit 3 random topics
- Confirm live agent streaming + final report + quality panel

## 5. Public Demo Guardrails

Recommended env values for stable demos:

- `HEXAMIND_RATE_LIMIT_PER_MINUTE=90`
- `HEXAMIND_STREAM_MAX_CONCURRENT=2`
- `HEXAMIND_STREAM_QUEUE_WAIT_SECONDS=20`
- `HEXAMIND_AGENT_TIMEOUT_SECONDS=35`
- `HEXAMIND_FINAL_TIMEOUT_SECONDS=45`

## 6. Go-Live Checklist

- Backend health endpoint returns `status: ok`
- Frontend points to public backend URL (not localhost)
- OpenRouter and Tavily keys are valid
- CORS includes public frontend domain
- At least 5 random-topic test runs complete end-to-end
- Competitive run validated with:

```bash
./.venv/bin/python scripts/run_competitive_research.py --global-baselines --limit 5
```

## 7. Known Caveat

Current repo still has two failing backend tests in milestone suites; runtime demo can still operate, but full production hardening should include fixing those tests before large-scale public traffic.
