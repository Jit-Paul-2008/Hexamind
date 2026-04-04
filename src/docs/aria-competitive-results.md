# ARIA Competitive Research Results

This file is the local ledger for upcoming research and test runs. It stores comparative results for ARIA against local architecture candidates, keeps a running line graph, and defines the local-model review loop that must happen before the next research run.

## Batch Orchestration

Use the competitive batch runner when you want one consolidated artifact for 20 topic runs.

Run command for local-architecture comparison:

```bash
npm run bench:local-architectures
```

Local architecture candidates:

- `Local-Balanced` uses small models for discovery and a larger model for final synthesis.
- `Local-Throughput` favors latency with smaller models across most roles.
- `Local-Quality` assigns the largest available local model to every role.
- `Local-VerificationHeavy` boosts skeptic, verifier, and final synthesis quality.
- `Verifier` and `Skeptic` are the most important critique roles when a run fails quality gates.

Generated artifacts:

- Single-file report: `ai-service/.data/competitive-research/competitive-research-latest.md`
- Machine-readable payload: `ai-service/.data/competitive-research/competitive-research-latest.json`
- Ledger update target: this file

The batch runner updates the ledger row and rewrites the Mermaid graph after each completed batch.

Operational note:

- Do not run the 20-topic competition through MCP/Pylance tools. Those tools are not meant for long-running, network-bound batches and can time out.
- The local runner already probes the model server on startup and then performs per-topic local model calls with stage timeouts, so use the shell/venv runner instead.

## How To Use

1. Run a research or benchmark locally.
2. Record the quality score for the 3 compared architecture slots in the table below.
3. Update the Mermaid line graph with the new run.
4. Feed the latest report into a local critic model such as `phi3:medium`, `qwen2.5:7b`, or `mistral:7b`.
5. Apply the improvement notes from that local model.
6. Only then start the next research run.

Note: when running local-architecture mode, the table headers `ARIA`, `Gemini`, and `GPT` are used as fixed display columns and map to the first three architecture candidates for that run. The batch row notes store the exact mapping.

## Latest Status

| Run | Date | Query / Test | ARIA Quality | Gemini Quality | GPT Quality | Winner | Notes | Improvement Actions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 2026-04-03 | Initial setup | 0 | 0 | 0 | n/a | Baseline ledger created. | Await first local run. |

| 1 | 2026-04-03 | ARIA Local Architecture Competitive Batch (20 topics) | 70.0 | 70.0 | 70.0 | ARIA | Columns mapped as ARIA=Local-Balanced, Gemini=Local-Throughput, GPT=Local-Quality. Generated consolidated competitive report and updated the ledger. | Local critic review pending. |

| 2 | 2026-04-03 | ARIA Local Architecture Competitive Batch (20 topics) | 70.0 | 70.0 | 70.0 | ARIA | Columns mapped as ARIA=Local-Balanced, Gemini=Local-Throughput, GPT=Local-Quality. Generated consolidated competitive report and updated the ledger. | Local critic review pending. |

| 3 | 2026-04-03 | ARIA Local Architecture Competitive Batch (20 topics) | 70.0 | 70.0 | 70.0 | ARIA | Columns mapped as ARIA=Local-Balanced, Gemini=Local-Throughput, GPT=Local-Quality. Generated consolidated competitive report and updated the ledger. | Local critic review pending. |

| 4 | 2026-04-03 | ARIA Local Architecture Competitive Batch (20 topics) | 70.0 | 70.0 | 70.0 | ARIA | Columns mapped as ARIA=Local-Balanced, Gemini=Local-Throughput, GPT=Local-Quality. Generated consolidated competitive report and updated the ledger. | Local critic review pending. |

| 5 | 2026-04-04 | ARIA Local Architecture Competitive Batch (1 topics) | 70.0 | 70.0 | 70.0 | ARIA | Columns mapped as ARIA=Local-Balanced, Gemini=Local-Throughput, GPT=Local-Quality. Generated consolidated competitive report and updated the ledger. | Local critic review pending. |

## Line Graph

```mermaid
xychart-beta
    title "Research Quality: ARIA vs Gemini vs GPT"
    x-axis "Run" [0, 1, 2, 3, 4, 5]
    y-axis "Quality Score" 0 --> 100
    line "ARIA" [0.0, 70.0, 70.0, 70.0, 70.0, 70.0]
    line "Gemini" [0.0, 70.0, 70.0, 70.0, 70.0, 70.0]
    line "GPT" [0.0, 70.0, 70.0, 70.0, 70.0, 70.0]
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
- `ARIA Quality`: score for mapped architecture slot 1
- `Gemini Quality`: score for mapped architecture slot 2
- `GPT Quality`: score for mapped architecture slot 3
- `Winner`: ARIA, Gemini, GPT, or tie
- `Notes`: short summary of what happened
- `Improvement Actions`: short list of what the local critic recommended

## Reference Endpoints

- `GET /health`
- `GET /api/models/status`
- `GET /api/benchmark/local`
- `POST /api/pipeline/start`
- `GET /api/pipeline/{sessionId}/quality`
