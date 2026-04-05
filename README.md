# Hexamind

Hexamind is a minimal full-stack multi-agent reasoning demo.

- Frontend: Next.js app router UI with a 4-agent canvas and live status widgets
- Backend: FastAPI service with pipeline session start + SSE event streaming

## Architecture

- `src/`: frontend app and UI state/store
- `ai-service/`: Python API service (`FastAPI` + `sse-starlette`)

The UI is a single full-window experience at `/` with the existing 4 agents:

1. Advocate
2. Skeptic
3. Synthesiser
4. Oracle

## API

- `GET /health` -> service health
- `GET /api/agents` -> agent metadata
- `POST /api/pipeline/start` -> create pipeline session
- `GET /api/pipeline/{sessionId}/stream` -> SSE events (`agent_start`, `agent_chunk`, `agent_done`, `pipeline_done`)
- `GET /api/pipeline/{sessionId}/quality` -> structured quality diagnostics + trust metrics
- `GET /api/models/status` -> cloud provider and pipeline readiness
- `GET /api/benchmark/competitive` -> latest consolidated ARIA/Gemini/GPT batch summary
- `POST /api/pipeline/{sessionId}/sarvam-transform` -> optional language/instruction transform of final report
- `POST /api/pipeline/{sessionId}/export-docx` -> optional DOCX export of transformed final report

## Additional Notable Project Capabilities

These are implemented in the repo but easy to miss if you only skim the quick-start:

- Request-level security middleware with optional auth token gating for sensitive pipeline routes.
- Built-in per-IP rate limiting via `HEXAMIND_RATE_LIMIT_PER_MINUTE`.
- JSONL audit logging for API traffic in `ai-service/.data/audit-log.jsonl`.
- Pipeline queue/backpressure controls (`HEXAMIND_STREAM_MAX_CONCURRENT`, queue wait timeout).
- Stage-level timeout budgets for retrieval, per-agent generation, and final synthesis.
- Automatic regenerate-on-quality-fail flow and deterministic failsafe fallback path.
- Run metadata emitted with quality reports (timings, trace coverage, provider diagnostics, report digest).
- Retrieval cache with TTL and automatic fallback source expansion when web sources are sparse.
- Prompt/version fingerprint snapshot support for reproducibility.
- Benchmark harness (`ai-service/benchmarking.py`) with win-rate and regression-oriented scoring helpers.
- Sarvam integration includes safe fallback behavior even when `SARVAM_API_KEY` is absent.

## Reliability and Security Environment Knobs

Useful production/runtime controls not listed elsewhere in this README:

```bash
# Security / traffic control
HEXAMIND_AUTH_TOKEN=your_token
HEXAMIND_RATE_LIMIT_PER_MINUTE=60

# Streaming concurrency + queueing
HEXAMIND_STREAM_MAX_CONCURRENT=2
HEXAMIND_STREAM_QUEUE_WAIT_SECONDS=15

# Stage timeouts
HEXAMIND_RETRIEVAL_TIMEOUT_SECONDS=18
HEXAMIND_AGENT_TIMEOUT_SECONDS=30
HEXAMIND_FINAL_TIMEOUT_SECONDS=40

# Provider health manager
HEXAMIND_PROVIDER_RETRY_BUDGET=1
HEXAMIND_PROVIDER_FAILURE_THRESHOLD=3
HEXAMIND_PROVIDER_COOLDOWN_SECONDS=30
HEXAMIND_PROVIDER_BACKOFF_SECONDS=0.25

# Research cache
HEXAMIND_RESEARCH_CACHE_TTL_SECONDS=1800

# Report safety behavior
HEXAMIND_AUTO_REGENERATE_ON_FAIL=1
HEXAMIND_NEVER_FAIL_REPORT=1
## Cloud Deployment

Hexamind is now cloud-only for public use. For the live deployment path, use:

- [PUBLIC_DEMO_ROLLOUT.md](PUBLIC_DEMO_ROLLOUT.md)
- [render.yaml](render.yaml)

Required public deployment values:

- `NEXT_PUBLIC_API_BASE_URL` must point to your backend public URL at build time.
- `HEXAMIND_CORS_ORIGINS` must include your frontend domain.
- `OPENROUTER_API_KEY` and `TAVILY_API_KEY` must be configured in your hosting platform.

For production verification, run the smoke tests in [PUBLIC_DEMO_ROLLOUT.md](PUBLIC_DEMO_ROLLOUT.md).
HEXAMIND_RESEARCH_FETCH_CONCURRENCY=5
HEXAMIND_RESEARCH_MIN_RELEVANCE=0.24
HEXAMIND_RESEARCH_AUDIENCE=auto
HEXAMIND_TOKEN_MODE=smart
```

Workflow design reference:

- `src/docs/aria-free-power-workflow.md`
- `src/docs/free-api-setup-and-smoke-test.md`
- `PUBLIC_DEMO_ROLLOUT.md` (cloud-only public demo deployment)

Quality API for each completed session:

- `GET /api/pipeline/{sessionId}/quality`

## Public Link Deployment (No Local Runtime)

If you want users on any device to use one public link, deploy with cloud APIs only:

1. Deploy backend to Render using `render.yaml`.
2. Add backend secrets (`OPENROUTER_API_KEY`, `TAVILY_API_KEY`) in Render.
3. Deploy frontend to Vercel.
4. In Vercel, set `NEXT_PUBLIC_API_BASE_URL=https://<your-render-api-domain>`.
5. In backend env, set `HEXAMIND_CORS_ORIGINS=https://<your-vercel-domain>`.

Cloud-only profile avoids local model dependencies and serves live API-backed research/report generation to public users.

## Quality Checks

```bash
npm run lint
npm run build
```

## Deployment

Hexamind is deployed as a cloud-only app. Use the public deployment guide and platform
secret stores rather than local Docker or localhost endpoints:

- [PUBLIC_DEMO_ROLLOUT.md](PUBLIC_DEMO_ROLLOUT.md)
- [render.yaml](render.yaml)
- Vercel production env: `NEXT_PUBLIC_API_BASE_URL=<your backend public URL>`

The backend and frontend should be deployed separately as public services.
