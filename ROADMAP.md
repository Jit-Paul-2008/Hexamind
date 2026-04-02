# Hexamind Delivery Roadmap

## Current State (Implemented)

1. Full backend pipeline is live with FastAPI endpoints for health, agent metadata, session start, and SSE streaming.
2. Frontend is wired to real backend events and no longer depends on timer-based mock orchestration.
3. Model provider diagnostics are exposed in health and surfaced in UI status indicators.
4. Canvas supports draggable agent windows and draggable processing windows with overlap avoidance.
5. Synthesis output panel is expanded to an A4-like report canvas for long-form output readability.
6. Internet research retrieval layer is integrated into backend generation flow with source inventory output.
7. Structured research report generation is implemented with sectioned markdown output and role-specific agent templates.
8. Build, lint, backend tests, and e2e contract tests are passing.

## Priority Next Steps (Tomorrow)

1. Strengthen evidence quality scoring.
2. Add source credibility ranking per citation domain and expose score in report.
3. Add citation-to-claim mapping so each key claim can be traced to source ids.
4. Add report mode selector: quick brief, technical report, thesis report.
5. Add post-generation quality gate to reject shallow outputs and trigger regeneration.

## Export and Download Features (Paused)

1. DOCX, PPTX, PDF, and Audio exports are intentionally paused until research-grade output quality is consistently met.
2. Export work resumes only after citation density, contradiction handling, and confidence calibration pass acceptance targets.

## ARIA Deep-Research Acceleration (Active)

### Phase 1: Agent-Specialized Model Routing

1. Route each agent to best-fit model/API via environment-configured map.
2. Keep deterministic fallback for reliability, but require research gates for production mode.
3. Track per-agent latency and fallback rates in diagnostics.

### Phase 2: Grounding and Evidence Integrity

1. Enforce minimum citations per section and per final report.
2. Add contradiction detector across source excerpts and present disputes explicitly.
3. Add source diversity requirement so final claims do not depend on a single domain.

### Phase 3: Research-Quality UX

1. Add evidence quality panel in output view (authority mix, citation count, contradiction count).
2. Show citation tags inline for major claims.
3. Add transparent regeneration reason when quality gates reject a draft.

## Research-Model Hardening

1. Add specialized retrieval connectors for official docs and academic sources.
2. Add optional File Search lane for private datasets.
3. Add optional Code Execution lane for numerical verification.
4. Add contradiction detection across sources and explicit uncertainty reporting.
5. Add prompt-injection filters for external web content.

## Deployment and Reliability

1. Add request-level tracing from frontend query id to backend session id.
2. Add rate limiting and auth guardrails for public deployment.
3. Add caching for repeated queries and source packs.
4. Add background job queue for long-running deep research workflows.
5. Add monitoring dashboards for latency, fallback rate, and source coverage.
