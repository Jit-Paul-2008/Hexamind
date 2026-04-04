from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
SERVICE_DIR = ROOT / "ai-service"
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from import compare_with_previous_report, extended_benchmark_suite, run_benchmark_suite, save_benchmark_report
from main import _benchmark_local_models
from model_provider import LocalPipelineModelProvider
from pipeline import PipelineService

TOPIC_TEMPLATES = (
    "What are the current evidence-backed developments around {topic} in 2026?",
    "How should decision-makers evaluate risks and opportunities for {topic} right now?",
    "What is the most practical implementation strategy for organizations working on {topic}?",
    "What are the strongest verified claims and open uncertainties about {topic} today?",
)

FALLBACK_TOPICS = (
    "grid-scale battery storage",
    "precision agriculture drones",
    "post-quantum cryptography migration",
    "synthetic biology safety governance",
    "carbon border adjustment mechanisms",
    "maritime autonomous navigation",
    "rural telemedicine infrastructure",
    "urban flood early-warning systems",
    "edge AI in manufacturing",
    "high-speed rail electrification",
    "digital identity interoperability",
    "space debris remediation",
)


@dataclass
class RunArtifacts:
    run_index: int
    topic: str
    report_path: Path
    benchmark_path: Path
    quality: dict[str, Any]
    local_bench: dict[str, Any]
    tuning_applied: dict[str, Any]


@dataclass
class TuningState:
    model_name: str = "llama3.1:8b"
    token_mode: str = "smart"
    max_sources: int = 8
    max_terms: int = 8
    max_hits_per_term: int = 6
    min_relevance: float = 0.2
    parallel_agents: bool = False


def _now_stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def _sanitize_topic(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw).strip()
    text = re.sub(r"\([^)]*\)", "", text).strip()
    return text


async def _fetch_random_topic(used: set[str]) -> str:
    # Pull a truly random live topic first; fallback to curated topics if unavailable.
    for _ in range(6):
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get("https://en.wikipedia.org/api/rest_v1/page/random/summary")
                response.raise_for_status()
                payload = response.json()
                title = _sanitize_topic(str(payload.get("title", "")))
                if not title:
                    continue
                norm = title.casefold()
                if norm in used:
                    continue
                used.add(norm)
                template = random.choice(TOPIC_TEMPLATES)
                return template.format(topic=title)
        except Exception:
            continue

    for topic in FALLBACK_TOPICS:
        norm = topic.casefold()
        if norm not in used:
            used.add(norm)
            return random.choice(TOPIC_TEMPLATES).format(topic=topic)

    suffix = random.randint(1000, 9999)
    return f"What are the strongest evidence-backed implications of emerging technology trend {suffix} in 2026?"


def _apply_runtime_env(tuning: TuningState) -> None:
    os.environ["HEXAMIND_MODEL_PROVIDER"] = "local"
    os.environ["HEXAMIND_MODEL_NAME"] = tuning.model_name
    os.environ["HEXAMIND_LOCAL_BASE_URL"] = os.getenv("HEXAMIND_LOCAL_BASE_URL", "http://127.0.0.1:11434/v1")
    os.environ["HEXAMIND_LOCAL_STRICT"] = "1"
    os.environ["HEXAMIND_WEB_RESEARCH"] = "1"
    os.environ["HEXAMIND_RESEARCH_PROVIDER"] = os.getenv("HEXAMIND_RESEARCH_PROVIDER", "duckduckgo")

    os.environ["HEXAMIND_TOKEN_MODE"] = tuning.token_mode
    os.environ["HEXAMIND_RESEARCH_MAX_SOURCES"] = str(tuning.max_sources)
    os.environ["HEXAMIND_RESEARCH_MAX_TERMS"] = str(tuning.max_terms)
    os.environ["HEXAMIND_RESEARCH_MAX_HITS_PER_TERM"] = str(tuning.max_hits_per_term)
    os.environ["HEXAMIND_RESEARCH_MIN_RELEVANCE"] = f"{tuning.min_relevance:.2f}"
    os.environ["HEXAMIND_PARALLEL_AGENTS"] = "1" if tuning.parallel_agents else "0"


def _estimate_tokens(final_answer: str) -> int:
    return int(max(1, round(len(final_answer.split()) * 1.33)))


def _save_report(topic: str, session_id: str, final_answer: str, quality: dict[str, Any], run_index: int) -> Path:
    out_dir = SERVICE_DIR / ".data" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"random-topic-full-report-{_now_stamp()}-run{run_index:02d}.md"

    metrics = quality.get("metrics", {}) if isinstance(quality, dict) else {}

    body = (
        "# Real-Time Random Topic Report\n\n"
        f"- Run: {run_index}\n"
        f"- Topic: {topic}\n"
        f"- Session ID: {session_id}\n"
        f"- Generated At: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- Overall Score: {quality.get('overallScore', 0.0)}\n"
        f"- Trust Score: {quality.get('trustScore', 0.0)}\n"
        f"- Source Count: {metrics.get('sourceCount', 0)}\n"
        f"- Claim Verification Rate: {metrics.get('claimVerificationRate', 0.0)}\n\n"
        "## Full Structured Synthesised Report\n\n"
        f"{final_answer}\n"
    )
    out_file.write_text(body, encoding="utf-8")
    return out_file


def _pick_fastest_model(local_bench: dict[str, Any]) -> str | None:
    entries = local_bench.get("benchmarks", []) if isinstance(local_bench, dict) else []
    viable: list[dict[str, Any]] = [x for x in entries if isinstance(x, dict) and not x.get("error")]
    if not viable:
        return None
    viable.sort(key=lambda x: float(x.get("tokensPerSecond", 0.0)), reverse=True)
    return str(viable[0].get("model", "")).strip() or None


def _tune_for_next_run(
    tuning: TuningState,
    quality: dict[str, Any],
    final_answer: str,
    local_bench: dict[str, Any],
) -> dict[str, Any]:
    overall = float(quality.get("overallScore", 0.0))
    trust = float(quality.get("trustScore", 0.0))
    metrics = quality.get("metrics", {}) if isinstance(quality, dict) else {}
    source_count = int(metrics.get("sourceCount", 0) or 0)
    words = len(final_answer.split())

    changes: dict[str, Any] = {
        "reasoning": [],
        "before": {
            "model_name": tuning.model_name,
            "token_mode": tuning.token_mode,
            "max_sources": tuning.max_sources,
            "max_terms": tuning.max_terms,
            "max_hits_per_term": tuning.max_hits_per_term,
            "min_relevance": tuning.min_relevance,
            "parallel_agents": tuning.parallel_agents,
        },
    }

    if overall < 72 or trust < 62:
        tuning.token_mode = "max-quality"
        tuning.max_sources = min(14, tuning.max_sources + 2)
        tuning.max_terms = min(14, tuning.max_terms + 1)
        tuning.max_hits_per_term = min(10, tuning.max_hits_per_term + 1)
        tuning.min_relevance = max(0.16, tuning.min_relevance - 0.02)
        tuning.parallel_agents = False
        changes["reasoning"].append("Quality or trust was below target; increased evidence depth and quality mode.")

    if words > 1100:
        tuning.token_mode = "lean"
        tuning.max_sources = max(6, tuning.max_sources - 1)
        tuning.max_terms = max(6, tuning.max_terms - 1)
        tuning.max_hits_per_term = max(5, tuning.max_hits_per_term - 1)
        tuning.min_relevance = min(0.30, tuning.min_relevance + 0.02)
        changes["reasoning"].append("Report length exceeded budget; applied lean token strategy to reduce token count and cost.")

    if source_count < 5:
        tuning.max_sources = min(14, tuning.max_sources + 2)
        tuning.max_hits_per_term = min(10, tuning.max_hits_per_term + 1)
        changes["reasoning"].append("Source coverage was low; expanded retrieval breadth for better evidence quality.")

    fastest_model = _pick_fastest_model(local_bench)
    if fastest_model and overall >= 72 and trust >= 62 and fastest_model != tuning.model_name:
        tuning.model_name = fastest_model
        changes["reasoning"].append("Quality was stable; switched to faster local model to lower research runtime cost.")

    if not changes["reasoning"]:
        changes["reasoning"].append("No major issues detected; kept current tuning for consistency.")

    changes["after"] = {
        "model_name": tuning.model_name,
        "token_mode": tuning.token_mode,
        "max_sources": tuning.max_sources,
        "max_terms": tuning.max_terms,
        "max_hits_per_term": tuning.max_hits_per_term,
        "min_relevance": tuning.min_relevance,
        "parallel_agents": tuning.parallel_agents,
    }
    return changes


def _append_improvement_log(artifacts: RunArtifacts, improvements_path: Path) -> None:
    improvements_path.parent.mkdir(parents=True, exist_ok=True)

    quality_metrics = artifacts.quality.get("metrics", {}) if isinstance(artifacts.quality, dict) else {}
    report_text = artifacts.report_path.read_text(encoding="utf-8")
    report_words = len(report_text.split())
    est_tokens = _estimate_tokens(report_text)

    local_bench_rows = []
    for row in artifacts.local_bench.get("benchmarks", []) if isinstance(artifacts.local_bench, dict) else []:
        if not isinstance(row, dict):
            continue
        if row.get("error"):
            local_bench_rows.append(f"- {row.get('model', 'unknown')}: error={row.get('error')}")
        else:
            local_bench_rows.append(
                f"- {row.get('model', 'unknown')}: latency={row.get('latencySeconds', 0)}s, "
                f"tokensPerSecond={row.get('tokensPerSecond', 0)}"
            )

    section = (
        f"\n## Run {artifacts.run_index:02d} - {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"- Topic: {artifacts.topic}\n"
        f"- Report: {artifacts.report_path}\n"
        f"- Benchmark JSON: {artifacts.benchmark_path}\n"
        f"- Overall Score: {artifacts.quality.get('overallScore', 0.0)}\n"
        f"- Trust Score: {artifacts.quality.get('trustScore', 0.0)}\n"
        f"- Source Count: {quality_metrics.get('sourceCount', 0)}\n"
        f"- Claim Verification Rate: {quality_metrics.get('claimVerificationRate', 0.0)}\n"
        f"- Approx Report Words: {report_words}\n"
        f"- Approx Token Count: {est_tokens}\n"
        f"- Estimated Generation Cost (local-only): $0 API spend\n\n"
        "### Local Model Throughput\n"
        f"{chr(10).join(local_bench_rows) if local_bench_rows else '- unavailable'}\n\n"
        "### Implemented Improvement Before Next Run\n"
        f"- Reasoning: {' | '.join(artifacts.tuning_applied.get('reasoning', []))}\n"
        f"- Before: {json.dumps(artifacts.tuning_applied.get('before', {}), sort_keys=True)}\n"
        f"- After: {json.dumps(artifacts.tuning_applied.get('after', {}), sort_keys=True)}\n"
    )

    if not improvements_path.exists():
        header = (
            "# Local Iterative Improvements Log\n\n"
            "This log is appended after each random-topic local report run.\n"
            "It tracks benchmark outcomes and the concrete tuning change implemented before the next topic.\n"
        )
        improvements_path.write_text(header + section, encoding="utf-8")
    else:
        with improvements_path.open("a", encoding="utf-8") as f:
            f.write(section)


async def _run_pipeline_for_topic(topic: str, tuning: TuningState) -> tuple[str, dict[str, Any], str]:
    _apply_runtime_env(tuning)

    provider = LocalPipelineModelProvider(tuning.model_name)
    service = PipelineService(
        storage_path=SERVICE_DIR / ".data" / "pipeline-sessions-random-topic.json",
        model_provider=provider,
    )

    session_id = service.start(topic, tenant_id="random-topic-report")
    async for _event in service.stream_events(session_id, tenant_id="random-topic-report"):
        pass

    final_answer = service.get_final_report(session_id, tenant_id="random-topic-report")
    quality = service.get_quality_report(session_id, tenant_id="random-topic-report")
    return final_answer, quality, session_id


async def run_iterations(total_runs: int, seed: int | None) -> list[RunArtifacts]:
    if seed is not None:
        random.seed(seed)

    used_topics: set[str] = set()
    tuning = TuningState()
    artifacts: list[RunArtifacts] = []
    previous_benchmark_path: Path | None = None

    bench_dir = SERVICE_DIR / ".data" / "benchmarks"
    bench_dir.mkdir(parents=True, exist_ok=True)
    improvements_path = SERVICE_DIR / ".data" / "reports" / "local-improvements-log.md"

    for idx in range(1, total_runs + 1):
        topic = await _fetch_random_topic(used_topics)
        final_answer, quality, session_id = await _run_pipeline_for_topic(topic, tuning)
        report_path = _save_report(topic, session_id, final_answer, quality, idx)

        local_bench = await _benchmark_local_models()
        suite = run_benchmark_suite(cases=extended_benchmark_suite(), suite_name="extended")

        benchmark_output = bench_dir / f"benchmark-random-topic-run{idx:02d}-{_now_stamp()}.json"
        benchmark_path = Path(save_benchmark_report(suite, str(benchmark_output)))

        alerts: list[dict[str, Any]] = []
        if previous_benchmark_path is not None:
            comparisons = compare_with_previous_report(suite, str(previous_benchmark_path))
            alerts = [
                {
                    "metric": alert.metric,
                    "previous": alert.previous,
                    "current": alert.current,
                    "delta": alert.delta,
                    "threshold": alert.threshold,
                    "severity": alert.severity,
                    "message": alert.message,
                }
                for alert in comparisons
            ]

        tuning_applied = _tune_for_next_run(tuning, quality, final_answer, local_bench)
        if alerts:
            tuning_applied.setdefault("regressionAlerts", alerts)

        run_artifact = RunArtifacts(
            run_index=idx,
            topic=topic,
            report_path=report_path,
            benchmark_path=benchmark_path,
            quality=quality,
            local_bench=local_bench,
            tuning_applied=tuning_applied,
        )
        _append_improvement_log(run_artifact, improvements_path)
        artifacts.append(run_artifact)
        previous_benchmark_path = benchmark_path

        print(
            json.dumps(
                {
                    "run": idx,
                    "topic": topic,
                    "sessionId": session_id,
                    "reportPath": str(report_path),
                    "benchmarkPath": str(benchmark_path),
                    "overallScore": quality.get("overallScore", 0.0),
                    "trustScore": quality.get("trustScore", 0.0),
                    "nextTuning": tuning_applied.get("after", {}),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    return artifacts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run fully local random-topic reports sequentially with benchmarking and iterative tuning."
    )
    parser.add_argument("--runs", type=int, default=10, help="Number of sequential random-topic runs.")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed for reproducibility.")
    args = parser.parse_args()

    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")

    asyncio.run(run_iterations(total_runs=args.runs, seed=args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
