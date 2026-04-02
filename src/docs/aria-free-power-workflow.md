# ARIA Free-Power Workflow

## Objective

Build a deep-research system that outperforms generic single-model assistants while using free-tier API keys.

## Core Principle

Performance comes from workflow quality, not one model call.
ARIA should win by doing better retrieval, stronger adversarial reasoning, stricter evidence gates, and transparent uncertainty.

## Free-First Model Strategy

Use low-cost/high-availability models by role instead of one model for everything.

- Advocate: fast exploration model (broad search synthesis)
- Skeptic: rigorous reasoning model (failure mode pressure-testing)
- Synthesiser: long-context integration model (claim reconciliation)
- Oracle: forecasting model (scenario and trigger modeling)
- Final: strongest free model available for structured report assembly

Use environment overrides per role:

- HEXAMIND_AGENT_MODEL_ADVOCATE
- HEXAMIND_AGENT_MODEL_SKEPTIC
- HEXAMIND_AGENT_MODEL_SYNTHESIS
- HEXAMIND_AGENT_MODEL_ORACLE
- HEXAMIND_AGENT_MODEL_FINAL

## Pipeline Blueprint

1. Query decomposition
- Transform user question into 5 to 8 targeted search intents:
  - official docs
  - latest evidence
  - benchmark/evaluation
  - implementation guide
  - limitations and failures

2. Retrieval pass
- Pull 8+ sources with domain diversity limits.
- Cap repeated domains to avoid source monoculture.
- Compute source credibility scores.

3. Agent debate pass
- Advocate builds strongest positive thesis with [Sx] citations.
- Skeptic attacks assumptions, constraints, and edge cases with [Sx].
- Synthesiser resolves tradeoffs and marks contradictions.
- Oracle projects 60/25/15 scenarios with evidence-linked triggers.

4. Quality gate
- Reject/regenerate if:
  - citation density is too low
  - claim-to-citation map is missing
  - key sections are missing
  - uncertainty is hidden instead of explicit

5. Final synthesis
- Produce a sectioned report with:
  - claim-to-citation map
  - contradictions and uncertainty
  - source inventory with credibility values

## Why This Can Beat Market Baselines

Most assistants fail on deep research because they:

- rely on one reasoning pass
- under-cite evidence
- ignore contradictions
- do not enforce output quality thresholds

ARIA can outperform by combining adversarial multi-agent reasoning with hard evidence gates and retrieval diversity.

## Suggested Runtime Profiles

### Profile: Free Max Quality

- HEXAMIND_COST_MODE=free
- HEXAMIND_WEB_RESEARCH=1
- HEXAMIND_RESEARCH_MAX_SOURCES=10
- HEXAMIND_MAX_SOURCES_PER_DOMAIN=2
- HEXAMIND_STREAM_CHUNK_DELAY_MS=4

### Profile: Free Fast Iteration

- HEXAMIND_COST_MODE=free
- HEXAMIND_WEB_RESEARCH=1
- HEXAMIND_RESEARCH_MAX_SOURCES=6
- HEXAMIND_MAX_SOURCES_PER_DOMAIN=2
- HEXAMIND_STREAM_CHUNK_DELAY_MS=2

## Acceptance Criteria

ARIA deep-research run is accepted only if:

1. Final report includes a claim-to-citation map.
2. At least 4 unique source IDs are cited when sources exist.
3. Contradictions are explicitly surfaced when evidence conflicts.
4. Source inventory includes authority and credibility metadata.
5. Recommendation includes uncertainty and trigger-based guardrails.
