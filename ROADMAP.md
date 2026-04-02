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

## Export and Download Features

### Phase 1: Document Export

1. Add backend export endpoint for DOCX report generation from markdown synthesis.
2. Add backend export endpoint for PPTX deck generation using report sections as slides.
3. Add frontend download actions in output panel for DOCX and PPTX.
4. Include report metadata in exported files: query, timestamp, source inventory, confidence statement.

### Phase 2: Audio Export

1. Add text-to-speech export endpoint to convert synthesis report into narration audio.
2. Support mp3 and wav output targets.
3. Add voice profile selector and narration speed controls.
4. Add frontend audio preview and download button.

### Phase 3: Packaging and Shareability

1. One-click export bundle: zip containing markdown, docx, pptx, and audio.
2. Add export history for recent sessions.
3. Add signed download links for deployed mode.

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
