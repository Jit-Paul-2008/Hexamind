from __future__ import annotations

from dataclasses import dataclass

from quality import analyze_pipeline_quality
from research import ResearchContext, ResearchSource
from workflow import build_workflow_profile


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    query: str
    domain: str
    baseline_answer: str
    candidate_answer: str
    research: ResearchContext


@dataclass(frozen=True)
class BenchmarkCaseResult:
    case_id: str
    baseline_score: float
    candidate_score: float
    winner: str
    score_delta: float
    candidate_passing: bool
    baseline_passing: bool


@dataclass(frozen=True)
class BenchmarkSuiteReport:
    suite_name: str
    cases: tuple[BenchmarkCaseResult, ...]
    win_rate: float
    average_score_delta: float
    passing_rate: float


def default_benchmark_suite() -> tuple[BenchmarkCase, ...]:
    return (
        _make_case(
            case_id="policy-audit",
            query="How should we revise the policy rollout plan for a regulated deployment?",
            domain="policy",
            baseline_answer="## Summary\n- The plan should be improved.\n",
            candidate_answer=(
                "## Executive Summary\n"
                "- A staged rollout with explicit compliance checkpoints reduces policy risk and preserves auditability [S1][S2][S3][S4]\n"
                "- The strongest sources all warn against rapid rollout without oversight, so the launch should remain phased [S1][S2][S3][S4]\n"
                "## Decision Recommendation\n"
                "- Require source-backed checkpoints before expansion and document the evidence basis in the launch review [S1][S2][S3][S4]\n"
                "- Escalate only after policy owners confirm the rollout criteria and the review log is complete [S1][S2][S3][S4]\n"
                "## Source Inventory\n"
                "- S1: https://example.gov/policy\n"
            ),
            sources=(
                ResearchSource(
                    id="S1",
                    title="Policy guidance",
                    url="https://example.gov/policy",
                    domain="example.gov",
                    snippet="",
                    excerpt="Official guidance recommends staged rollout with compliance checkpoints.",
                    authority="primary",
                    credibility_score=0.96,
                    recency_score=1.0,
                    discovery_pass="official",
                ),
                ResearchSource(
                    id="S2",
                    title="Independent review",
                    url="https://example.org/review",
                    domain="example.org",
                    snippet="",
                    excerpt="Independent review warns against rapid rollout without oversight.",
                    authority="high",
                    credibility_score=0.84,
                    recency_score=0.82,
                    discovery_pass="evidence",
                ),
                ResearchSource(
                    id="S3",
                    title="Academic memo",
                    url="https://example.edu/memo",
                    domain="example.edu",
                    snippet="",
                    excerpt="Academic memo supports phased rollout and explicit review checkpoints.",
                    authority="primary",
                    credibility_score=0.91,
                    recency_score=0.87,
                    discovery_pass="methodology",
                ),
                ResearchSource(
                    id="S4",
                    title="Industry brief",
                    url="https://example.com/brief",
                    domain="example.com",
                    snippet="",
                    excerpt="Industry brief recommends audit logging and staged escalation.",
                    authority="secondary",
                    credibility_score=0.73,
                    recency_score=0.84,
                    discovery_pass="comparison",
                ),
            ),
        ),
        _make_case(
            case_id="engineering-latency",
            query="How can we reduce backend latency without weakening reliability?",
            domain="engineering",
            baseline_answer="## Summary\n- Reduce latency carefully.\n",
            candidate_answer=(
                "## Executive Summary\n"
                "- Cache hot retrieval paths and reuse evidence packs to preserve bounded prompt windows and reduce repeated retrieval work [S1][S2][S3][S4]\n"
                "## Analytical Breakdown\n"
                "### Claim Graph\n"
                "- C1: bounded context and fail-open recovery protect reliability when snapshots are reused [S1][S2][S3][S4]\n"
                "- C2: prompt compression and reusable snapshots are the recommended implementation path [S1][S2][S3][S4]\n"
                "## Confidence and Open Questions\n"
                "- Confidence is moderate because the sources agree on the tradeoff and the evidence remains source-diverse [S1][S2][S3][S4]\n"
            ),
            sources=(
                ResearchSource(
                    id="S1",
                    title="Ops note",
                    url="https://example.net/ops",
                    domain="example.net",
                    snippet="",
                    excerpt="Operational notes recommend caching and bounded prompt windows.",
                    authority="secondary",
                    credibility_score=0.74,
                    recency_score=0.9,
                    discovery_pass="recent",
                ),
                ResearchSource(
                    id="S2",
                    title="Benchmark note",
                    url="https://example.com/benchmark",
                    domain="example.com",
                    snippet="",
                    excerpt="Benchmark results show latency gains when retrieval results are reused.",
                    authority="high",
                    credibility_score=0.81,
                    recency_score=0.86,
                    discovery_pass="benchmark",
                ),
                ResearchSource(
                    id="S3",
                    title="Reliability note",
                    url="https://example.edu/reliability",
                    domain="example.edu",
                    snippet="",
                    excerpt="Reliability notes recommend bounded context and fail-open recovery paths.",
                    authority="primary",
                    credibility_score=0.89,
                    recency_score=0.83,
                    discovery_pass="methodology",
                ),
                ResearchSource(
                    id="S4",
                    title="Systems brief",
                    url="https://example.org/systems",
                    domain="example.org",
                    snippet="",
                    excerpt="Systems brief highlights prompt compression and reusable snapshots.",
                    authority="high",
                    credibility_score=0.8,
                    recency_score=0.88,
                    discovery_pass="comparison",
                ),
            ),
        ),
        _make_case(
            case_id="operations-launch",
            query="What is the safest way to launch a new operating workflow?",
            domain="operations",
            baseline_answer="## Answer\n- Launch it and monitor it.\n",
            candidate_answer=(
                "## Executive Summary\n"
                "- Launch with canary gates, rollback criteria, audit logging, and prompt registry tracking [S1][S2][S3][S4]\n"
                "## Action Plan\n"
                "- Measure queue wait, defect rate, fallback frequency, and registry version drift before broad rollout [S1][S2][S3][S4]\n"
                "## Source Inventory\n"
                "- S3: https://example.edu/runbooks\n"
            ),
            sources=(
                ResearchSource(
                    id="S1",
                    title="Runbook",
                    url="https://example.gov/runbook",
                    domain="example.gov",
                    snippet="",
                    excerpt="Runbook recommends canary deployment and explicit rollback thresholds.",
                    authority="primary",
                    credibility_score=0.95,
                    recency_score=0.98,
                    discovery_pass="official",
                ),
                ResearchSource(
                    id="S2",
                    title="Safety review",
                    url="https://example.org/safety",
                    domain="example.org",
                    snippet="",
                    excerpt="Safety review argues for audit logs and small rollout scopes.",
                    authority="high",
                    credibility_score=0.82,
                    recency_score=0.86,
                    discovery_pass="evidence",
                ),
                ResearchSource(
                    id="S3",
                    title="Operational guide",
                    url="https://example.edu/runbooks",
                    domain="example.edu",
                    snippet="",
                    excerpt="Operational guide tracks queue delay, fallback behavior, and incident response.",
                    authority="primary",
                    credibility_score=0.93,
                    recency_score=0.9,
                    discovery_pass="methodology",
                ),
                ResearchSource(
                    id="S4",
                    title="Release memo",
                    url="https://example.com/release",
                    domain="example.com",
                    snippet="",
                    excerpt="Release memo tracks prompt versions, audit logs, and rollback criteria.",
                    authority="secondary",
                    credibility_score=0.77,
                    recency_score=0.85,
                    discovery_pass="recent",
                ),
            ),
        ),
    )


def evaluate_benchmark_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    baseline_report = analyze_pipeline_quality(
        query=case.query,
        assembled={"baseline": case.baseline_answer},
        final_answer=case.baseline_answer,
        research=case.research,
    )
    candidate_report = analyze_pipeline_quality(
        query=case.query,
        assembled={"candidate": case.candidate_answer},
        final_answer=case.candidate_answer,
        research=case.research,
    )

    baseline_score = float(baseline_report["overallScore"])
    candidate_score = float(candidate_report["overallScore"])
    winner = "candidate" if candidate_score >= baseline_score else "baseline"

    return BenchmarkCaseResult(
        case_id=case.id,
        baseline_score=round(baseline_score, 2),
        candidate_score=round(candidate_score, 2),
        winner=winner,
        score_delta=round(candidate_score - baseline_score, 2),
        candidate_passing=bool(candidate_report["passing"]),
        baseline_passing=bool(baseline_report["passing"]),
    )


def run_benchmark_suite(cases: tuple[BenchmarkCase, ...] | None = None, suite_name: str = "default") -> BenchmarkSuiteReport:
    selected_cases = cases or default_benchmark_suite()
    results = tuple(evaluate_benchmark_case(case) for case in selected_cases)
    wins = sum(1 for result in results if result.winner == "candidate")
    win_rate = wins / len(results) if results else 0.0
    average_score_delta = sum(result.score_delta for result in results) / len(results) if results else 0.0
    passing_rate = sum(1 for result in results if result.candidate_passing) / len(results) if results else 0.0

    return BenchmarkSuiteReport(
        suite_name=suite_name,
        cases=results,
        win_rate=round(win_rate, 3),
        average_score_delta=round(average_score_delta, 2),
        passing_rate=round(passing_rate, 3),
    )


def _make_case(
    *,
    case_id: str,
    query: str,
    domain: str,
    baseline_answer: str,
    candidate_answer: str,
    sources: tuple[ResearchSource, ...],
) -> BenchmarkCase:
    return BenchmarkCase(
        id=case_id,
        query=query,
        domain=domain,
        baseline_answer=baseline_answer,
        candidate_answer=candidate_answer,
        research=ResearchContext(
            query=query,
            workflow_profile=build_workflow_profile(query),
            search_terms=(domain, query.split()[0].lower()),
            search_passes=("official", "evidence"),
            sources=sources,
            generated_at=0.0,
            contradictions=tuple(),
        ),
    )