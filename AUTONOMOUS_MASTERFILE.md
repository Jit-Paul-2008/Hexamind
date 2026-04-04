**Hexamind Autonomous Masterfile**

Use this file as the operating contract for a new chat session. The session should behave as a local autonomous research operator and should not ask for repeated confirmation between runs.

**Objective**

Run a continuous local research-improvement loop:
1. Extract real source data from configured local inputs or approved endpoints.
2. Run the Hexamind research pipeline with local models only.
3. Store the full report, agent outputs, metadata, and comparisons.
4. Compare against the previous run and record semantic deltas.
5. Analyze gaps and generate improvement suggestions with the 70B model.
6. Apply only safe, bounded improvements.
7. Repeat for the next run.

**Run Protocol**

The chat must operate in autonomous mode and advance exactly one run at a time.

After completing a run, the chat must stop and report exactly:

`Run:(run_number) is completed`

Do not start the next run until the previous run has been reported with that marker.

**Model Roles**

- `llama3.1:8b`: Advocate, Skeptic, Verifier, fast support tasks.
- `llama3.1:70b-instruct-q4_K_M`: Synthesiser, Oracle, final improvement reasoning.
- `nomic-embed-text:latest`: Local embedding and similarity work.

**Required Environment**

Set these before running the loop:

- `AUTONOMOUS_ENABLED=true`
- `HEXAMIND_MODEL_PROVIDER=local`
- `HEXAMIND_LOCAL_STRICT=1`
- `HEXAMIND_WEB_RESEARCH=1` for live-source enrichment when you want broader coverage
- `HEXAMIND_LOCAL_MODEL_SMALL=llama3.1:8b`
- `HEXAMIND_LOCAL_MODEL_MEDIUM=llama3.1:70b-instruct-q4_K_M`
- `HEXAMIND_LOCAL_MODEL_LARGE=llama3.1:70b-instruct-q4_K_M`
- `HEXAMIND_LOCAL_EMBEDDINGS_MODEL=nomic-embed-text:latest`
- `AUTONOMOUS_DATA_SOURCES=...`
- `AUTONOMOUS_MIN_SOURCE_COUNT=3`
- `AUTONOMOUS_MIN_SOURCE_DIVERSITY=3`
- `AUTONOMOUS_MIN_SOURCE_COVERAGE=0.85`
- `AUTONOMOUS_MIN_EXTRACTED_CHARS=4000`
- `AUTONOMOUS_IMPROVEMENT_MIN_CONFIDENCE=0.65`
- `AUTONOMOUS_IMPROVEMENT_MAX_SUGGESTIONS=3`

**Execution Entry Points**

- Continuous loop: `python scripts/run_autonomous_loop.py`
- Single run: `python scripts/extract_and_research.py`

**Storage Contract**

Each run must save:
- input data
- extraction log
- full report
- quality metadata
- comparison to previous run
- gap analysis
- suggestion set
- applied configuration
- manifest

In addition to per-run artifacts, the loop now auto-updates:

- `reports-versioned/aggregated/run-results-dashboard.md` (visual charts + table)
- `reports-versioned/aggregated/run-metrics-history.json` (machine-readable history)

Per run, the loop also creates a small manual review form:

- `reports-versioned/iterations/<iteration-id>/analysis/human-review-form.json`

Fill this form after each run with 0-10 scores for:

- accuracy
- humanLikeResponse
- usefulness
- overallHumanReviewScore (optional; if left null, dashboard uses the average of the three above)

The dashboard includes this as `Human Review` for each run.

Dashboard tracks these key parameters per run:

- token usage (from provider diagnostics when available)
- speed (total stage time)
- accuracy proxy (claim verification rate)
- human-like response proxy (structure + fluency heuristic)
- usefulness proxy (weighted quality + verification + coverage + citations)

**Web-Enabled Mode**

If `HEXAMIND_WEB_RESEARCH=1`, the new chat should treat live web retrieval as a coverage booster, not a replacement for the supplied local corpus. The preferred flow is:

1. Extract local sources first.
2. Use live web retrieval only to fill coverage gaps or corroborate weak claims.
3. Keep the source corpus and coverage summary in the run manifest.
4. Do not advance to the next run if source coverage is below the configured minimum.

**Current Readiness**

The system is usable now for controlled runs with web-enabled coverage. The next chat should still validate with one single run before leaving it unattended. That is the correct final safety step before long autonomous operation.
