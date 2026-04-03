# ARIA Competitive Research Results

This file is the local ledger for upcoming research and test runs. It stores comparative results for ARIA versus Gemini/GPT, keeps a running line graph, and defines the local-model review loop that must happen before the next research run.

## Batch Orchestration

Use the competitive batch runner when you want one consolidated artifact for 20 topic runs.

Run command for local-architecture comparison:

```bash
npm run bench:local-architectures
```

Local role assignment:

- `ARIA` runs through the local Hexamind stack and uses the strongest local model available.
- `Gemini` is the external comparison baseline.
- `GPT` is the external GPT-family comparison baseline.
- `Verifier` and `Skeptic` are the most important local critique roles when a run fails quality gates.

Generated artifacts:

- Single-file report: `ai-service/.data/competitive-research/competitive-research-latest.md`
- Machine-readable payload: `ai-service/.data/competitive-research/competitive-research-latest.json`
- Ledger update target: this file

The batch runner updates the ledger row and rewrites the Mermaid graph after each completed batch.

## How To Use

1. Run a research or benchmark locally.
2. Record the quality score for ARIA, Gemini, and GPT in the table below.
3. Update the Mermaid line graph with the new run.
4. Feed the latest report into a local critic model such as `phi3:medium`, `qwen2.5:7b`, or `mistral:7b`.
5. Apply the improvement notes from that local model.
6. Only then start the next research run.

## Latest Status

| Run | Date | Query / Test | ARIA Quality | Gemini Quality | GPT Quality | Winner | Notes | Improvement Actions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 2026-04-03 | Initial setup | 0 | 0 | 0 | n/a | Baseline ledger created. | Await first local run. |

## Line Graph

```mermaid
xychart-beta
    title "Research Quality: ARIA vs Gemini vs GPT"
    x-axis "Run" [0]
    y-axis "Quality Score" 0 --> 100
    line "ARIA" [0]
    line "Gemini" [0]
    line "GPT" [0]
```

## Local Critic Loop

Use this loop after every completed run:

1. Collect the latest research report and quality summary.
2. Send the report to a local critic model, preferably `phi3:medium` for broad review or `qwen2.5:7b` for sharper verification.
3. Ask the critic to return:
   - the weakest claims,
   - missing evidence,
   - contradiction handling gaps,
   - model-routing improvements,
   - retrieval improvements,
   - and one short action plan.
4. Apply the action plan to ARIA before scheduling the next run.
5. Record the new run and scores here.

## Critic Prompt Template

```text
You are reviewing the latest ARIA research report.

Task:
- Identify the most important ways to improve ARIA before the next research run.
- Focus on evidence quality, contradiction handling, routing, retrieval depth, and final synthesis quality.
- Keep the answer short, specific, and actionable.

Return:
1. Top 5 weaknesses
2. Top 5 changes to make ARIA better
3. Which change should happen first
4. Whether the next research should wait until the fixes are applied
```

## Append Format

For each future run, add one row with:

- `Run`: sequential number
- `Date`: ISO date
- `Query / Test`: short description of the benchmark or research topic
- `ARIA Quality`: quality score from Hexamind
- `Gemini Quality`: comparison score from the Gemini baseline
- `GPT Quality`: comparison score from the GPT baseline
- `Winner`: ARIA, Gemini, GPT, or tie
- `Notes`: short summary of what happened
- `Improvement Actions`: short list of what the local critic recommended

## Reference Endpoints

- `GET /health`
- `GET /api/models/status`
- `GET /api/benchmark/local`
- `POST /api/pipeline/start`
- `GET /api/pipeline/{sessionId}/quality`
