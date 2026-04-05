# ARIA Refined Full-API Plan

## Objective
Evolve ARIA from the current system into a staged, high-quality, cost-aware API pipeline that improves both output quality and efficiency.

## Target Architecture (Staged Multiagent)

### Operating Principle
- One research fetch.
- Three specialist processors consuming distilled evidence.
- One final synthesizer compiling the processed outputs into a user-facing report.
- Never re-send the full raw fetch to every stage if a compressed or role-filtered view is sufficient.
- Keep the final agent focused on synthesis, not retrieval cleanup.

### Stage 1: Deep Research API (Bulk Evidence Collection)
Purpose:
- Collect broad, relevant evidence once.
- Avoid repeated retrieval by downstream agents.

Required output contract (structured JSON):
- claim_id
- claim_text
- source_url
- source_domain
- source_type (primary/secondary)
- source_credibility_score
- source_timestamp
- evidence_excerpt
- confidence_score
- topic_tags

Notes:
- This stage is recall-heavy and breadth-first.
- Must return structured evidence, not unstructured text dumps.

### Stage 2: Lightweight Analysis APIs (Chunk Segregation)
Purpose:
- Process evidence into focused perspectives.
- Keep these APIs fast and cost-efficient.

Operating rule:
- Each specialist should receive a compressed evidence bundle or a role-filtered slice, not the full raw fetch unless required.

Sub-roles:
- Positive/Opportunity chunking
- Negative/Risk chunking
- Neutral/Other/Context chunking

Required output contract per chunk:
- chunk_id
- bucket_type (positive/negative/other)
- supporting_claim_ids
- counter_claim_ids
- confidence
- unresolved_questions

Notes:
- Use lightweight models here.
- Keep strict schema validation and reject malformed outputs.
- The specialist outputs should be independently useful and small enough to keep token growth bounded.

### Stage 3: Strong Synthesis API (Final Intelligence Report)
Purpose:
- Merge curated chunks into one coherent final output.
- Resolve conflicts and present balanced conclusions.

Required final report requirements:
- Executive synthesis
- Positive/negative/other integration
- Contradiction and tradeoff section
- Uncertainty and limitations section
- Claim-to-citation map
- Final recommendation with confidence band

Notes:
- Use strongest model budget here only.
- This stage is quality-critical and should receive structured, cleaned inputs only.
- Final synthesis should combine only the three processed specialist outputs plus the minimal evidence references needed for citation grounding.

## Why This Should Outperform the First Multiagent System

Expected quality gains:
- Better evidence grounding due to centralized retrieval.
- Better coherence from structured chunk handoff into synthesis.
- Lower hallucination risk when claim-citation mapping is mandatory.

Expected efficiency gains:
- Retrieval done once, not duplicated per agent.
- Lightweight models handle routing/classification tasks.
- Premium model used only for final synthesis.
- Token growth stays controlled if the three specialists consume compressed/segmented evidence instead of raw duplication.

Expected reliability gains:
- Stage-level schema validation prevents cascading garbage outputs.
- Easier debugging and observability by isolating stage failures.

## Risks and Controls

Risk: Error propagation from Stage 1.
Control:
- Add retrieval quality thresholds before allowing Stage 2.

Risk: Over-segmentation loses nuance.
Control:
- Add overlap allowance and cross-bucket reconciliation step.

Risk: Repeating full raw evidence across all specialist agents inflates token cost.
Control:
- Share one compressed evidence bundle and role-filtered slices, not duplicated full fetches.

Risk: Final synthesis invents links.
Control:
- Enforce claim-to-citation map and contradiction checks as hard gates.

Risk: Latency from strict sequential processing.
Control:
- Parallelize only inside Stage 2 where safe.

## Success Metrics

Quality metrics:
- Citation count and citation integrity
- Source count and unique domain count
- Claim verification rate
- Contradiction handling quality
- Trust score

Efficiency metrics:
- Total tokens per report
- Cost per report
- End-to-end latency
- Fail/retry rate

## Rollout Path

1. Freeze stage contracts (input/output schemas).
2. Build Stage 1 with strict evidence structure.
3. Build Stage 2 lightweight chunking endpoints.
4. Build Stage 3 strong synthesis endpoint.
5. Add quality gates at stage boundaries.
6. Run benchmark set vs old multiagent pipeline.
7. Promote only if quality and efficiency both improve.

## Decision Rule
Proceed with this refined architecture as the primary ARIA direction if benchmark results show:
- Equal or better trust and quality metrics
- Lower or equal cost per report
- Stable latency under demo/target load
