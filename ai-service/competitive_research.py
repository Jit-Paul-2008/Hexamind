from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import httpx

from model_provider import (
    DeterministicPipelineModelProvider,
    GeminiPipelineModelProvider,
    LocalPipelineModelProvider,
    OpenRouterPipelineModelProvider,
    PipelineModelProvider,
)
from pipeline import PipelineService


DEFAULT_COMPETITIVE_TOPICS: tuple[str, ...] = (
    "How should we harden an API gateway for regulated enterprise traffic?",
    "What is the best rollback strategy for a critical production release?",
    "How can a research system reduce latency without losing evidence quality?",
    "What architecture best supports auditability in multi-agent research?",
    "Should a team choose local-first inference or managed API models?",
    "How should a benchmark harness compare three competing research reports?",
    "What are the strongest safeguards against citation drift in long reports?",
    "How can contradiction handling be made explicit in final synthesis?",
    "What is the most reliable way to measure retrieval quality over time?",
    "How should a system route between small, medium, and large local models?",
    "What workflow best supports policy analysis with evidence and uncertainty?",
    "How should a medical research summary surface limitations and safety warnings?",
    "What is the safest deployment strategy for an externally facing AI service?",
    "How can an operations team keep a single source of truth for report ledgers?",
    "What signals should trigger regeneration when research quality is weak?",
    "How should a forecast report separate probability from certainty?",
    "What evidence structure best supports technical implementation guidance?",
    "How can a team measure whether a system beats generic assistant baselines?",
    "What report format makes side-by-side model comparison easy to review?",
    "How should local critic models refine an already strong research answer?",
)


@dataclass(frozen=True)
class CompetitiveProviderSpec:
    label: str
    model_name: str
    provider_factory: Callable[[], PipelineModelProvider]
    notes: str = ""
    role_models: dict[str, str] | None = None


@dataclass(frozen=True)
class CompetitiveRunResult:
    label: str
    model_name: str
    session_id: str
    query: str
    final_answer: str
    quality_report: dict[str, object]
    diagnostics: dict[str, object]
    runtime_seconds: float

    @property
    def overall_score(self) -> float:
        return float(self.quality_report.get("overallScore", 0.0))

    @property
    def trust_score(self) -> float:
        return float(self.quality_report.get("trustScore", 0.0))


@dataclass(frozen=True)
class CompetitiveTopicResult:
    query: str
    provider_results: tuple[CompetitiveRunResult, ...]
    winner: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompetitiveBatchReport:
    batch_name: str
    generated_at: float
    topics: tuple[CompetitiveTopicResult, ...]
    provider_specs: tuple[CompetitiveProviderSpec, ...]
    output_markdown_path: str = ""
    output_json_path: str = ""

    @property
    def topic_count(self) -> int:
        return len(self.topics)

    def provider_stats(self) -> dict[str, dict[str, float | int]]:
        stats: dict[str, dict[str, float | int]] = {
            spec.label: {"wins": 0, "topics": 0, "averageScore": 0.0, "averageTrust": 0.0}
            for spec in self.provider_specs
        }
        for topic in self.topics:
            for result in topic.provider_results:
                bucket = stats.setdefault(
                    result.label,
                    {"wins": 0, "topics": 0, "averageScore": 0.0, "averageTrust": 0.0},
                )
                bucket["topics"] = int(bucket["topics"]) + 1
                bucket["averageScore"] = float(bucket["averageScore"]) + result.overall_score
                bucket["averageTrust"] = float(bucket["averageTrust"]) + result.trust_score
            stats.setdefault(topic.winner, {"wins": 0, "topics": 0, "averageScore": 0.0, "averageTrust": 0.0})["wins"] = int(
                stats[topic.winner]["wins"]
            ) + 1

        for bucket in stats.values():
            topics = int(bucket["topics"])
            if topics:
                bucket["averageScore"] = round(float(bucket["averageScore"]) / topics, 2)
                bucket["averageTrust"] = round(float(bucket["averageTrust"]) / topics, 2)
        return stats


def build_default_provider_specs() -> tuple[CompetitiveProviderSpec, ...]:
    aria_model = (
        os.getenv(
            "HEXAMIND_COMPETITIVE_ARIA_MODEL",
            os.getenv("HEXAMIND_LOCAL_MODEL_LARGE", os.getenv("HEXAMIND_LOCAL_MODEL", "llama3.1:8b")),
        )
        .strip()
        or "llama3.1:8b"
    )
    gemini_model = os.getenv("HEXAMIND_COMPETITIVE_GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"
    gpt_model = os.getenv("HEXAMIND_COMPETITIVE_GPT_MODEL", "openai/gpt-4.1-mini").strip() or "openai/gpt-4.1-mini"

    return (
        CompetitiveProviderSpec(
            label="ARIA",
            model_name=aria_model,
            provider_factory=lambda: _safe_provider_factory(
                "ARIA",
                aria_model,
                lambda: LocalPipelineModelProvider(aria_model),
            ),
            notes="Local-first Hexamind route used for the internal ARIA run.",
        ),
        CompetitiveProviderSpec(
            label="Gemini",
            model_name=gemini_model,
            provider_factory=lambda: _safe_provider_factory(
                "Gemini",
                gemini_model,
                lambda: GeminiPipelineModelProvider(gemini_model),
            ),
            notes="External comparison baseline.",
        ),
        CompetitiveProviderSpec(
            label="GPT",
            model_name=gpt_model,
            provider_factory=lambda: _safe_provider_factory(
                "GPT",
                gpt_model,
                lambda: OpenRouterPipelineModelProvider(gpt_model),
            ),
            notes="GPT-family comparison baseline via OpenRouter when available.",
        ),
    )


def build_local_architecture_provider_specs(max_architectures: int = 3) -> tuple[CompetitiveProviderSpec, ...]:
    models = _discover_local_models()
    model_small, model_medium, model_large = _pick_local_tiers(models)
    default_model = model_medium

    architectures = [
        {
            "label": "Local-Balanced",
            "notes": "Small on exploratory agents, medium on synthesis/oracle, large on final.",
            "roles": {
                "advocate": model_small,
                "skeptic": model_small,
                "synthesiser": model_medium,
                "oracle": model_medium,
                "verifier": model_small,
                "final": model_large,
            },
        },
        {
            "label": "Local-Throughput",
            "notes": "Favor latency: small for most roles and medium final synthesis.",
            "roles": {
                "advocate": model_small,
                "skeptic": model_small,
                "synthesiser": model_small,
                "oracle": model_small,
                "verifier": model_small,
                "final": model_medium,
            },
        },
        {
            "label": "Local-Quality",
            "notes": "Favor answer quality: large model on all agent roles.",
            "roles": {
                "advocate": model_large,
                "skeptic": model_large,
                "synthesiser": model_large,
                "oracle": model_large,
                "verifier": model_large,
                "final": model_large,
            },
        },
        {
            "label": "Local-VerificationHeavy",
            "notes": "Boost skeptic/verifier/final while keeping discovery lighter.",
            "roles": {
                "advocate": model_small,
                "skeptic": model_large,
                "synthesiser": model_medium,
                "oracle": model_medium,
                "verifier": model_large,
                "final": model_large,
            },
        },
    ]

    specs: list[CompetitiveProviderSpec] = []
    for architecture in architectures[: max(1, max_architectures)]:
        roles = architecture["roles"]
        roles_copy = {key: value for key, value in roles.items()}
        label = str(architecture["label"])
        specs.append(
            CompetitiveProviderSpec(
                label=label,
                model_name=roles_copy.get("final", default_model),
                provider_factory=lambda roles=roles_copy: _safe_provider_factory(
                    "local",
                    roles.get("final", default_model),
                    lambda: _build_local_provider_with_overrides(default_model, roles),
                ),
                notes=str(architecture["notes"]),
                role_models=roles_copy,
            )
        )
    return tuple(specs)


async def run_competitive_batch(
    queries: Iterable[str] | None = None,
    provider_specs: tuple[CompetitiveProviderSpec, ...] | None = None,
) -> CompetitiveBatchReport:
    selected_queries = tuple(queries or DEFAULT_COMPETITIVE_TOPICS)
    selected_specs = provider_specs or build_default_provider_specs()
    batch_started = time.perf_counter()

    provider_services: dict[str, tuple[PipelineService, PipelineModelProvider]] = {}
    for spec in selected_specs:
        provider = spec.provider_factory()
        storage_path = _competitive_storage_dir().joinpath(f"{spec.label.lower()}-sessions.json")
        provider_services[spec.label] = (
            PipelineService(storage_path=storage_path, model_provider=provider),
            provider,
        )

    topic_results: list[CompetitiveTopicResult] = []
    for query in selected_queries:
        provider_runs: list[CompetitiveRunResult] = []
        for spec in selected_specs:
            service, provider = provider_services[spec.label]
            provider_runs.append(await _run_single_provider(service, provider, spec, query))

        winner = max(provider_runs, key=lambda item: (item.overall_score, item.trust_score)).label
        topic_results.append(
            CompetitiveTopicResult(
                query=query,
                provider_results=tuple(provider_runs),
                winner=winner,
                notes=_topic_notes(provider_runs),
            )
        )

    report = CompetitiveBatchReport(
        batch_name=(
            "ARIA Local Architecture Competitive Batch"
            if selected_specs and all(spec.label.startswith("Local-") for spec in selected_specs)
            else "ARIA Competitive Research Batch"
        ),
        generated_at=time.time(),
        topics=tuple(topic_results),
        provider_specs=selected_specs,
    )

    duration = time.perf_counter() - batch_started
    print(f"competitive batch completed in {duration:.2f}s")
    return report


async def _run_single_provider(
    service: PipelineService,
    provider: PipelineModelProvider,
    spec: CompetitiveProviderSpec,
    query: str,
) -> CompetitiveRunResult:
    run_started = time.perf_counter()
    tenant_id = "competitive-research"
    session_id = service.start(query, tenant_id=tenant_id)
    final_answer = ""

    try:
        async for event in service.stream_events(session_id, tenant_id):
            payload = _decode_sse_payload(event.get("data", ""))
            if payload.get("type") == "pipeline_done":
                final_answer = str(payload.get("fullContent", ""))
    except Exception as exc:
        final_answer = (
            "## Competitive Run Failed\n"
            f"- Provider: {spec.label}\n"
            f"- Error: {type(exc).__name__}: {exc}"
        )

    quality_report = service.get_quality_report(session_id, tenant_id)
    diagnostics = provider.diagnostics()
    runtime_seconds = round(time.perf_counter() - run_started, 3)
    return CompetitiveRunResult(
        label=spec.label,
        model_name=spec.model_name,
        session_id=session_id,
        query=query,
        final_answer=final_answer,
        quality_report=quality_report,
        diagnostics=diagnostics,
        runtime_seconds=runtime_seconds,
    )


def save_competitive_batch_report(
    report: CompetitiveBatchReport,
    output_path: str | None = None,
) -> tuple[str, str]:
    target_md = Path(output_path) if output_path else _competitive_storage_dir().joinpath("competitive-research-latest.md")
    target_json = target_md.with_suffix(".json")
    target_md.parent.mkdir(parents=True, exist_ok=True)
    target_json.parent.mkdir(parents=True, exist_ok=True)

    target_md.write_text(_render_markdown_report(report), encoding="utf-8")
    target_json.write_text(json.dumps(_report_payload(report), indent=2, sort_keys=True), encoding="utf-8")
    return str(target_md), str(target_json)


def load_latest_competitive_batch_report() -> dict[str, object]:
    target_json = _competitive_storage_dir().joinpath("competitive-research-latest.json")
    if not target_json.exists():
        return {"status": "missing", "notes": ["No competitive batch report has been generated yet."]}
    try:
        payload = json.loads(target_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": "error", "notes": ["Competitive batch report could not be parsed."]}
    payload["status"] = "ready"
    return payload


def update_competitive_results_ledger(
    report: CompetitiveBatchReport,
    ledger_path: str | None = None,
) -> str:
    target = Path(ledger_path) if ledger_path else Path(__file__).resolve().parents[1] / "src" / "docs" / "aria-competitive-results.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    text = target.read_text(encoding="utf-8") if target.exists() else _ledger_template()
    lines = text.splitlines()

    run_number = _next_run_number(lines)
    summary = report.provider_stats()
    score_columns = _score_columns(report, summary)
    aria_score = score_columns[0][1]
    gemini_score = score_columns[1][1]
    gpt_score = score_columns[2][1]
    winner = max(
        (("ARIA", aria_score), ("Gemini", gemini_score), ("GPT", gpt_score)),
        key=lambda item: item[1],
    )[0]
    mapping_note = f"Columns mapped as ARIA={score_columns[0][0]}, Gemini={score_columns[1][0]}, GPT={score_columns[2][0]}."
    row = (
        f"| {run_number} | {time.strftime('%Y-%m-%d', time.localtime(report.generated_at))} | "
        f"{report.batch_name} ({report.topic_count} topics) | {aria_score:.1f} | {gemini_score:.1f} | {gpt_score:.1f} | {winner} | "
        f"{mapping_note} Generated consolidated competitive report and updated the ledger. | Local critic review pending. |"
    )

    updated = _insert_ledger_row(lines, row)
    updated = _rewrite_ledger_graph(updated)
    target.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
    return str(target)


def _safe_provider_factory(
    label: str,
    model_name: str,
    factory: Callable[[], PipelineModelProvider],
) -> PipelineModelProvider:
    try:
        return factory()
    except Exception as exc:
        return DeterministicPipelineModelProvider(
            configured_provider=label.lower(),
            model_name=model_name,
            reason=f"{label} provider unavailable: {type(exc).__name__}",
        )


def _competitive_storage_dir() -> Path:
    return Path(__file__).resolve().with_name(".data").joinpath("competitive-research")


def _decode_sse_payload(raw: str) -> dict[str, object]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _topic_notes(provider_runs: Iterable[CompetitiveRunResult]) -> tuple[str, ...]:
    notes: list[str] = []
    for result in provider_runs:
        notes.append(
            f"{result.label}: score {result.overall_score:.1f}, trust {result.trust_score:.1f}, runtime {result.runtime_seconds:.1f}s"
        )
    return tuple(notes)


def _render_markdown_report(report: CompetitiveBatchReport) -> str:
    stats = report.provider_stats()
    lines = [
        f"# {report.batch_name}",
        "",
        f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report.generated_at))}",
        f"Topics covered: {report.topic_count}",
        "",
        "## Provider Summary",
        "",
        "| Provider | Wins | Average Score | Average Trust | Model | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for spec in report.provider_specs:
        bucket = stats.get(spec.label, {})
        role_summary = ""
        if spec.role_models:
            role_summary = "; ".join(
                f"{role}={model}"
                for role, model in spec.role_models.items()
                if role in {"advocate", "skeptic", "synthesiser", "oracle", "verifier", "final"}
            )
            if role_summary:
                role_summary = f" ({role_summary})"
        lines.append(
            f"| {spec.label} | {int(bucket.get('wins', 0))} | {float(bucket.get('averageScore', 0.0)):.1f} | {float(bucket.get('averageTrust', 0.0)):.1f} | {spec.model_name} | {(spec.notes or 'n/a') + role_summary} |"
        )

    lines.extend([
        "",
        "## Topic Comparison",
        "",
    ])

    for index, topic in enumerate(report.topics, start=1):
        lines.extend(
            [
                f"### {index}. {topic.query}",
                "",
                "| Provider | Score | Trust | Session | Runtime | Winner |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for result in topic.provider_results:
            lines.append(
                f"| {result.label} | {result.overall_score:.1f} | {result.trust_score:.1f} | {result.session_id} | {result.runtime_seconds:.1f}s | {'yes' if result.label == topic.winner else ''} |"
            )
        lines.append("")
        for result in topic.provider_results:
            lines.extend(
                [
                    "<details>",
                    f"<summary>{result.label} report</summary>",
                    "",
                    "```text",
                    _truncate_block(result.final_answer),
                    "```",
                    "</details>",
                    "",
                ]
            )
        lines.extend([f"Winner: {topic.winner}", ""])

    return "\n".join(lines).rstrip() + "\n"


def _report_payload(report: CompetitiveBatchReport) -> dict[str, object]:
    return {
        "batchName": report.batch_name,
        "generatedAt": report.generated_at,
        "topicCount": report.topic_count,
        "providerSpecs": [
            {
                "label": spec.label,
                "modelName": spec.model_name,
                "notes": spec.notes,
                "roleModels": dict(spec.role_models or {}),
            }
            for spec in report.provider_specs
        ],
        "providerStats": report.provider_stats(),
        "topics": [
            {
                "query": topic.query,
                "winner": topic.winner,
                "notes": list(topic.notes),
                "results": [
                    {
                        "label": result.label,
                        "modelName": result.model_name,
                        "sessionId": result.session_id,
                        "query": result.query,
                        "finalAnswer": result.final_answer,
                        "qualityReport": result.quality_report,
                        "diagnostics": result.diagnostics,
                        "runtimeSeconds": result.runtime_seconds,
                        "overallScore": result.overall_score,
                        "trustScore": result.trust_score,
                    }
                    for result in topic.provider_results
                ],
            }
            for topic in report.topics
        ],
    }


def _truncate_block(text: str, limit: int = 2600) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 32].rstrip() + "\n...[truncated]"


def _find_result(topic: CompetitiveTopicResult, label: str) -> CompetitiveRunResult:
    for result in topic.provider_results:
        if result.label == label:
            return result
    return topic.provider_results[0]


def _score_columns(
    report: CompetitiveBatchReport,
    summary: dict[str, dict[str, float | int]],
) -> list[tuple[str, float]]:
    labels = [spec.label for spec in report.provider_specs]
    columns: list[tuple[str, float]] = []
    for label in labels[:3]:
        columns.append((label, float(summary.get(label, {}).get("averageScore", 0.0))))
    while len(columns) < 3:
        columns.append((f"n/a-{len(columns)+1}", 0.0))
    return columns


def _discover_local_models() -> list[str]:
    base = os.getenv("HEXAMIND_LOCAL_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
    candidates = [
        f"{base}/models",
        f"{base.replace('/v1', '')}/api/tags",
    ]
    for endpoint in candidates:
        try:
            with httpx.Client(timeout=6.0) as client:
                response = client.get(endpoint)
                if response.status_code >= 400:
                    continue
                payload = response.json()
        except Exception:
            continue

        models: list[str] = []
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            for item in payload["data"]:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    candidate = item["id"]
                    if _is_generation_model(candidate):
                        models.append(candidate)
        if isinstance(payload, dict) and isinstance(payload.get("models"), list):
            for item in payload["models"]:
                if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                    continue
                candidate = item["name"]
                family = ""
                details = item.get("details")
                if isinstance(details, dict):
                    family = str(details.get("family", "")).strip().lower()
                if _is_generation_model(candidate, family=family):
                    models.append(candidate)
        if models:
            seen: set[str] = set()
            unique: list[str] = []
            for model in models:
                if model in seen:
                    continue
                seen.add(model)
                unique.append(model)
            return unique
    return []


def _is_generation_model(model_name: str, family: str = "") -> bool:
    normalized = model_name.strip().lower()
    if not normalized:
        return False
    if any(token in normalized for token in ("embed", "embedding", "rerank", "bge", "e5", "nomic-embed", "mxbai-embed")):
        return False
    if family in {"bert", "embedding", "reranker"}:
        return False
    return True


def _pick_local_tiers(models: list[str]) -> tuple[str, str, str]:
    configured_small = os.getenv("HEXAMIND_LOCAL_MODEL_SMALL", "").strip()
    configured_medium = os.getenv("HEXAMIND_LOCAL_MODEL_MEDIUM", "").strip()
    configured_large = os.getenv("HEXAMIND_LOCAL_MODEL_LARGE", "").strip()
    configured_default = os.getenv("HEXAMIND_LOCAL_MODEL", "llama3.1:8b").strip() or "llama3.1:8b"

    if configured_small and configured_medium and configured_large:
        return configured_small, configured_medium, configured_large

    generation_models = [model for model in models if _is_generation_model(model)]

    if not generation_models:
        small = configured_small or configured_default
        medium = configured_medium or configured_default
        large = configured_large or configured_default
        return small, medium, large

    ranked = sorted(generation_models, key=_model_size_estimate)
    small = configured_small or ranked[0]
    medium = configured_medium or ranked[len(ranked) // 2]
    large = configured_large or ranked[-1]
    return small, medium, large


def _is_generation_model(model_name: str) -> bool:
    lowered = model_name.lower()
    blocked_markers = (
        "embed",
        "embedding",
        "bge",
        "e5",
        "nomic-embed",
        "mxbai-embed",
    )
    if any(marker in lowered for marker in blocked_markers):
        return False
    return True


def _model_size_estimate(model_name: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)b", model_name.lower())
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 8.0
    return 8.0


def _build_local_provider_with_overrides(
    default_model: str,
    role_models: dict[str, str],
) -> PipelineModelProvider:
    keys = {
        "HEXAMIND_AGENT_MODEL_ADVOCATE": role_models.get("advocate", default_model),
        "HEXAMIND_AGENT_MODEL_SKEPTIC": role_models.get("skeptic", default_model),
        "HEXAMIND_AGENT_MODEL_SYNTHESIS": role_models.get("synthesiser", default_model),
        "HEXAMIND_AGENT_MODEL_ORACLE": role_models.get("oracle", default_model),
        "HEXAMIND_AGENT_MODEL_VERIFIER": role_models.get("verifier", default_model),
        "HEXAMIND_AGENT_MODEL_FINAL": role_models.get("final", default_model),
        "HEXAMIND_LOCAL_MODEL_SMALL": role_models.get("advocate", default_model),
        "HEXAMIND_LOCAL_MODEL_MEDIUM": role_models.get("synthesiser", default_model),
        "HEXAMIND_LOCAL_MODEL_LARGE": role_models.get("final", default_model),
        "HEXAMIND_LOCAL_MODEL": default_model,
    }

    previous = {name: os.environ.get(name) for name in keys}
    try:
        for name, value in keys.items():
            os.environ[name] = value
        return LocalPipelineModelProvider(default_model)
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _ledger_template() -> str:
    return """# ARIA Competitive Research Results

This file is the local ledger for upcoming research and test runs. It stores comparative results for ARIA versus Gemini/GPT, keeps a running line graph, and defines the local-model review loop that must happen before the next research run.

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
"""


def _next_run_number(lines: list[str]) -> int:
    run_numbers: list[int] = []
    for line in lines:
        if not line.startswith("| "):
            continue
        parts = [part.strip() for part in line.split("|") if part.strip()]
        if not parts or parts[0] in {"Run", "---"}:
            continue
        try:
            run_numbers.append(int(parts[0]))
        except ValueError:
            continue
    return (max(run_numbers) + 1) if run_numbers else 1


def _insert_ledger_row(lines: list[str], row: str) -> list[str]:
    try:
        graph_start = next(index for index, line in enumerate(lines) if line.strip() == "## Line Graph")
    except StopIteration:
        return lines + ["", row]

    try:
        table_start = next(index for index, line in enumerate(lines) if line.strip() == "## Latest Status")
    except StopIteration:
        return lines + ["", row]

    try:
        graph_index = next(index for index in range(table_start, graph_start) if lines[index].startswith("| 0 "))
    except StopIteration:
        return lines[:graph_start] + [row, ""] + lines[graph_start:]

    updated = list(lines)
    updated.insert(graph_start, row)
    updated.insert(graph_start + 1, "")
    return updated


def _rewrite_ledger_graph(lines: list[str]) -> list[str]:
    try:
        graph_start = next(index for index, line in enumerate(lines) if line.strip() == "```mermaid")
        graph_end = next(index for index in range(graph_start + 1, len(lines)) if lines[index].strip() == "```")
    except StopIteration:
        return lines

    rows = _extract_ledger_rows(lines)
    if not rows:
        return lines

    runs = [str(row[0]) for row in rows]
    aria_scores = [str(row[3]) for row in rows]
    gemini_scores = [str(row[4]) for row in rows]
    gpt_scores = [str(row[5]) for row in rows]
    graph_lines = [
        "```mermaid",
        "xychart-beta",
        '    title "Research Quality: ARIA vs Gemini vs GPT"',
        f'    x-axis "Run" [{", ".join(runs)}]',
        '    y-axis "Quality Score" 0 --> 100',
        f'    line "ARIA" [{", ".join(aria_scores)}]',
        f'    line "Gemini" [{", ".join(gemini_scores)}]',
        f'    line "GPT" [{", ".join(gpt_scores)}]',
        "```",
    ]
    return lines[:graph_start] + graph_lines + lines[graph_end + 1 :]


def _extract_ledger_rows(lines: list[str]) -> list[tuple[int, str, str, float, float, float]]:
    rows: list[tuple[int, str, str, float, float, float]] = []
    for line in lines:
        if not line.startswith("| "):
            continue
        parts = [part.strip() for part in line.split("|") if part.strip()]
        if len(parts) < 6 or parts[0] in {"Run", "---"}:
            continue
        try:
            run = int(parts[0])
            aria = float(parts[3])
            gemini = float(parts[4])
            gpt = float(parts[5])
        except ValueError:
            continue
        rows.append((run, parts[1], parts[2], aria, gemini, gpt))
    rows.sort(key=lambda item: item[0])
    return rows