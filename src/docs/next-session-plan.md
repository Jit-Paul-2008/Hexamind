# Next Session Plan

## Session Handoff Snapshot

- Backend and frontend are integrated with live SSE pipeline flow.
- Structured long-form synthesis is active in A4-like output mode.
- Internet retrieval is integrated and source inventory appears in final report.
- Draggable agent and processing windows are available with overlap handling.
- Build and test status was green at handoff time.

## Tomorrow Start Checklist

1. Run local stack and verify health payload includes webResearchEnabled true.
2. Run one live query and confirm source inventory contains real urls.
3. Validate that evidence snapshot lines contain substantive findings.
4. Pause export tracks (docx, pptx, audio) and lock focus on research quality.
5. Validate claim-to-citation density for each agent output and final synthesis.

## Planned Implementation Track

### Track A: Quality and Grounding

1. Add citation-to-claim linking in synthesis section bodies.
2. Add source credibility scoring and confidence calibration.
3. Add regeneration gate when citation count is below threshold.

### Track B: ARIA Deep-Research Upgrade (Primary Focus)

1. Agent-specialized model routing
- Route each role to best-fit models via configurable API model map.
- Advocate: high-recall exploration model.
- Skeptic: high-precision reasoning model.
- Synthesiser: long-context integration model.
- Oracle: forecasting-oriented reasoning model.

2. Grounding hard gates
- Enforce minimum citation density in each major section.
- Reject or regenerate drafts when source support is shallow.
- Surface explicit evidence gaps instead of speculative prose.

3. Retrieval and contradiction checks
- Expand source diversity by domain and authority tier.
- Detect source disagreement and render explicit contradiction notes.
- Add confidence calibration based on source quality and agreement.

4. Free-key power profile (active)
- Use free-tier model routing per agent role.
- Increase retrieval breadth while limiting per-domain concentration.
- Enforce claim-to-citation map as hard quality gate in final synthesis.
- Use fast rerun path when quality gates fail (regenerate with stronger grounding).

### Track C: Frontend UX for Research Fidelity

1. Add evidence quality widget: citation count, authority mix, contradiction count.
2. Show per-claim source tags inline in synthesis sections.
3. Add regeneration reason banners when quality gates fail.

## Suggested API Endpoints

- GET /health
- POST /api/pipeline/start
- GET /api/pipeline/{sessionId}/stream
- GET /api/pipeline/{sessionId}/quality
- POST /api/pipeline/{sessionId}/regenerate

## Risks to Address

- Citation drift when regenerating final synthesis.
- Prompt-injection or low-trust content in remote pages.
- Model-routing cost spikes across multi-agent calls.
- Source overfitting (too many claims from one domain).

## Execution Reference

- See `src/docs/aria-free-power-workflow.md` for runtime profiles and acceptance criteria.
