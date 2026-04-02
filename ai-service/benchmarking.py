from __future__ import annotations

from dataclasses import dataclass
import json
import time
from pathlib import Path

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
    expected_winner: str = "candidate"  # Expected outcome for regression testing


@dataclass(frozen=True)
class BenchmarkCaseResult:
    case_id: str
    baseline_score: float
    candidate_score: float
    baseline_trust: float
    candidate_trust: float
    winner: str
    score_delta: float
    trust_delta: float
    candidate_passing: bool
    baseline_passing: bool
    regression_detected: bool = False


@dataclass(frozen=True)
class BenchmarkSuiteReport:
    suite_name: str
    cases: tuple[BenchmarkCaseResult, ...]
    win_rate: float
    average_score_delta: float
    average_trust_delta: float
    passing_rate: float
    regression_count: int
    domain_breakdown: dict


@dataclass(frozen=True)
class RegressionAlert:
    metric: str
    previous: float
    current: float
    delta: float
    threshold: float
    severity: str
    message: str


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
    baseline_trust = float(baseline_report.get("trustScore", 0))
    candidate_trust = float(candidate_report.get("trustScore", 0))
    winner = "candidate" if candidate_score >= baseline_score else "baseline"
    regression_detected = case.expected_winner == "candidate" and winner == "baseline"

    benchmark_pass = bool(candidate_report["passing"]) or (
        candidate_score >= baseline_score + 12.0 and candidate_trust >= baseline_trust
    )

    return BenchmarkCaseResult(
        case_id=case.id,
        baseline_score=round(baseline_score, 2),
        candidate_score=round(candidate_score, 2),
        baseline_trust=round(baseline_trust, 2),
        candidate_trust=round(candidate_trust, 2),
        winner=winner,
        score_delta=round(candidate_score - baseline_score, 2),
        trust_delta=round(candidate_trust - baseline_trust, 2),
        candidate_passing=benchmark_pass,
        baseline_passing=bool(baseline_report["passing"]),
        regression_detected=regression_detected,
    )


def run_benchmark_suite(cases: tuple[BenchmarkCase, ...] | None = None, suite_name: str = "default") -> BenchmarkSuiteReport:
    selected_cases = cases or default_benchmark_suite()
    results = tuple(evaluate_benchmark_case(case) for case in selected_cases)
    wins = sum(1 for result in results if result.winner == "candidate")
    win_rate = wins / len(results) if results else 0.0
    average_score_delta = sum(result.score_delta for result in results) / len(results) if results else 0.0
    average_trust_delta = sum(result.trust_delta for result in results) / len(results) if results else 0.0
    passing_rate = sum(1 for result in results if result.candidate_passing) / len(results) if results else 0.0
    regression_count = sum(1 for result in results if result.regression_detected)
    
    # Domain breakdown
    domain_stats: dict = {}
    for case, result in zip(selected_cases, results):
        domain = case.domain
        if domain not in domain_stats:
            domain_stats[domain] = {"wins": 0, "total": 0, "avg_delta": 0.0}
        domain_stats[domain]["total"] += 1
        if result.winner == "candidate":
            domain_stats[domain]["wins"] += 1
        domain_stats[domain]["avg_delta"] += result.score_delta
    
    for domain in domain_stats:
        total = domain_stats[domain]["total"]
        domain_stats[domain]["win_rate"] = round(domain_stats[domain]["wins"] / total, 3) if total > 0 else 0.0
        domain_stats[domain]["avg_delta"] = round(domain_stats[domain]["avg_delta"] / total, 2) if total > 0 else 0.0

    return BenchmarkSuiteReport(
        suite_name=suite_name,
        cases=results,
        win_rate=round(win_rate, 3),
        average_score_delta=round(average_score_delta, 2),
        average_trust_delta=round(average_trust_delta, 2),
        passing_rate=round(passing_rate, 3),
        regression_count=regression_count,
        domain_breakdown=domain_stats,
    )


def _make_case(
    *,
    case_id: str,
    query: str,
    domain: str,
    baseline_answer: str,
    candidate_answer: str,
    sources: tuple[ResearchSource, ...],
    expected_winner: str = "candidate",
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
        expected_winner=expected_winner,
    )


# =============================================================================
# BEAST WORKFLOW: Extended Benchmark Suite
# =============================================================================

def extended_benchmark_suite() -> tuple[BenchmarkCase, ...]:
    """Extended benchmark suite with diverse test cases across domains."""
    return default_benchmark_suite() + (
        # Comparison benchmark
        _make_case(
            case_id="comparison-databases",
            query="Should I use PostgreSQL or MySQL for a new web application?",
            domain="comparison",
            baseline_answer="## Summary\n- Both are good databases. PostgreSQL is more feature-rich.\n",
            candidate_answer=(
                "## Executive Summary\n"
                "- PostgreSQL offers superior JSON support, advanced indexing, and better ACID compliance for complex applications [S1][S2][S3][S4]\n"
                "- MySQL provides faster simple queries and wider hosting support for basic CRUD applications [S2][S3]\n"
                "## Claim-to-Citation Map\n"
                "- C1: PostgreSQL JSON support is production-grade [S1]\n"
                "- C2: MySQL has broader hosting availability [S2][S3]\n"
                "- C3: PostgreSQL handles complex queries better [S1][S4]\n"
                "## Contradictions\n"
                "- Performance benchmarks differ: MySQL faster for simple reads [S2], PostgreSQL faster for complex joins [S4]\n"
                "## Uncertainty and Limitations\n"
                "- Performance depends on specific workload patterns and query complexity\n"
                "- Both databases evolve rapidly; version-specific features should be verified\n"
            ),
            sources=(
                ResearchSource(id="S1", title="PostgreSQL Docs", url="https://example.gov/postgres",
                    domain="example.gov", snippet="", excerpt="PostgreSQL provides advanced JSON support and complex indexing.",
                    authority="primary", credibility_score=0.95, recency_score=0.95, discovery_pass="official"),
                ResearchSource(id="S2", title="Database Comparison", url="https://example.edu/compare",
                    domain="example.edu", snippet="", excerpt="MySQL offers faster simple queries, PostgreSQL better for complex operations.",
                    authority="primary", credibility_score=0.9, recency_score=0.88, discovery_pass="evidence"),
                ResearchSource(id="S3", title="Hosting Analysis", url="https://example.com/hosting",
                    domain="example.com", snippet="", excerpt="MySQL has broader hosting support and lower resource requirements.",
                    authority="secondary", credibility_score=0.75, recency_score=0.82, discovery_pass="recent"),
                ResearchSource(id="S4", title="Performance Study", url="https://example.org/perf",
                    domain="example.org", snippet="", excerpt="PostgreSQL outperforms on complex joins and analytical queries.",
                    authority="high", credibility_score=0.85, recency_score=0.9, discovery_pass="benchmark"),
            ),
        ),
        
        # Technical implementation benchmark
        _make_case(
            case_id="technical-auth",
            query="How do I implement JWT authentication in a Node.js Express application?",
            domain="technical",
            baseline_answer="## Implementation\n- Use jsonwebtoken package to create and verify tokens.\n",
            candidate_answer=(
                "## Executive Summary\n"
                "- JWT authentication requires token generation on login, middleware validation, and secure secret management [S1][S2][S3][S4]\n"
                "## Implementation Steps\n"
                "1. Install dependencies: `npm install jsonwebtoken bcryptjs` [S1][S2]\n"
                "2. Create auth middleware that extracts and verifies JWT from Authorization header [S1][S3]\n"
                "3. Use secure environment variables for JWT_SECRET with minimum 256-bit entropy [S2][S4]\n"
                "4. Set appropriate token expiration (15-30 minutes for access tokens) [S3][S4]\n"
                "## Claim-to-Citation Map\n"
                "- C1: jsonwebtoken is the standard library for Node.js JWT [S1][S2]\n"
                "- C2: 256-bit secrets are minimum recommended [S2][S4]\n"
                "- C3: Short expiration reduces token theft risk [S3][S4]\n"
                "## Security Considerations\n"
                "- Store refresh tokens securely with proper rotation [S3]\n"
                "- Never expose secrets in client-side code [S2][S4]\n"
                "## Uncertainty and Limitations\n"
                "- Implementation details vary by Express version and project structure\n"
            ),
            sources=(
                ResearchSource(id="S1", title="Express Auth Guide", url="https://example.gov/express",
                    domain="example.gov", snippet="", excerpt="Express JWT authentication uses jsonwebtoken library with middleware pattern.",
                    authority="primary", credibility_score=0.92, recency_score=0.9, discovery_pass="official"),
                ResearchSource(id="S2", title="Security Best Practices", url="https://example.edu/security",
                    domain="example.edu", snippet="", excerpt="JWT secrets should use minimum 256-bit entropy and environment variables.",
                    authority="primary", credibility_score=0.94, recency_score=0.88, discovery_pass="evidence"),
                ResearchSource(id="S3", title="Token Management", url="https://example.org/tokens",
                    domain="example.org", snippet="", excerpt="Access tokens should expire in 15-30 minutes with refresh token rotation.",
                    authority="high", credibility_score=0.86, recency_score=0.85, discovery_pass="methodology"),
                ResearchSource(id="S4", title="Auth Implementation", url="https://example.com/impl",
                    domain="example.com", snippet="", excerpt="Production JWT requires secure secrets and short expiration windows.",
                    authority="secondary", credibility_score=0.78, recency_score=0.9, discovery_pass="recent"),
            ),
        ),
        
        # Forecast/prediction benchmark
        _make_case(
            case_id="forecast-ai-jobs",
            query="How will AI affect software engineering jobs in the next 5 years?",
            domain="forecast",
            baseline_answer="## Prediction\n- AI will change some jobs but create new opportunities.\n",
            candidate_answer=(
                "## Executive Summary\n"
                "- AI will augment rather than replace most software engineering roles, with 60% probability of net job growth in specialized areas [S1][S2][S3][S4]\n"
                "## Scenario Analysis\n"
                "### Most Likely (60%): Augmentation-Led Growth\n"
                "- AI tools boost productivity, demand for AI-skilled engineers rises [S1][S2]\n"
                "- Trigger: Continued AI capability growth without AGI breakthrough\n"
                "### Moderate (25%): Structural Shift\n"
                "- Junior roles decline, senior/specialized roles increase [S2][S3]\n"
                "- Trigger: AI achieves reliable autonomous coding for routine tasks\n"
                "### Pessimistic (15%): Significant Displacement\n"
                "- Major job losses in routine development [S3][S4]\n"
                "- Trigger: AGI-level systems emerge sooner than expected\n"
                "## Claim-to-Citation Map\n"
                "- C1: Productivity augmentation is most likely path [S1][S2]\n"
                "- C2: Specialized AI roles will grow [S1][S3]\n"
                "- C3: Junior role displacement is possible [S3][S4]\n"
                "## Contradictions\n"
                "- Sources disagree on timeline: S1 predicts 10+ years to major impact, S4 suggests 3-5 years\n"
                "## Uncertainty and Limitations\n"
                "- Predictions depend heavily on unpredictable AI research breakthroughs\n"
                "- Economic conditions and regulation will significantly affect outcomes\n"
            ),
            sources=(
                ResearchSource(id="S1", title="Labor Market Analysis", url="https://example.gov/labor",
                    domain="example.gov", snippet="", excerpt="AI augmentation expected to boost software engineering productivity and demand.",
                    authority="primary", credibility_score=0.92, recency_score=0.95, discovery_pass="official"),
                ResearchSource(id="S2", title="Tech Employment Study", url="https://example.edu/employment",
                    domain="example.edu", snippet="", excerpt="Specialized AI engineering roles projected to grow significantly.",
                    authority="primary", credibility_score=0.88, recency_score=0.9, discovery_pass="evidence"),
                ResearchSource(id="S3", title="Industry Forecast", url="https://example.org/forecast",
                    domain="example.org", snippet="", excerpt="Junior developer roles may decline as AI handles routine tasks.",
                    authority="high", credibility_score=0.82, recency_score=0.88, discovery_pass="recent"),
                ResearchSource(id="S4", title="Disruption Analysis", url="https://example.com/disruption",
                    domain="example.com", snippet="", excerpt="Rapid AI advancement could significantly disrupt programming jobs within 3-5 years.",
                    authority="secondary", credibility_score=0.72, recency_score=0.92, discovery_pass="comparison"),
            ),
        ),
        
        # Medical/health benchmark
        _make_case(
            case_id="medical-sleep",
            query="What are the evidence-based approaches to improving sleep quality?",
            domain="medical",
            baseline_answer="## Recommendations\n- Get 7-9 hours of sleep and avoid screens before bed.\n",
            candidate_answer=(
                "## Executive Summary\n"
                "- Evidence strongly supports sleep hygiene practices, cognitive behavioral therapy for insomnia (CBT-I), and consistent sleep schedules [S1][S2][S3][S4]\n"
                "## Evidence-Based Interventions\n"
                "### First-Line: CBT-I (Strong Evidence)\n"
                "- 70-80% response rate, effects persist after treatment ends [S1][S2]\n"
                "### Sleep Hygiene (Moderate Evidence)\n"
                "- Consistent sleep/wake times, dark/cool environment, limited caffeine [S1][S3]\n"
                "### Light Exposure (Moderate Evidence)\n"
                "- Morning bright light, evening blue light reduction [S2][S4]\n"
                "## Claim-to-Citation Map\n"
                "- C1: CBT-I is most effective non-pharmacological intervention [S1][S2]\n"
                "- C2: Consistent timing improves circadian alignment [S1][S3]\n"
                "- C3: Light exposure affects melatonin production [S2][S4]\n"
                "## Contradictions\n"
                "- S3 suggests melatonin supplements effective, S4 finds limited evidence for supplements\n"
                "## Uncertainty and Limitations\n"
                "- Individual responses vary significantly\n"
                "- Underlying conditions may require medical evaluation\n"
                "- This is general information, not medical advice\n"
            ),
            sources=(
                ResearchSource(id="S1", title="Sleep Medicine Guidelines", url="https://example.gov/sleep",
                    domain="example.gov", snippet="", excerpt="CBT-I recommended as first-line treatment with 70-80% response rate.",
                    authority="primary", credibility_score=0.96, recency_score=0.92, discovery_pass="official"),
                ResearchSource(id="S2", title="Sleep Research Review", url="https://example.edu/sleep-research",
                    domain="example.edu", snippet="", excerpt="Light exposure and CBT-I show strongest evidence for sleep improvement.",
                    authority="primary", credibility_score=0.94, recency_score=0.88, discovery_pass="evidence"),
                ResearchSource(id="S3", title="Clinical Practice", url="https://example.org/clinical",
                    domain="example.org", snippet="", excerpt="Sleep hygiene and melatonin supplements can improve sleep quality.",
                    authority="high", credibility_score=0.85, recency_score=0.85, discovery_pass="methodology"),
                ResearchSource(id="S4", title="Supplement Review", url="https://example.com/supplements",
                    domain="example.com", snippet="", excerpt="Evidence for sleep supplements is limited; light therapy more effective.",
                    authority="secondary", credibility_score=0.75, recency_score=0.9, discovery_pass="comparison"),
            ),
        ),
        
        # Decision/recommendation benchmark
        _make_case(
            case_id="decision-cloud",
            query="Should our startup use AWS, GCP, or Azure for our cloud infrastructure?",
            domain="decision",
            baseline_answer="## Recommendation\n- AWS is the market leader and a safe choice.\n",
            candidate_answer=(
                "## Executive Summary\n"
                "- Recommended: Start with AWS or GCP based on team expertise; both offer startup credits and broad service coverage [S1][S2][S3][S4]\n"
                "## Decision Framework\n"
                "### Choose AWS If:\n"
                "- Team has AWS experience or certifications [S1][S2]\n"
                "- Need broadest service catalog and enterprise features [S1]\n"
                "### Choose GCP If:\n"
                "- Heavy data/ML workloads planned [S2][S3]\n"
                "- Team prefers Kubernetes-native approach [S3]\n"
                "### Choose Azure If:\n"
                "- Microsoft ecosystem integration required [S4]\n"
                "- Enterprise sales motion with Microsoft partnerships [S4]\n"
                "## Claim-to-Citation Map\n"
                "- C1: AWS has broadest service catalog [S1][S2]\n"
                "- C2: GCP leads in data/ML tooling [S2][S3]\n"
                "- C3: Azure best for Microsoft integration [S4]\n"
                "## Cost Considerations\n"
                "- All providers offer $100K+ startup credits [S1][S2][S3]\n"
                "- Egress costs significant for all; plan data architecture early [S2][S4]\n"
                "## Uncertainty and Limitations\n"
                "- Pricing and features change frequently; verify current offers\n"
                "- Lock-in risk exists with all providers\n"
            ),
            sources=(
                ResearchSource(id="S1", title="Cloud Comparison", url="https://example.gov/cloud",
                    domain="example.gov", snippet="", excerpt="AWS leads in service breadth with startup credits available.",
                    authority="primary", credibility_score=0.9, recency_score=0.92, discovery_pass="official"),
                ResearchSource(id="S2", title="Startup Cloud Guide", url="https://example.edu/startups",
                    domain="example.edu", snippet="", excerpt="GCP offers strong data and ML capabilities; all providers have startup programs.",
                    authority="primary", credibility_score=0.88, recency_score=0.9, discovery_pass="evidence"),
                ResearchSource(id="S3", title="Kubernetes Analysis", url="https://example.org/k8s",
                    domain="example.org", snippet="", excerpt="GCP Kubernetes support most mature; Azure improving rapidly.",
                    authority="high", credibility_score=0.84, recency_score=0.88, discovery_pass="comparison"),
                ResearchSource(id="S4", title="Enterprise Cloud", url="https://example.com/enterprise",
                    domain="example.com", snippet="", excerpt="Azure best for Microsoft ecosystem; egress costs significant for all providers.",
                    authority="secondary", credibility_score=0.78, recency_score=0.85, discovery_pass="recent"),
            ),
        ),
    )


def save_benchmark_report(report: BenchmarkSuiteReport, output_path: str | None = None) -> str:
    target = Path(output_path) if output_path else Path(__file__).resolve().with_name(".data").joinpath("benchmark-latest.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "suiteName": report.suite_name,
        "generatedAt": time.time(),
        "winRate": report.win_rate,
        "averageScoreDelta": report.average_score_delta,
        "averageTrustDelta": report.average_trust_delta,
        "passingRate": report.passing_rate,
        "regressionCount": report.regression_count,
        "domainBreakdown": report.domain_breakdown,
        "cases": [
            {
                "caseId": case.case_id,
                "baselineScore": case.baseline_score,
                "candidateScore": case.candidate_score,
                "baselineTrust": case.baseline_trust,
                "candidateTrust": case.candidate_trust,
                "winner": case.winner,
                "scoreDelta": case.score_delta,
                "trustDelta": case.trust_delta,
                "candidatePassing": case.candidate_passing,
                "baselinePassing": case.baseline_passing,
                "regressionDetected": case.regression_detected,
            }
            for case in report.cases
        ],
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(target)


def compare_with_previous_report(
    current: BenchmarkSuiteReport,
    previous_report_path: str,
) -> list[RegressionAlert]:
    path = Path(previous_report_path)
    if not path.exists():
        return []

    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    alerts: list[RegressionAlert] = []
    checks = [
        ("winRate", float(previous.get("winRate", 0.0)), current.win_rate, 0.05),
        ("averageScoreDelta", float(previous.get("averageScoreDelta", 0.0)), current.average_score_delta, 3.0),
        ("averageTrustDelta", float(previous.get("averageTrustDelta", 0.0)), current.average_trust_delta, 3.0),
        ("passingRate", float(previous.get("passingRate", 0.0)), current.passing_rate, 0.10),
    ]
    for metric, prev, curr, threshold in checks:
        delta = curr - prev
        if delta >= -threshold:
            continue
        severity = "high" if abs(delta) >= threshold * 2 else "medium"
        alerts.append(
            RegressionAlert(
                metric=metric,
                previous=round(prev, 3),
                current=round(curr, 3),
                delta=round(delta, 3),
                threshold=threshold,
                severity=severity,
                message=f"{metric} regressed by {abs(delta):.3f} (threshold {threshold:.3f})",
            )
        )
    return alerts
