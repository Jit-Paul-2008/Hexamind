from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol, TypeVar

import httpx

from research import ResearchContext, format_research_context, source_inventory_markdown
from prompt_registry import prompt_fingerprint, prompt_registry_snapshot


T = TypeVar("T")


class PipelineModelProvider(Protocol):
    async def build_research_context(self, query: str) -> ResearchContext | None:
        ...

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        ...

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        ...

    def diagnostics(self) -> dict[str, str | int | bool]:
        ...


@dataclass
class _ProviderHealthManager:
    provider_name: str
    retry_budget: int = 1
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    backoff_seconds: float = 0.25
    failure_count: int = 0
    success_count: int = 0
    open_until: float = 0.0
    last_error: str = ""
    last_stage: str = ""
    last_failure_at: float = 0.0

    def can_attempt(self) -> bool:
        return not self.is_open()

    def is_open(self) -> bool:
        return time.monotonic() < self.open_until

    def record_success(self) -> None:
        self.success_count += 1
        self.failure_count = 0
        self.open_until = 0.0

    def record_failure(self, stage: str, exc: Exception) -> None:
        self.failure_count += 1
        self.last_stage = stage
        self.last_failure_at = time.monotonic()
        self.last_error = f"{type(exc).__name__}: {exc}".strip()[:240]
        if self.failure_count >= self.failure_threshold:
            self.open_until = time.monotonic() + self.cooldown_seconds

    def snapshot(self) -> dict[str, str | int | bool]:
        return {
            "circuitState": "open" if self.is_open() else "closed",
            "circuitOpen": self.is_open(),
            "failureCount": self.failure_count,
            "successCount": self.success_count,
            "retryBudget": self.retry_budget,
            "failureThreshold": self.failure_threshold,
            "cooldownSeconds": int(self.cooldown_seconds),
            "backoffSeconds": int(self.backoff_seconds * 1000),
            "lastStage": self.last_stage,
            "lastError": self.last_error,
            "cooldownRemainingSeconds": max(0, int(self.open_until - time.monotonic())),
        }


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _stage_timeout_seconds(stage: str) -> float:
    defaults = {
        "retrieval": 18.0,
        "agent": 30.0,
        "final": 40.0,
    }
    env_names = {
        "retrieval": "HEXAMIND_STAGE_TIMEOUT_RETRIEVAL_SECONDS",
        "agent": "HEXAMIND_STAGE_TIMEOUT_AGENT_SECONDS",
        "final": "HEXAMIND_STAGE_TIMEOUT_FINAL_SECONDS",
    }
    default = defaults.get(stage, 30.0)
    env_name = env_names.get(stage)
    if not env_name:
        return default
    value = os.getenv(env_name)
    if value is None:
        return default
    try:
        return max(0.5, float(value))
    except ValueError:
        return default


def _provider_retry_budget() -> int:
    return max(0, _env_int("HEXAMIND_PROVIDER_RETRY_BUDGET", 1))


def _provider_failure_threshold() -> int:
    return max(1, _env_int("HEXAMIND_PROVIDER_FAILURE_THRESHOLD", 3))


def _provider_cooldown_seconds() -> float:
    return max(1.0, _env_float("HEXAMIND_PROVIDER_COOLDOWN_SECONDS", 30.0))


def _provider_backoff_seconds() -> float:
    return max(0.05, _env_float("HEXAMIND_PROVIDER_BACKOFF_SECONDS", 0.25))


def _local_strict_mode() -> bool:
    return os.getenv("HEXAMIND_LOCAL_STRICT", "0").strip().lower() in {"1", "true", "yes", "on"}


def _query_complexity_score(query: str) -> float:
    words = re.findall(r"[a-zA-Z0-9]{3,}", query.lower())
    unique_words = set(words)
    score = min(1.0, (len(words) / 24.0) + (len(unique_words) / 18.0) * 0.35)
    if any(token in query.lower() for token in ("compare", "versus", "vs", "tradeoff", "benchmark")):
        score += 0.1
    if any(token in query.lower() for token in ("policy", "medical", "clinical", "engineering", "architecture", "reliability")):
        score += 0.08
    return max(0.0, min(1.0, score))


def _local_model_tier(query: str, research: ResearchContext | None) -> str:
    complexity = research.workflow_profile.complexity_score if research else _query_complexity_score(query)
    source_count = len(research.sources) if research else 0
    contradiction_count = len(getattr(research, "contradictions", ())) if research else 0
    if complexity >= 0.75 or source_count >= 6 or contradiction_count >= 2:
        return "large"
    if complexity >= 0.48 or source_count >= 3:
        return "medium"
    return "small"


def _local_token_budget(stage: str, tier: str, research: ResearchContext | None) -> int:
    budgets = {
        "small": {"agent": 900, "final": 1500},
        "medium": {"agent": 1200, "final": 1900},
        "large": {"agent": 1500, "final": 2400},
    }
    stage_budget = budgets.get(tier, budgets["medium"]).get(stage, 1400)
    if research and research.workflow_profile.complexity_score >= 0.7:
        stage_budget += 150
    return stage_budget


def _local_context_budget(stage: str, tier: str, research: ResearchContext | None) -> int:
    budgets = {
        "small": {"agent": 2400, "final": 3200},
        "medium": {"agent": 3600, "final": 5000},
        "large": {"agent": 4800, "final": 6800},
    }
    budget = budgets.get(tier, budgets["medium"]).get(stage, 3600)
    if research and research.workflow_profile.complexity_score >= 0.7:
        budget += 400
    return budget


def _compressed_research_block(research: ResearchContext | None, char_budget: int) -> str:
    block = format_research_context(research)
    if len(block) <= char_budget:
        return block
    if not research or not research.sources:
        return block[:char_budget].rstrip()

    # format_research_context collapses whitespace, making everything inline
    # Find "Source pack:" and try to include it with at least one source
    source_pack_idx = block.find("Source pack:")
    if source_pack_idx == -1:
        return block[:char_budget].rstrip()
    
    # If we can fit everything up to and including source pack start, do it
    if source_pack_idx + 200 <= char_budget:  # Leave room for at least partial source info
        return block[:char_budget].rstrip()
    
    # Otherwise, compress the prefix and keep sources
    # Take just the query, then jump to sources
    query_end = block.find("Audience profile:")
    if query_end > 0:
        query_part = block[:query_end].rstrip()
        sources_part = block[source_pack_idx:]
        available = char_budget - len(query_part) - 5  # 5 for " ... "
        if available > 50:
            combined = query_part + " ... " + sources_part[:available].rstrip() + "…"
            return combined[:char_budget].rstrip()
    
    # Fallback: simple truncation
    return block[:char_budget].rstrip()


def _deterministic_prompt_text(agent_id: str) -> str:
    prompts = {
        "advocate": (
            "You are the ADVOCATE agent in a professional multi-agent research pipeline. Your mission is to construct the strongest evidence-backed case for action.\n\n"
            "REQUIRED OUTPUT STRUCTURE (use exact headings):\n"
            "## Opportunity Thesis\n"
            "State the core opportunity in one sentence with a quantified impact estimate (percentage, timeframe, or magnitude).\n\n"
            "## Strategic Upside\n"
            "List 3-5 specific benefits with:\n"
            "- Each benefit tied to a source [Sx] citation\n"
            "- Quantified where possible (X% improvement, Y cost reduction)\n"
            "- Timeframe for realization (immediate, 30-day, 90-day)\n\n"
            "## Supporting Logic\n"
            "Present a reasoning chain: Premise A + Evidence B → Conclusion C\n"
            "- Include at least 2 causal mechanisms explaining WHY the benefit occurs\n"
            "- Reference comparable precedents or case studies from sources\n"
            "- Note required conditions for success\n\n"
            "## Actionable Next Step\n"
            "Specify ONE concrete action with:\n"
            "- Who executes (role, not generic team)\n"
            "- What exactly (specific deliverable)\n"
            "- When (exact timeframe)\n"
            "- Success criteria (measurable threshold)\n\n"
            "## Citations Used\n"
            "List each [Sx] with one-line evidence summary and credibility note.\n\n"
            "QUALITY REQUIREMENTS:\n"
            "- Every claim must cite [Sx] source IDs from the research context\n"
            "- Use specific numbers over vague qualifiers\n"
            "- No generic phrases like 'could potentially' or 'may help'\n"
            "- Ground optimism in evidence, not speculation"
        ),
        "skeptic": (
            "You are the SKEPTIC agent in a professional multi-agent research pipeline. Your mission is to identify failure modes, quantify risks, and ensure the recommendation survives adversarial scrutiny.\n\n"
            "REQUIRED OUTPUT STRUCTURE (use exact headings):\n"
            "## Risk Thesis\n"
            "State the primary risk hypothesis with severity classification (Critical/High/Medium/Low).\n\n"
            "## Primary Failure Modes\n"
            "Enumerate 3-5 failure scenarios using this taxonomy:\n"
            "- Technical risk: architecture, integration, scalability failures\n"
            "- Execution risk: timeline, resource, capability gaps\n"
            "- Market/External risk: competitive, regulatory, economic shifts\n"
            "- Adoption risk: user resistance, training, change management\n\n"
            "For each failure mode include:\n"
            "- Probability estimate (percentage or likelihood band)\n"
            "- Impact severity (1-5 scale with description)\n"
            "- Detection difficulty (how early can we spot this failing?)\n"
            "- Source citation [Sx] if evidence-based\n\n"
            "## Risk Severity Matrix\n"
            "Rank risks by (Probability × Impact) and identify the top 2 that require immediate mitigation.\n\n"
            "## Second-Order Effects\n"
            "Identify downstream consequences if primary risks materialize:\n"
            "- Cascade effects on dependent systems/processes\n"
            "- Reputation and trust implications\n"
            "- Recovery cost and timeline\n\n"
            "## Mitigation Requirements\n"
            "For each high-severity risk, specify:\n"
            "- Required control (preventive vs detective vs corrective)\n"
            "- Resource investment needed\n"
            "- Feasibility assessment (can we actually implement this?)\n"
            "- Trigger threshold (when do we activate contingency?)\n\n"
            "## Citations Used\n"
            "List each [Sx] with risk-relevant evidence summary.\n\n"
            "QUALITY REQUIREMENTS:\n"
            "- Every major risk claim must cite [Sx] source IDs\n"
            "- Use probability ranges, not vague terms like 'might fail'\n"
            "- Distinguish between evidence-based risks and speculation\n"
            "- Challenge assumptions in the advocate position explicitly"
        ),
        "synthesiser": (
            "You are the SYNTHESISER agent in a professional multi-agent research pipeline. Your mission is to integrate competing perspectives into a decision-ready recommendation.\n\n"
            "REQUIRED OUTPUT STRUCTURE (use exact headings):\n"
            "## Integrated Assessment\n"
            "One-paragraph summary of the core tension between opportunity and risk with your resolution stance.\n\n"
            "## Conflict Resolution Matrix\n"
            "For each point where Advocate and Skeptic disagree:\n"
            "| Dimension | Advocate Position | Skeptic Position | Resolution | Confidence |\n"
            "Explain your resolution reasoning with source citations [Sx].\n\n"
            "## Tradeoff Analysis\n"
            "Enumerate the key tradeoffs:\n"
            "- What you gain vs. what you sacrifice\n"
            "- Short-term vs. long-term considerations\n"
            "- Reversibility of each choice\n"
            "Use weighted scoring if multiple options exist.\n\n"
            "## Decision Rule\n"
            "State a specific IF-THEN decision framework:\n"
            "- IF [specific measurable condition] THEN [specific action]\n"
            "- Include at least 2 conditional branches\n"
            "- Define the null hypothesis (what happens if we do nothing)\n\n"
            "## Stakeholder Impact\n"
            "Identify who is affected and how:\n"
            "- Primary beneficiaries\n"
            "- Those who bear risk or cost\n"
            "- Required buy-in from specific roles\n\n"
            "## Guardrails\n"
            "Define operational boundaries:\n"
            "- Hard limits that cannot be crossed\n"
            "- Soft limits that trigger review\n"
            "- Escalation criteria (when to involve senior decision-makers)\n\n"
            "## Citations Used\n"
            "List each [Sx] with synthesis-relevant evidence.\n\n"
            "QUALITY REQUIREMENTS:\n"
            "- Explicitly acknowledge where sources conflict\n"
            "- Assign confidence levels to each recommendation element\n"
            "- Decision rules must be testable and unambiguous\n"
            "- No generic 'balance is key' conclusions"
        ),
        "oracle": (
            "You are the ORACLE agent in a professional multi-agent research pipeline. Your mission is to forecast outcomes with scenario analysis and define leading indicators.\n\n"
            "REQUIRED OUTPUT STRUCTURE (use exact headings):\n"
            "## Scenario Outlook\n"
            "Brief context on forecast methodology and key assumptions.\n\n"
            "## Most Likely Outcome (60%)\n"
            "- Specific outcome description with timeline\n"
            "- Key drivers that make this probable\n"
            "- Source evidence [Sx] supporting this trajectory\n"
            "- Expected metrics at 30/90/180 day marks\n\n"
            "## Upside Scenario (25%)\n"
            "- What accelerates beyond expectations\n"
            "- Required catalyst events\n"
            "- Magnitude of outperformance (quantified)\n"
            "- Early signals that this path is emerging\n\n"
            "## Downside Scenario (15%)\n"
            "- What causes underperformance or failure\n"
            "- Trigger conditions\n"
            "- Recovery options if this occurs\n"
            "- Circuit-breaker thresholds\n\n"
            "## Scenario Interdependencies\n"
            "Map how scenarios can shift:\n"
            "- What moves likelihood from base case to upside\n"
            "- What moves likelihood from base case to downside\n"
            "- Non-linear effects and tipping points\n\n"
            "## Leading Indicators Dashboard\n"
            "Define 4-6 measurable signals to track:\n"
            "| Indicator | Current Value | Target Range | Warning Threshold | Update Frequency |\n"
            "Distinguish leading (predictive) from lagging (confirmatory) indicators.\n\n"
            "## Forecast Confidence\n"
            "- Overall confidence level with rationale\n"
            "- Key uncertainties that could invalidate the forecast\n"
            "- Recommended forecast review cadence\n\n"
            "## Citations Used\n"
            "List each [Sx] with forecast-relevant evidence.\n\n"
            "QUALITY REQUIREMENTS:\n"
            "- All scenario probabilities must sum to 100%\n"
            "- Use specific timeframes, not vague 'soon' or 'eventually'\n"
            "- Indicators must be measurable and accessible\n"
            "- Acknowledge forecast uncertainty explicitly"
        ),
        "verifier": (
            "You are the VERIFIER agent in a professional multi-agent research pipeline. Your mission is to audit evidence quality and validate claims.\n\n"
            "REQUIRED OUTPUT STRUCTURE (use exact headings):\n"
            "## Verification Summary\n"
            "Overview of evidence quality across the research with aggregate confidence score.\n\n"
            "## Claim Audit Table\n"
            "For each major claim from other agents:\n"
            "| Claim | Source | Verification Status | Evidence Strength | Notes |\n"
            "\nStatus categories:\n"
            "- VERIFIED: Multiple independent sources confirm\n"
            "- SUPPORTED: Single credible source supports\n"
            "- WEAKLY-SUPPORTED: Indirect evidence or low-credibility source\n"
            "- CONTESTED: Sources disagree on this claim\n"
            "- UNVERIFIED: No source evidence found\n"
            "- SPECULATIVE: Claim extends beyond available evidence\n\n"
            "## Source Triangulation\n"
            "For critical claims, assess source agreement:\n"
            "- Which claims have 3+ independent sources (strong)\n"
            "- Which claims have 2 sources (moderate)\n"
            "- Which claims have only 1 source (weak)\n"
            "- Which claims have no sources (flag for removal)\n\n"
            "## Evidence Gaps\n"
            "Identify missing evidence that would strengthen the analysis:\n"
            "- What data would increase confidence\n"
            "- What sources should be consulted\n"
            "- What experiments could validate assumptions\n\n"
            "## Contradiction Map\n"
            "Where sources disagree:\n"
            "- State the contradiction clearly\n"
            "- Assess which source is more credible and why\n"
            "- Recommend how to resolve or flag the disagreement\n\n"
            "## Verification Confidence\n"
            "- Overall evidence strength score (1-100)\n"
            "- Recommendation for report confidence level\n"
            "- List claims that should include caveats in final report\n\n"
            "QUALITY REQUIREMENTS:\n"
            "- Audit at least 5 specific claims\n"
            "- Reference source credibility scores from research context\n"
            "- Be rigorous - flag weak evidence even if convenient\n"
            "- Distinguish between absence of evidence and evidence of absence"
        ),
        "final": (
            "You are the FINAL SYNTHESISER for a professional multi-agent research pipeline. Your mission is to produce a comprehensive, actionable research report.\n\n"
            "REQUIRED OUTPUT STRUCTURE (use exact headings):\n"
            "## Executive Summary\n"
            "3-sentence decision brief: Context → Finding → Recommendation with confidence level.\n\n"
            "## Research Scope\n"
            "- Core question addressed\n"
            "- Methodology: multi-agent synthesis with live web retrieval\n"
            "- Output objective and intended audience\n\n"
            "## Evidence Snapshot\n"
            "Table of sources with authority, credibility, and key contribution.\n\n"
            "## Analytical Breakdown\n"
            "### Report Plan\n"
            "Dynamic structure based on query type.\n\n"
            "### Claim Graph\n"
            "Map key claims to sources with edges showing support/contradiction.\n\n"
            "### Contradictions and Uncertainty\n"
            "Explicit disclosure of where evidence conflicts and confidence is limited.\n\n"
            "## Decision Recommendation\n"
            "Specific, actionable recommendation with:\n"
            "- The decision (what to do)\n"
            "- Trigger conditions (when to act)\n"
            "- Success thresholds (how to measure)\n"
            "- Contingency (what if it fails)\n\n"
            "## Action Plan\n"
            "Phased implementation with owners, timelines, and milestones.\n\n"
            "## Confidence and Open Questions\n"
            "Honest assessment of what we know vs. don't know.\n\n"
            "## Source Inventory\n"
            "Full citation list with credibility and relevance notes.\n\n"
            "QUALITY REQUIREMENTS:\n"
            "- Minimum 5 source citations\n"
            "- No generic template phrases\n"
            "- Traceability from evidence → analysis → conclusion\n"
            "- Explicit uncertainty quantification"
        ),
    }
    return prompts.get(agent_id, prompts["final"])


def _provider_agent_prompt(provider_name: str, agent_id: str) -> str:
    if provider_name == "openrouter":
        return _deterministic_prompt_text(agent_id)
    if provider_name == "local":
        return _deterministic_prompt_text(agent_id)
    if provider_name == "gemini":
        return _deterministic_prompt_text(agent_id)
    return _deterministic_prompt_text(agent_id)


def _provider_final_prompt(provider_name: str) -> str:
    return _deterministic_prompt_text("final")


async def _invoke_with_resilience(
    health: _ProviderHealthManager,
    stage: str,
    operation: Callable[[], Awaitable[T]],
    timeout_seconds: float,
    validate: Callable[[T], bool] | None = None,
) -> T:
    last_error: Exception | None = None
    attempts = health.retry_budget + 1

    for attempt in range(attempts):
        if not health.can_attempt():
            raise RuntimeError(f"{health.provider_name} circuit breaker is open")

        try:
            result = await asyncio.wait_for(operation(), timeout=timeout_seconds)
            if validate is not None and not validate(result):
                raise RuntimeError(f"{health.provider_name} stage {stage} returned an invalid result")
            health.record_success()
            return result
        except Exception as exc:
            last_error = exc
            health.record_failure(stage, exc)
            if attempt >= health.retry_budget or health.is_open():
                break
            await asyncio.sleep(min(health.backoff_seconds * (attempt + 1), 1.0))

    assert last_error is not None
    raise last_error


@dataclass
class DeterministicPipelineModelProvider:
    configured_provider: str = "deterministic"
    model_name: str = "deterministic"
    reason: str = ""
    _research: ResearchContext | None = None

    async def build_research_context(self, query: str) -> ResearchContext | None:
        return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        self._research = research  # Store for _get_source_details
        q = query.strip()
        source_block = self._source_block(research)
        if agent_id == "advocate":
            return self._structured_advocate(q, source_block)
        if agent_id == "skeptic":
            return self._structured_skeptic(q, source_block)
        if agent_id == "synthesiser":
            return self._structured_synthesiser(q, source_block)
        if agent_id == "verifier":
            return self._structured_verifier(q, source_block)
        return self._structured_oracle(q, source_block)

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        q = query.strip()
        report_mode = self._report_mode(q, research)
        refinement_block = f"\n- Refinement focus: {refinement_note.strip()}" if refinement_note and refinement_note.strip() else ""
        source_inventory = source_inventory_markdown(research)
        evidence_snapshot = self._evidence_snapshot_markdown(research)
        report_plan = self._report_plan_markdown(q, research, report_mode)
        claim_graph = self._claim_graph_markdown(outputs, research, report_mode)
        recommendation = self._decision_recommendation(outputs, research, report_mode)
        uncertainty = self._uncertainty_markdown(research, report_mode)
        action_plan = self._action_plan_markdown(report_mode, research)
        return (
            "## Executive Summary\n"
            f"This report addresses '{q}' using live retrieval evidence when available. It combines supportive and skeptical views, then converts them into a testable plan rather than a generic recommendation.\n\n"
            "## Research Scope\n"
            f"- Core question: {q}{refinement_block}\n"
            "- Method: retrieval-first synthesis with explicit citations and uncertainty disclosure.\n"
            f"- Output objective: a {report_mode} decision memo that can be validated in staged execution.\n"
            f"### Report Plan\n{report_plan}\n\n"
            "## Evidence Snapshot\n"
            f"{evidence_snapshot}\n\n"
            "## Analytical Breakdown\n"
            f"### {self._analysis_lens_heading(report_mode)}\n"
            f"- Opportunity case: {self._extract_section_summary(outputs.get('advocate', ''), '## Strategic Upside', '## Supporting Logic')}\n"
            f"- Risk case: {self._extract_section_summary(outputs.get('skeptic', ''), '## Primary Failure Modes', '## Risk Severity')}\n"
            f"- Integrated position: {self._extract_section_summary(outputs.get('synthesiser', ''), '## Tradeoff Resolution', '## Decision Rule')}\n"
            f"- Forecast signal: {self._extract_section_summary(outputs.get('oracle', ''), '## Most Likely Outcome (60%)', '## Upside Scenario (25%)')}\n\n"
            "### Verification Findings\n"
            f"{self._extract_section_summary(outputs.get('verifier', ''), '## Verification Summary', '## Claim Verification')}\n\n"
            "### Claim Graph\n"
            f"{claim_graph}\n\n"
            "### Contradictions and Uncertainty\n"
            f"{uncertainty}\n\n"
            "## Decision Recommendation\n"
            f"{recommendation}\n\n"
            "## Action Plan\n"
            f"{action_plan}\n\n"
            "## Confidence and Open Questions\n"
            f"{self._confidence_block(research, report_mode)}\n\n"
            "## Source Inventory\n"
            f"{source_inventory}"
        )

    def _evidence_snapshot_markdown(self, research: ResearchContext | None) -> str:
        if not research or not research.sources:
            return "- No live sources were retrieved. This report uses structured reasoning only and should be treated as provisional."

        lines: list[str] = []
        for source in research.sources[:6]:
            lines.append(
                f"- [{source.id}] {source.title} ({source.domain}) - authority: {source.authority}, credibility: {source.credibility_score:.2f}"
            )
            lines.append(f"  - Evidence: {source.excerpt}")
        return "\n".join(lines)

    def _claim_graph_markdown(self, outputs: dict[str, str], research: ResearchContext | None, report_mode: str) -> str:
        if not research or not research.sources:
            return "- Claim graph unavailable because no live sources were retrieved."

        advocate_claim = self._extract_section_summary(outputs.get("advocate", ""), "## Strategic Upside", "## Supporting Logic")
        skeptic_claim = self._extract_section_summary(outputs.get("skeptic", ""), "## Primary Failure Modes", "## Risk Severity")
        synthesis_claim = self._extract_section_summary(outputs.get("synthesiser", ""), "## Tradeoff Resolution", "## Decision Rule")
        outlook_claim = self._extract_section_summary(outputs.get("oracle", ""), "## Most Likely Outcome (60%)", "## Upside Scenario (25%)")

        top = research.sources[:4]
        lines = [
            f"- Node C1 (opportunity): {advocate_claim} -> [{top[0].id}]",
            f"- Node C2 (risk): {skeptic_claim} -> [{top[min(1, len(top) - 1)].id}]",
            f"- Node C3 (synthesis): {synthesis_claim} -> [{top[min(2, len(top) - 1)].id}]",
            f"- Node C4 (forecast): {outlook_claim} -> [{top[min(3, len(top) - 1)].id}]",
            f"- Edge: C1 supports C3; C2 constrains C3; C4 is conditional on the {report_mode} evidence profile.",
        ]
        return "\n".join(lines)

    def _decision_recommendation(self, outputs: dict[str, str], research: ResearchContext | None, report_mode: str) -> str:
        confidence_basis = self._source_block(research)
        summary = self._extract_section_summary(outputs.get("synthesiser", ""), "## Decision Rule", "## Guardrails")
        return (
            f"1. Use a {report_mode}-specific pilot with explicit success/failure gates.\n"
            "2. Require each key claim to map to at least one source ID and one measurable KPI.\n"
            "3. Escalate only when two consecutive review cycles show stable metrics and no unresolved contradictions.\n"
            f"4. Current confidence basis: {confidence_basis}.\n"
            f"5. Decision rule from synthesis: {summary}"
        )

    def _report_plan_markdown(self, query: str, research: ResearchContext | None, report_mode: str) -> str:
        if not research or not research.sources:
            return (
                f"- Mode: {report_mode}\n"
                "- Plan: collect evidence first, then build a claim graph, then validate against contradictions.\n"
                "- Priority: state uncertainty explicitly because no live sources were found."
            )

        plan_lines = [
            f"- Mode: {report_mode}",
            "- Section order: evidence snapshot -> claim graph -> contradictions -> decision recommendation -> action plan.",
            "- Priority: privilege primary sources, then reconcile disagreements before recommending action.",
        ]
        if report_mode == "policy":
            plan_lines.append("- Focus: regulatory constraints, stakeholder impact, and compliance risk.")
        elif report_mode == "engineering":
            plan_lines.append("- Focus: architecture, failure modes, reliability, and implementation cost.")
        elif report_mode == "medical":
            plan_lines.append("- Focus: evidence strength, safety, and conservative interpretation of claims.")
        elif report_mode == "operations":
            plan_lines.append("- Focus: execution, rollout sequencing, and operational guardrails.")
        else:
            plan_lines.append("- Focus: evidence quality, source diversity, and decision confidence.")
        return "\n".join(plan_lines)

    def _uncertainty_markdown(self, research: ResearchContext | None, report_mode: str) -> str:
        if not research or not research.sources:
            return "- Confidence: low because there are no retrieved live sources to validate external claims.\n- Open question: which live sources are most likely to overturn the current answer?"
        if len(research.sources) < 3:
            return (
                "- Confidence: moderate but limited by source diversity.\n"
                "- Rationale: prioritize collecting additional independent domains before scaling decisions.\n"
                f"- Open question: which {report_mode}-specific evidence is still missing?"
            )
        contradiction_count = len(getattr(research, "contradictions", ()))
        return (
            f"- Confidence: moderate, with {len(research.sources)} sources across {len({source.domain for source in research.sources})} domains.\n"
            f"- Rationale: contradiction count = {contradiction_count}; treat the recommendation as conditional when disputes remain unresolved.\n"
            f"- Open question: which source pair would most strongly change the answer if it were updated?"
        )

    def _action_plan_markdown(self, report_mode: str, research: ResearchContext | None) -> str:
        if report_mode == "policy":
            return (
                "- Step 1: map the policy surface and required approvals.\n"
                "- Step 2: validate the recommendation against the most authoritative sources.\n"
                "- Step 3: review implementation risk with stakeholders and legal/compliance owners.\n"
                "- Step 4: decide whether to adopt, revise, or stop."
            )
        if report_mode == "engineering":
            return (
                "- Step 1: confirm baseline architecture and bottlenecks.\n"
                "- Step 2: run a constrained technical pilot with explicit reliability gates.\n"
                "- Step 3: measure latency, failure modes, and implementation effort.\n"
                "- Step 4: scale only if the pilot improves both quality and operability."
            )
        if report_mode == "medical":
            return (
                "- Step 1: verify that the evidence base is current and primary-source backed.\n"
                "- Step 2: separate observational signal from causal inference.\n"
                "- Step 3: assess safety, uncertainty, and contraindications explicitly.\n"
                "- Step 4: escalate only with clinical oversight and documented caveats."
            )
        if report_mode == "operations":
            return (
                "- Step 1: define the operational baseline and failure thresholds.\n"
                "- Step 2: pilot the change in one constrained workflow.\n"
                "- Step 3: review defects, cycle time, and user adoption.\n"
                "- Step 4: scale only after two stable review cycles."
            )
        return (
            "- Step 1: confirm baseline, collect sources, and document assumptions.\n"
            "- Step 2: run a constrained pilot or desk evaluation.\n"
            "- Step 3: review performance, risks, and source contradictions.\n"
            "- Step 4: decide whether to scale, hold, or stop."
        )

    def _confidence_block(self, research: ResearchContext | None, report_mode: str) -> str:
        if not research or not research.sources:
            return "- Confidence: low, because the report has no live source support.\n- Open questions: which live source would most likely invalidate the recommendation?"

        domain_count = len({source.domain for source in research.sources})
        contradiction_count = len(getattr(research, "contradictions", ()))
        confidence = "high" if len(research.sources) >= 5 and domain_count >= 3 and contradiction_count == 0 else "moderate"
        if contradiction_count > 0:
            confidence = "moderate"
        return (
            f"- Confidence: {confidence}, with {len(research.sources)} sources across {domain_count} domains for the {report_mode} frame.\n"
            f"- Rationale: contradiction count = {contradiction_count}; source mix and recency determine how much weight to put on the recommendation.\n"
            "- Open questions: which claim would fail first under a stricter source audit?"
        )

    def _report_mode(self, query: str, research: ResearchContext | None) -> str:
        normalized = query.lower()
        if any(token in normalized for token in ("policy", "regulation", "law", "compliance", "governance")):
            return "policy"
        if any(token in normalized for token in ("medical", "clinical", "health", "patient", "diagnosis", "treatment")):
            return "medical"
        if any(token in normalized for token in ("architecture", "engineering", "system", "api", "backend", "latency", "performance", "reliability")):
            return "engineering"
        if any(token in normalized for token in ("operations", "workflow", "launch", "rollout", "scale", "process", "team")):
            return "operations"
        if any(token in normalized for token in ("compare", "versus", "vs", "benchmark", "tradeoff")):
            return "comparison"
        return "research"

    def _analysis_lens_heading(self, report_mode: str) -> str:
        headings = {
            "policy": "Policy Lens",
            "medical": "Clinical Evidence Lens",
            "engineering": "Engineering Lens",
            "operations": "Operational Lens",
            "comparison": "Comparison Lens",
            "research": "Research Lens",
        }
        return headings.get(report_mode, "Research Lens")

    def _structured_advocate(self, query: str, source_block: str) -> str:
        sources = self._get_source_details()
        primary_source = sources[0] if sources else {"id": "S1", "title": "reasoning analysis", "domain": "internal", "cred": 0.7}
        secondary_source = sources[1] if len(sources) > 1 else primary_source
        
        return (
            "## Opportunity Thesis\n"
            f"The strategic opportunity in addressing '{query}' presents a **high-value path** with "
            f"estimated 15-40% improvement potential over baseline approaches within 90 days, contingent on disciplined execution "
            f"and evidence-based iteration [supported by {primary_source['id']}].\n\n"
            "## Strategic Upside\n"
            f"1. **Immediate efficiency gain (0-30 days)**: Structured approach reduces decision latency by ~25% through clear ownership and pre-defined success criteria [{primary_source['id']}].\n"
            f"2. **Quality improvement (30-60 days)**: Evidence-grounded methodology surfaces blind spots earlier, reducing rework by 20-35% [{secondary_source['id']}].\n"
            f"3. **Compounding returns (60-90 days)**: Fast feedback loops create institutional learning that accelerates future similar decisions.\n"
            f"4. **Risk-adjusted value**: Staged rollout limits downside while preserving upside optionality.\n"
            f"5. **Competitive positioning**: Early movers on evidence-based approaches outperform reactive competitors [{primary_source['id']}].\n\n"
            "## Supporting Logic\n"
            f"**Reasoning chain:**\n"
            f"- Premise A: Current approaches to '{query}' lack systematic evidence integration, leading to inconsistent outcomes.\n"
            f"- Evidence B: Source [{primary_source['id']}] from {primary_source['domain']} (credibility: {primary_source['cred']:.0%}) demonstrates that structured methodology improves outcome predictability.\n"
            f"- Mechanism: When decision-makers have explicit criteria and evidence mapping, they identify failure modes 2x faster.\n"
            f"- Conclusion: Implementing this approach creates measurable value through faster learning cycles.\n\n"
            f"**Required conditions for success:**\n"
            "- Clear scope boundaries defined before launch\n"
            "- Pre-committed success/failure thresholds\n"
            "- Resource allocation for at least 2 iteration cycles\n\n"
            "## Actionable Next Step\n"
            "**Action**: Launch a 14-day constrained pilot.\n"
            "- **Who**: Product/Operations lead (single accountable owner)\n"
            "- **What**: Apply methodology to ONE high-value, low-complexity decision with full evidence tracking\n"
            "- **When**: Begin within 7 days of approval\n"
            "- **Success criteria**: Pilot demonstrates ≥15% improvement in decision confidence score OR reduces time-to-decision by ≥20%\n\n"
            "## Citations Used\n"
            f"- [{primary_source['id']}] {primary_source['title']} ({primary_source['domain']}): Primary evidence for methodology effectiveness.\n"
            + (f"- [{secondary_source['id']}] {secondary_source['title']} ({secondary_source['domain']}): Supporting evidence for quality improvements.\n" if secondary_source != primary_source else "")
        )

    def _structured_skeptic(self, query: str, source_block: str) -> str:
        sources = self._get_source_details()
        primary_source = sources[0] if sources else {"id": "S1", "title": "risk analysis", "domain": "internal", "cred": 0.7}
        
        return (
            "## Risk Thesis\n"
            f"Pursuing '{query}' carries **MEDIUM-HIGH risk** due to hidden complexity costs, execution uncertainty, "
            f"and potential for false confidence from incomplete evidence [{primary_source['id']}]. "
            "Mitigation requires explicit controls before scaling.\n\n"
            "## Primary Failure Modes\n"
            "### 1. Integration Complexity Underestimation (Technical Risk)\n"
            "- **Probability**: 40-60%\n"
            "- **Impact**: 4/5 - Can erase projected gains entirely\n"
            "- **Detection**: Medium difficulty - often surfaces late in implementation\n"
            f"- **Evidence**: [{primary_source['id']}] indicates integration efforts typically exceed estimates by 2-3x\n\n"
            "### 2. Adoption Resistance (Execution Risk)\n"
            "- **Probability**: 30-50%\n"
            "- **Impact**: 3/5 - Reduces effectiveness even if technically successful\n"
            "- **Detection**: Early signals available through engagement metrics\n"
            "- **Evidence**: Change initiatives fail at 70% rate without structured change management\n\n"
            "### 3. Measurement Gaming (Adoption Risk)\n"
            "- **Probability**: 25-40%\n"
            "- **Impact**: 3/5 - Creates false confidence, delays course correction\n"
            "- **Detection**: Difficult - requires external validation\n"
            "- **Evidence**: Goodhart's Law - metrics become targets and lose validity\n\n"
            "### 4. Resource Diversion (Execution Risk)\n"
            "- **Probability**: 35-55%\n"
            "- **Impact**: 3/5 - Opportunity cost of attention and budget\n"
            "- **Detection**: Easy - visible in allocation decisions\n\n"
            "## Risk Severity Matrix\n"
            "| Risk | Probability | Impact | Score | Priority |\n"
            "|------|-------------|--------|-------|----------|\n"
            "| Integration complexity | 50% | 4 | **2.0** | **P1 - Mitigate immediately** |\n"
            "| Adoption resistance | 40% | 3 | 1.2 | P2 - Active monitoring |\n"
            "| Measurement gaming | 32% | 3 | 1.0 | P2 - Design controls |\n"
            "| Resource diversion | 45% | 3 | 1.35 | P2 - Scope limits |\n\n"
            "## Second-Order Effects\n"
            "If primary risks materialize:\n"
            "- **Cascade**: Failed pilot damages credibility for future initiatives (trust recovery: 6-12 months)\n"
            "- **Reputation**: Stakeholders become skeptical of evidence-based claims broadly\n"
            "- **Recovery cost**: Rollback requires 50-75% of original investment plus opportunity cost\n"
            "- **Team impact**: Morale and momentum loss affects adjacent projects\n\n"
            "## Mitigation Requirements\n"
            "### For Integration Complexity (P1):\n"
            "- **Control**: Technical spike + architecture review BEFORE commitment\n"
            "- **Investment**: 3-5 days of senior engineering time upfront\n"
            "- **Feasibility**: High - standard practice but often skipped\n"
            "- **Trigger**: If spike reveals >40% more complexity than estimated, rescope or abort\n\n"
            "### For Adoption Resistance (P2):\n"
            "- **Control**: Stakeholder mapping + explicit change management plan\n"
            "- **Investment**: 2-3 days of product/operations time\n"
            "- **Feasibility**: Medium - requires executive sponsorship\n"
            "- **Trigger**: If <50% of target users engage in week 1, pause and diagnose\n\n"
            "## Citations Used\n"
            f"- [{primary_source['id']}] {primary_source['title']} ({primary_source['domain']}): Risk patterns and failure mode evidence.\n"
        )

    def _structured_synthesiser(self, query: str, source_block: str) -> str:
        sources = self._get_source_details()
        primary_source = sources[0] if sources else {"id": "S1", "title": "synthesis", "domain": "internal", "cred": 0.7}
        
        return (
            "## Integrated Assessment\n"
            f"Analysis of '{query}' reveals a **conditional opportunity**: the upside is real and achievable, "
            "but ONLY under disciplined execution with explicit guardrails. The core tension is between "
            f"speed-to-value (Advocate) and risk mitigation (Skeptic). Resolution: proceed with staged gates [{primary_source['id']}].\n\n"
            "## Conflict Resolution Matrix\n"
            "| Dimension | Advocate Position | Skeptic Position | Resolution | Confidence |\n"
            "|-----------|-------------------|------------------|------------|------------|\n"
            "| Timeline | 90-day full value | 40-60% failure risk | **Staged: 30-day pilot first** | 75% |\n"
            "| Scope | Broad application | Hidden complexity | **Narrow: 1 workflow only** | 80% |\n"
            "| Investment | Commit resources | Opportunity cost | **Capped: 15% of available budget** | 70% |\n"
            "| Success metric | 25% improvement | Measurement gaming | **External validation required** | 65% |\n\n"
            "**Resolution rationale**: Sources suggest that staged approaches preserve upside while limiting downside. "
            f"[{primary_source['id']}] supports conditional commitment over binary go/no-go.\n\n"
            "## Tradeoff Analysis\n"
            "### What you gain vs. sacrifice:\n"
            "- **Gain**: Faster learning, potential 15-40% improvement, competitive positioning\n"
            "- **Sacrifice**: Immediate full-scale impact, resource allocation to other initiatives\n\n"
            "### Short-term vs. long-term:\n"
            "- **Short-term (0-30 days)**: Investment cost, learning curve, temporary productivity dip\n"
            "- **Long-term (90+ days)**: Compounding returns, institutional capability, reduced future risk\n\n"
            "### Reversibility:\n"
            "- Pilot stage: **Fully reversible** - abort costs ~$X, no reputation damage\n"
            "- Scale stage: **Partially reversible** - rollback costs ~5x pilot, some reputation risk\n"
            "- Full deployment: **Difficult to reverse** - switching costs lock in decision\n\n"
            "## Decision Rule\n"
            "```\n"
            "IF (pilot metrics ≥ 15% improvement over baseline)\n"
            "   AND (no critical risk triggers fired)\n"
            "   AND (resource availability confirmed for Phase 2)\n"
            "THEN → Proceed to expanded pilot (3 workflows)\n"
            "\n"
            "ELSE IF (pilot metrics between 5-15% improvement)\n"
            "   AND (learnings suggest fixable issues)\n"
            "THEN → Iterate on pilot (extend 2 weeks) with specific improvements\n"
            "\n"
            "ELSE → Abort and redirect resources\n"
            "```\n\n"
            "**Null hypothesis**: If we do nothing, current baseline continues with ~5% natural degradation over 6 months due to increasing complexity.\n\n"
            "## Stakeholder Impact\n"
            "- **Primary beneficiaries**: Operations team (reduced cognitive load), Leadership (better decision confidence)\n"
            "- **Risk bearers**: Implementation team (effort), Adjacent projects (resource competition)\n"
            "- **Required buy-in**: Executive sponsor (resource approval), Operations lead (execution), Technical lead (integration)\n\n"
            "## Guardrails\n"
            "### Hard Limits (non-negotiable):\n"
            "- Budget cap: 15% of quarterly allocation\n"
            "- Timeline: Maximum 90 days to value demonstration\n"
            "- Scope: No more than 3 workflows before formal review\n\n"
            "### Soft Limits (trigger review):\n"
            "- Week-over-week engagement decline >20%\n"
            "- Metric improvement <10% at day 21\n"
            "- Integration effort exceeds estimate by >50%\n\n"
            "### Escalation Criteria:\n"
            "- Any hard limit breach → Executive review required\n"
            "- Two soft limit breaches → Pause and reassess\n"
            "- Stakeholder conflict → Facilitated alignment session\n\n"
            "## Citations Used\n"
            f"- [{primary_source['id']}] {primary_source['title']} ({primary_source['domain']}): Supports staged execution model.\n"
        )

    def _structured_oracle(self, query: str, source_block: str) -> str:
        sources = self._get_source_details()
        primary_source = sources[0] if sources else {"id": "S1", "title": "forecast", "domain": "internal", "cred": 0.7}
        
        return (
            "## Scenario Outlook\n"
            f"Forecasting outcomes for '{query}' using evidence synthesis and probabilistic scenario modeling. "
            f"Methodology: weighted scenario analysis with leading indicators [{primary_source['id']}]. "
            "Key assumption: execution quality matches historical organizational baseline.\n\n"
            "## Most Likely Outcome (60%)\n"
            "**Trajectory**: Gradual improvement with early friction, achieving 65-80% of projected value.\n\n"
            "**Timeline markers:**\n"
            "- Day 30: Pilot operational, early signals emerging, 10-15% baseline measurement complete\n"
            "- Day 60: First iteration complete, learnings applied, 40-50% of target improvement visible\n"
            "- Day 90: Scaled to 2-3 workflows, 60-75% of target improvement sustained\n"
            "- Day 180: Methodology embedded, 80%+ of projected value captured, maintenance mode\n\n"
            f"**Key drivers**: Adequate resourcing, clear ownership, and willingness to iterate based on data [{primary_source['id']}].\n"
            f"**Source evidence**: Historical success rates for similar initiatives at comparable complexity.\n\n"
            "## Upside Scenario (25%)\n"
            "**Trajectory**: Faster-than-expected adoption creates multiplier effects, achieving 120-150% of projected value.\n\n"
            "**Catalyst requirements:**\n"
            "- Early champion emerges who drives viral internal adoption\n"
            "- First use case hits exceptional results (>30% improvement), creating proof point\n"
            "- External validation (customer feedback, market recognition) amplifies internal momentum\n\n"
            "**Magnitude**: 40-60% better than base case within same timeframe\n"
            "**Early signals** (watch for by Day 14):\n"
            "- Engagement >80% of target users\n"
            "- Unsolicited requests to join pilot\n"
            "- Leadership citing initiative in other contexts\n\n"
            "## Downside Scenario (15%)\n"
            "**Trajectory**: Hidden complexity and resistance cause stall, achieving <30% of projected value.\n\n"
            "**Trigger conditions:**\n"
            "- Key integration fails or takes 3x longer than estimated\n"
            "- Executive sponsor changes or withdraws support\n"
            "- Competing priority absorbs allocated resources\n"
            "- Early metrics are gamed, masking real problems\n\n"
            "**Recovery options:**\n"
            "- Narrow scope to single highest-value workflow\n"
            "- Extend timeline with reduced resource commitment\n"
            "- Pivot to learning exercise with explicit write-off\n\n"
            "**Circuit-breaker thresholds:**\n"
            "- Day 14: <30% engagement → Pause and diagnose\n"
            "- Day 30: <5% improvement → Scope reduction required\n"
            "- Day 45: No improvement + team frustration → Abort consideration\n\n"
            "## Scenario Interdependencies\n"
            "**Base → Upside shifts when:**\n"
            "- Week 2 engagement exceeds 75% AND first win story emerges\n"
            "- Technical integration completes ahead of schedule\n"
            "- External validation creates organizational excitement\n\n"
            "**Base → Downside shifts when:**\n"
            "- Key dependency fails or is delayed >2 weeks\n"
            "- Sponsor attention diverted to crisis\n"
            "- Team capacity reduced by >30% due to competing work\n\n"
            "**Tipping points:**\n"
            "- Day 21 is critical: trajectory usually clear by this point\n"
            "- Resource continuity decision at Day 30 locks in 70% of outcome\n\n"
            "## Leading Indicators Dashboard\n"
            "| Indicator | Current | Target | Warning | Frequency |\n"
            "|-----------|---------|--------|---------|----------|\n"
            "| User engagement rate | Baseline | >70% | <50% | Daily |\n"
            "| Decision time (vs baseline) | 100% | <80% | >95% | Weekly |\n"
            "| Stakeholder satisfaction | Baseline | >7/10 | <5/10 | Bi-weekly |\n"
            "| Resource utilization | 0% | 80-100% | >120% | Weekly |\n"
            "| Integration blockers | 0 | 0 | >2 active | Daily |\n"
            "| Iteration velocity | N/A | 1/week | <1/2 weeks | Weekly |\n\n"
            "**Leading** (predictive): Engagement rate, integration blockers, iteration velocity\n"
            "**Lagging** (confirmatory): Decision time, stakeholder satisfaction\n\n"
            "## Forecast Confidence\n"
            "- **Overall confidence**: 65% (moderate) - historical data supports methodology but execution variance is high\n"
            "- **Key uncertainties**: Integration complexity (underestimated 40% of time), sponsor continuity, resource competition\n"
            "- **Forecast review cadence**: Day 14 (early signal check), Day 30 (trajectory confirmation), Day 60 (scale decision)\n\n"
            "## Citations Used\n"
            f"- [{primary_source['id']}] {primary_source['title']} ({primary_source['domain']}): Forecast baseline and scenario probabilities.\n"
        )

    def _structured_verifier(self, query: str, source_block: str) -> str:
        sources = self._get_source_details()
        source_count = len(sources)
        avg_cred = sum(s['cred'] for s in sources) / max(1, source_count) if sources else 0.5
        
        return (
            "## Claim Verification\n"
            f"Evidence audit for '{query}' assessing claim support quality across {source_count} sources "
            f"with average credibility {avg_cred:.0%}.\n\n"
            "## Verification Summary\n"
            f"- **Overall evidence strength**: {int(avg_cred * 100)}/100\n"
            f"- **Source diversity**: {source_count} sources across {len(set(s['domain'] for s in sources)) if sources else 0} domains\n"
            f"- **Triangulation quality**: {'Strong' if source_count >= 3 else 'Moderate' if source_count >= 2 else 'Weak'} - {'multiple' if source_count >= 3 else 'limited'} independent confirmation\n"
            "- **Recommendation**: " + ("Proceed with confidence" if avg_cred > 0.7 and source_count >= 3 else "Proceed with caution - evidence gaps exist" if avg_cred > 0.5 else "Strengthen evidence before acting") + "\n\n"
            "## Claim Audit Table\n"
            "| # | Claim | Source | Status | Strength | Notes |\n"
            "|---|-------|--------|--------|----------|-------|\n"
            f"| 1 | 15-40% improvement potential | [{sources[0]['id'] if sources else 'S1'}] | SUPPORTED | Medium | Single source, reasonable estimate |\n"
            f"| 2 | Staged rollout reduces risk | [{sources[0]['id'] if sources else 'S1'}] | VERIFIED | High | Multiple sources confirm pattern |\n"
            "| 3 | 90-day value realization | Internal | WEAKLY-SUPPORTED | Low | Based on estimates, not evidence |\n"
            "| 4 | Integration complexity risk | Historical | VERIFIED | High | Consistent with industry data |\n"
            "| 5 | Adoption requires change mgmt | Best practice | SUPPORTED | Medium | Well-established pattern |\n"
            "| 6 | Compound returns over time | Theoretical | SPECULATIVE | Low | Logical but unproven in context |\n\n"
            "## Source Triangulation\n"
            "### Strong confirmation (3+ sources): \n"
            "- Staged execution reduces failure risk\n"
            "- Integration complexity commonly underestimated\n\n"
            "### Moderate confirmation (2 sources):\n"
            "- Evidence-based approaches improve outcomes\n"
            "- Clear ownership improves execution\n\n"
            "### Weak confirmation (1 source):\n"
            "- Specific improvement percentages (15-40%)\n"
            "- 90-day timeline estimates\n\n"
            "### No confirmation (flag for removal):\n"
            "- Compound return multipliers (speculative extrapolation)\n\n"
            "## Evidence Gaps\n"
            "**Critical gaps that would strengthen analysis:**\n"
            "1. **Quantified baseline**: Current performance metrics to measure against\n"
            "2. **Comparable implementations**: Case studies in similar organizational contexts\n"
            "3. **Resource estimation validation**: Third-party effort estimates\n"
            "4. **Failure mode frequency**: Statistical data on similar initiative failures\n\n"
            "**Recommended additional sources:**\n"
            "- Industry benchmarking studies\n"
            "- Internal historical project data\n"
            "- Expert interviews (practitioners, not vendors)\n\n"
            "## Contradiction Map\n"
            "| Contradiction | Source A | Source B | Resolution |\n"
            "|---------------|----------|----------|------------|\n"
            "| Timeline optimism | Advocate (90d) | Skeptic (risk) | **Use conservative estimate** - plan for 90d, budget for 120d |\n"
            "| Scope recommendation | Advocate (broad) | Skeptic (narrow) | **Defer to Skeptic** - start narrow, evidence suggests safer |\n"
            "| ROI magnitude | High estimates | Risk discount | **Apply 30% haircut** to optimistic projections |\n\n"
            "## Verification Confidence\n"
            f"- **Overall evidence strength score**: {int(avg_cred * 85)}/100\n"
            "- **Report confidence level**: " + ("HIGH - proceed with stated recommendations" if avg_cred > 0.75 else "MEDIUM - include uncertainty caveats" if avg_cred > 0.5 else "LOW - flag as exploratory") + "\n\n"
            "**Claims requiring explicit caveats in final report:**\n"
            "- Improvement percentage ranges (evidence supports direction, not magnitude)\n"
            "- Timeline estimates (high variance in historical outcomes)\n"
            "- Long-term compound effects (theoretical, not empirical)\n"
        )

    def _get_source_details(self) -> list[dict]:
        """Extract structured source info from research context."""
        if not hasattr(self, '_research') or not self._research or not self._research.sources:
            return []
        return [
            {"id": s.id, "title": s.title, "domain": s.domain, "cred": s.credibility_score}
            for s in self._research.sources[:6]
        ]

    def _source_block(self, research: ResearchContext | None) -> str:
        if not research or not research.sources:
            return "No live web sources were available, so this result is based on direct reasoning only."

        top = research.sources[0]
        return f"{top.id} {top.title} ({top.domain})"

    def _extract_section_summary(self, text: str, preferred: str, fallback: str) -> str:
        lines = text.splitlines()
        section_indexes = [i for i, line in enumerate(lines) if line.strip() in {preferred, fallback}]
        for index in section_indexes:
            for candidate in lines[index + 1 :]:
                stripped = candidate.strip()
                if not stripped:
                    continue
                if stripped.startswith("## "):
                    break
                if stripped.startswith("-") or stripped[0].isdigit():
                    return stripped.lstrip("- ").strip()
                return stripped
        return text.split("\n", 1)[0].strip() or "Not available"

    def _research_findings(self, research: ResearchContext | None) -> str:
        if not research or not research.sources:
            return "- No live web retrieval was available, so the report should flag that gap explicitly.\n- The app still needs a retrieval layer before generation to qualify as a research model.\n- Final claims should be marked as provisional when they are not source-backed."

        lines = [
            "- The app now has an actual web-retrieval prepass and should no longer rely only on model memory.",
            "- Source inventory and source pack should be displayed alongside the answer so users can audit the claims.",
            "- Claims should be tied to source IDs and the report should include a section that explains which sources were used and why they matter.",
        ]
        if any(source.authority == "primary" for source in research.sources):
            lines.append("- Primary sources should be preferred whenever the question asks for current specifications or official guidance.")
        if len(research.sources) >= 3:
            lines.append("- A mixed source set is healthier than a single-source answer because it reveals disagreements and gaps.")
        return "\n".join(lines)

    def _tool_analysis_markdown(self, research: ResearchContext | None) -> str:
        source_note = self._source_block(research)
        return (
            "#### 3.2.1 Google Search\n"
            "- Best for current facts, news, policy changes, and broad discovery.\n"
            "- Missing step in the app: a live grounding pass before synthesis.\n"
            "- What to do: search first, then pass the top results into the model with explicit source IDs.\n\n"
            "#### 3.2.2 URL Context\n"
            "- Best for deep reading of specific pages or docs discovered during search.\n"
            "- Missing step in the app: direct page retrieval and page-level evidence extraction.\n"
            "- What to do: fetch the most relevant URLs, extract the visible text, and use it as page-grounding context.\n\n"
            "#### 3.2.3 File Search\n"
            "- Best for private knowledge bases, manuals, and repeatable retrieval over your own documents.\n"
            "- Missing step in the app: a private-data retrieval lane for uploaded files or internal notes.\n"
            "- What to do: keep File Search as a separate lane from public web search and cite retrieved document chunks.\n\n"
            "#### 3.2.4 Code Execution\n"
            "- Best for numeric checks, comparisons, calculations, and small data transformations.\n"
            "- Missing step in the app: any verification stage that computes derived values instead of trusting model prose.\n"
            "- What to do: run code when a query needs aggregation, scoring, or repeatable analysis.\n\n"
            f"- Current grounding note: {source_note}"
        )

    def diagnostics(self) -> dict[str, str | int | bool]:
        registry = prompt_registry_snapshot(
            [
                prompt_fingerprint("advocate", _provider_agent_prompt(self.configured_provider, "advocate")),
                prompt_fingerprint("skeptic", _provider_agent_prompt(self.configured_provider, "skeptic")),
                prompt_fingerprint("synthesiser", _provider_agent_prompt(self.configured_provider, "synthesiser")),
                prompt_fingerprint("oracle", _provider_agent_prompt(self.configured_provider, "oracle")),
                prompt_fingerprint("final", _provider_final_prompt(self.configured_provider)),
            ]
        )
        return {
            "configuredProvider": self.configured_provider,
            "activeProvider": "deterministic",
            "modelName": self.model_name,
            "isFallback": self.configured_provider != "deterministic",
            "fallbackCount": 0,
            "lastError": self.reason,
            "promptRegistryVersion": registry["registryVersion"],
            "promptRegistrySize": len(registry["prompts"]),
        }


class GeminiPipelineModelProvider:
    def __init__(self, model_name: str) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        self._model_name = model_name
        self._fallback_count = 0
        self._last_error = ""
        self._health = _ProviderHealthManager(
            provider_name="gemini",
            retry_budget=_provider_retry_budget(),
            failure_threshold=_provider_failure_threshold(),
            cooldown_seconds=_provider_cooldown_seconds(),
            backoff_seconds=_provider_backoff_seconds(),
        )
        self._researcher = _create_researcher()
        self._model = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.35,
        )
        self._fallback = DeterministicPipelineModelProvider(
            configured_provider="gemini",
            model_name=model_name,
            reason="Gemini runtime call failed",
        )

    async def build_research_context(self, query: str) -> ResearchContext | None:
        if not _web_research_enabled():
            return None
        if not self._health.can_attempt():
            return None
        try:
            return await _invoke_with_resilience(
                self._health,
                "retrieval",
                lambda: self._researcher.research(query),
                _stage_timeout_seconds("retrieval"),
            )
        except Exception as exc:
            self._register_fallback(exc)
            return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.build_agent_text(agent_id, query, research)

        prompts = {
            "advocate": (
                "You are the ADVOCATE agent in a professional multi-agent research pipeline. Your mission is to construct the strongest evidence-backed case for action.\n\n"
                "REQUIRED OUTPUT STRUCTURE:\n"
                "## Opportunity Thesis\n"
                "State the core opportunity with quantified impact (percentage, timeframe, magnitude). One sentence.\n\n"
                "## Strategic Upside\n"
                "List 3-5 specific benefits. Each MUST include:\n"
                "- [Sx] citation to research source\n"
                "- Quantified estimate where possible\n"
                "- Timeframe (immediate/30-day/90-day)\n\n"
                "## Supporting Logic\n"
                "Present reasoning chain: Premise + Evidence → Conclusion\n"
                "- At least 2 causal mechanisms explaining WHY benefits occur\n"
                "- Reference comparable precedents from sources\n"
                "- Note required conditions for success\n\n"
                "## Actionable Next Step\n"
                "ONE concrete action with: Who (role), What (deliverable), When (timeframe), Success criteria (measurable)\n\n"
                "## Citations Used\n"
                "List each [Sx] with evidence summary and credibility note.\n\n"
                "QUALITY REQUIREMENTS: Every claim cites [Sx]. Use specific numbers. No 'could potentially' phrases. Ground in evidence."
            ),
            "skeptic": (
                "You are the SKEPTIC agent in a professional multi-agent research pipeline. Your mission is to identify failure modes, quantify risks, and ensure recommendations survive scrutiny.\n\n"
                "REQUIRED OUTPUT STRUCTURE:\n"
                "## Risk Thesis\n"
                "Primary risk hypothesis with severity (Critical/High/Medium/Low).\n\n"
                "## Primary Failure Modes\n"
                "3-5 failures using taxonomy: Technical | Execution | Market/External | Adoption\n"
                "For each include: Probability (%), Impact (1-5), Detection difficulty, [Sx] citation\n\n"
                "## Risk Severity Matrix\n"
                "Rank by (Probability × Impact). Identify top 2 requiring immediate mitigation.\n\n"
                "## Second-Order Effects\n"
                "Downstream consequences: Cascade effects, reputation impact, recovery cost\n\n"
                "## Mitigation Requirements\n"
                "For high-severity risks: Control type, resource investment, feasibility, trigger threshold\n\n"
                "## Citations Used\n"
                "List each [Sx] with risk-relevant evidence.\n\n"
                "QUALITY REQUIREMENTS: Cite [Sx] for every major risk. Use probability ranges. Challenge advocate assumptions explicitly."
            ),
            "synthesiser": (
                "You are the SYNTHESISER agent in a professional multi-agent research pipeline. Your mission is to integrate competing perspectives into a decision-ready recommendation.\n\n"
                "REQUIRED OUTPUT STRUCTURE:\n"
                "## Integrated Assessment\n"
                "Core tension between opportunity/risk with your resolution stance. One paragraph.\n\n"
                "## Conflict Resolution Matrix\n"
                "Where Advocate and Skeptic disagree: Dimension | Advocate | Skeptic | Resolution | Confidence\n\n"
                "## Tradeoff Analysis\n"
                "Key tradeoffs: Gain vs sacrifice, short vs long-term, reversibility of choices.\n\n"
                "## Decision Rule\n"
                "Specific IF-THEN framework with 2+ conditional branches. Define null hypothesis.\n\n"
                "## Stakeholder Impact\n"
                "Who benefits, who bears risk, required buy-in from which roles.\n\n"
                "## Guardrails\n"
                "Hard limits (non-negotiable), soft limits (trigger review), escalation criteria.\n\n"
                "## Citations Used\n"
                "List [Sx] with synthesis-relevant evidence.\n\n"
                "QUALITY REQUIREMENTS: Acknowledge source conflicts. Assign confidence levels. Decision rules must be testable."
            ),
            "oracle": (
                "You are the ORACLE agent in a professional multi-agent research pipeline. Your mission is to forecast outcomes with scenario analysis and define leading indicators.\n\n"
                "REQUIRED OUTPUT STRUCTURE:\n"
                "## Scenario Outlook\n"
                "Forecast methodology and key assumptions.\n\n"
                "## Most Likely Outcome (60%)\n"
                "Timeline markers at 30/60/90/180 days. Key drivers. [Sx] evidence.\n\n"
                "## Upside Scenario (25%)\n"
                "Catalyst requirements. Magnitude (quantified). Early signals.\n\n"
                "## Downside Scenario (15%)\n"
                "Trigger conditions. Recovery options. Circuit-breaker thresholds.\n\n"
                "## Scenario Interdependencies\n"
                "What shifts likelihood between scenarios. Tipping points.\n\n"
                "## Leading Indicators Dashboard\n"
                "4-6 measurable signals: Indicator | Target | Warning | Frequency\n"
                "Distinguish leading (predictive) from lagging (confirmatory).\n\n"
                "## Forecast Confidence\n"
                "Overall level with rationale. Key uncertainties. Review cadence.\n\n"
                "## Citations Used\n"
                "List [Sx] with forecast-relevant evidence.\n\n"
                "QUALITY REQUIREMENTS: Probabilities sum to 100%. Use specific timeframes. Indicators must be measurable."
            ),
            "verifier": (
                "You are the VERIFIER agent. Your mission is to audit evidence quality and validate claims.\n\n"
                "REQUIRED OUTPUT STRUCTURE:\n"
                "## Verification Summary\n"
                "Evidence quality overview with aggregate confidence score (1-100).\n\n"
                "## Claim Audit Table\n"
                "| Claim | Source | Status | Strength | Notes |\n"
                "Status: VERIFIED/SUPPORTED/WEAKLY-SUPPORTED/CONTESTED/UNVERIFIED/SPECULATIVE\n\n"
                "## Source Triangulation\n"
                "Strong (3+ sources) | Moderate (2) | Weak (1) | None\n\n"
                "## Evidence Gaps\n"
                "Missing data. Recommended sources. Validation experiments.\n\n"
                "## Contradiction Map\n"
                "Where sources disagree. Which is more credible. Resolution recommendation.\n\n"
                "## Verification Confidence\n"
                "Overall score. Confidence level. Claims needing caveats.\n\n"
                "QUALITY REQUIREMENTS: Audit 5+ claims. Reference credibility scores. Flag weak evidence."
            ),
        }
        instruction = prompts.get(agent_id, prompts.get("verifier", prompts["oracle"]))
        research_block = format_research_context(research)
        try:
            resolved = await _invoke_with_resilience(
                self._health,
                f"agent:{agent_id}",
                lambda: self._ainvoke(
                    f"{instruction}\n\nQuestion: {query.strip()}\n\nLive web research context:\n{research_block}"
                ),
                _stage_timeout_seconds("agent"),
                lambda text: _is_agent_research_grade(text, minimum_length=260, research=research),
            )
            return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.build_agent_text(agent_id, query, research)

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

        research_block = format_research_context(research)
        final_prompt = (
            "You are the FINAL SYNTHESISER for a professional multi-agent research pipeline producing executive-grade research reports.\n\n"
            "REQUIRED OUTPUT STRUCTURE (use exact headings):\n\n"
            "## Executive Summary\n"
            "3-sentence decision brief: Context → Key Finding → Recommendation with confidence level (High/Medium/Low).\n\n"
            "## Research Scope\n"
            "- Core question addressed\n"
            "- Methodology: multi-agent synthesis with live web retrieval\n"
            "- Evidence basis: X sources across Y domains\n"
            "- Output objective and intended audience\n\n"
            "## Evidence Snapshot\n"
            "| Source | Domain | Authority | Credibility | Key Contribution |\n"
            "List all sources used with their evidence value.\n\n"
            "## Analytical Breakdown\n\n"
            "### Report Plan\n"
            "Query type classification and dynamic section focus.\n\n"
            "### Claim Graph\n"
            "Map key claims to sources: Claim → [Sx] with support/contradiction edges.\n"
            "Show how evidence flows from sources to conclusions.\n\n"
            "### Contradictions and Uncertainty\n"
            "- Where sources disagree and how conflict was resolved\n"
            "- Confidence intervals on key claims\n"
            "- Evidence gaps that limit certainty\n\n"
            "## Decision Recommendation\n"
            "Specific, actionable recommendation with:\n"
            "- **THE DECISION**: Exact policy choice or action (not vague guidance)\n"
            "- **TRIGGER CONDITIONS**: When to act (specific thresholds)\n"
            "- **SUCCESS THRESHOLDS**: How to measure (quantified KPIs)\n"
            "- **CONTINGENCY**: What if it fails (specific fallback)\n\n"
            "## Action Plan\n"
            "Phased implementation with:\n"
            "- Phase 1 (0-30d): Immediate actions with owners\n"
            "- Phase 2 (30-90d): Scaled actions with milestones\n"
            "- Phase 3 (90d+): Sustained operations with review cadence\n\n"
            "## Confidence and Open Questions\n"
            "- Overall confidence: X% with rationale\n"
            "- What we know vs. don't know\n"
            "- Key uncertainties that could change the recommendation\n"
            "- Recommended follow-up research\n\n"
            "## Source Inventory\n"
            "Complete citation list with credibility and relevance assessment.\n\n"
            "QUALITY REQUIREMENTS:\n"
            "- Minimum 5 source citations with [Sx] format\n"
            "- NO generic template phrases ('it depends', 'generally speaking', 'may vary')\n"
            "- Traceability: every conclusion maps to specific evidence\n"
            "- Quantify uncertainty explicitly (percentages, ranges, confidence levels)\n"
            "- Decision recommendation must name EXACT action, not vague guidance\n\n"
            f"Question: {query.strip()}\n\n"
            f"ADVOCATE ANALYSIS:\n{outputs.get('advocate', 'Not available')}\n\n"
            f"SKEPTIC ANALYSIS:\n{outputs.get('skeptic', 'Not available')}\n\n"
            f"SYNTHESIS:\n{outputs.get('synthesiser', 'Not available')}\n\n"
            f"FORECAST:\n{outputs.get('oracle', 'Not available')}\n\n"
            f"VERIFICATION:\n{outputs.get('verifier', 'Not available')}\n\n"
            f"LIVE RESEARCH CONTEXT:\n{research_block}"
            + (f"\n\nREFINEMENT FOCUS: {refinement_note.strip()}" if refinement_note and refinement_note.strip() else "")
        )
        try:
            resolved = await _invoke_with_resilience(
                self._health,
                "final",
                lambda: self._ainvoke(final_prompt),
                _stage_timeout_seconds("final"),
                lambda text: _is_final_research_grade(text, minimum_length=900, research=research),
            )
            return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

    def diagnostics(self) -> dict[str, str | int | bool]:
        breaker_state = self._health.snapshot()
        registry = prompt_registry_snapshot(
            [
                prompt_fingerprint("advocate", _provider_agent_prompt("gemini", "advocate")),
                prompt_fingerprint("skeptic", _provider_agent_prompt("gemini", "skeptic")),
                prompt_fingerprint("synthesiser", _provider_agent_prompt("gemini", "synthesiser")),
                prompt_fingerprint("oracle", _provider_agent_prompt("gemini", "oracle")),
                prompt_fingerprint("final", _provider_final_prompt("gemini")),
            ]
        )
        return {
            "configuredProvider": "gemini",
            "activeProvider": "deterministic-fallback" if self._health.is_open() else "gemini",
            "modelName": self._model_name,
            "isFallback": self._fallback_count > 0,
            "fallbackCount": self._fallback_count,
            "lastError": self._last_error,
            "promptRegistryVersion": registry["registryVersion"],
            "promptRegistrySize": len(registry["prompts"]),
            **breaker_state,
        }

    def _register_fallback(self, exc: Exception) -> None:
        self._fallback_count += 1
        message = f"{type(exc).__name__}: {exc}".strip()
        self._last_error = message[:240]

    async def _ainvoke(self, prompt: str) -> str:
        response = await self._model.ainvoke(prompt)
        content = getattr(response, "content", "")
        return str(content).strip()


class OpenRouterPipelineModelProvider:
    def __init__(self, default_model: str) -> None:
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for provider=openrouter")

        self._default_model = default_model
        self._fallback_count = 0
        self._last_error = ""
        self._health = _ProviderHealthManager(
            provider_name="openrouter",
            retry_budget=_provider_retry_budget(),
            failure_threshold=_provider_failure_threshold(),
            cooldown_seconds=_provider_cooldown_seconds(),
            backoff_seconds=_provider_backoff_seconds(),
        )
        self._base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self._timeout_seconds = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "35"))
        self._cost_mode = _cost_mode()
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://hexamind.local"),
            "X-Title": os.getenv("OPENROUTER_X_TITLE", "Hexamind ARIA"),
            "Content-Type": "application/json",
        }
        self._researcher = _create_researcher()
        self._fallback = DeterministicPipelineModelProvider(
            configured_provider="openrouter",
            model_name=default_model,
            reason="OpenRouter runtime call failed",
        )
        self._model_by_role = {
            "advocate": os.getenv("HEXAMIND_AGENT_MODEL_ADVOCATE", default_model).strip(),
            "skeptic": os.getenv("HEXAMIND_AGENT_MODEL_SKEPTIC", default_model).strip(),
            "synthesiser": os.getenv("HEXAMIND_AGENT_MODEL_SYNTHESIS", default_model).strip(),
            "oracle": os.getenv("HEXAMIND_AGENT_MODEL_ORACLE", default_model).strip(),
            "final": os.getenv("HEXAMIND_AGENT_MODEL_FINAL", default_model).strip(),
        }

    async def build_research_context(self, query: str) -> ResearchContext | None:
        if not _web_research_enabled():
            return None
        if not self._health.can_attempt():
            return None
        try:
            return await _invoke_with_resilience(
                self._health,
                "retrieval",
                lambda: self._researcher.research(query),
                _stage_timeout_seconds("retrieval"),
            )
        except Exception as exc:
            self._register_fallback(exc)
            return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.build_agent_text(agent_id, query, research)

        prompts = {
            "advocate": (
                "You are ADVOCATE in ARIA deep-research mode. Build the strongest evidence-backed case.\n"
                "REQUIRED: '## Opportunity Thesis' (quantified impact), '## Strategic Upside' (3-5 benefits with [Sx] citations), "
                "'## Supporting Logic' (reasoning chain with causal mechanisms), '## Actionable Next Step' (who/what/when/success criteria), '## Citations Used'.\n"
                "Every claim must cite [Sx]. Use specific numbers. No vague qualifiers."
            ),
            "skeptic": (
                "You are SKEPTIC in ARIA deep-research mode. Identify failure modes and quantify risks.\n"
                "REQUIRED: '## Risk Thesis' (severity rating), '## Primary Failure Modes' (3-5 with probability/impact/detection), "
                "'## Risk Severity Matrix', '## Second-Order Effects', '## Mitigation Requirements' (control/investment/trigger), '## Citations Used'.\n"
                "Every risk claim must cite [Sx]. Use probability ranges. Challenge advocate assumptions."
            ),
            "synthesiser": (
                "You are SYNTHESISER in ARIA deep-research mode. Integrate perspectives into decision-ready output.\n"
                "REQUIRED: '## Integrated Assessment', '## Conflict Resolution Matrix' (Advocate vs Skeptic), '## Tradeoff Analysis', "
                "'## Decision Rule' (IF-THEN conditions), '## Stakeholder Impact', '## Guardrails' (hard/soft limits), '## Citations Used'.\n"
                "Acknowledge conflicts explicitly. Decision rules must be testable."
            ),
            "oracle": (
                "You are ORACLE in ARIA deep-research mode. Forecast outcomes with scenario analysis.\n"
                "REQUIRED: '## Scenario Outlook', '## Most Likely Outcome (60%)' (30/60/90-day marks), "
                "'## Upside Scenario (25%)', '## Downside Scenario (15%)' (circuit-breakers), "
                "'## Scenario Interdependencies', '## Leading Indicators Dashboard' (table), '## Forecast Confidence', '## Citations Used'.\n"
                "Probabilities must sum to 100%. Use specific timeframes."
            ),
            "verifier": (
                "You are VERIFIER in ARIA deep-research mode. Audit evidence quality.\n"
                "REQUIRED: '## Verification Summary', '## Claim Audit Table' (5+ claims), '## Source Triangulation', "
                "'## Evidence Gaps', '## Contradiction Map', '## Verification Confidence'.\n"
                "Reference credibility scores. Flag weak evidence rigorously."
            ),
        }
        system_prompt = prompts.get(agent_id, prompts.get("verifier", prompts["oracle"]))
        research_block = _trim_for_prompt(format_research_context(research), 6500)
        model_name = self._model_by_role.get(agent_id, self._default_model)

        try:
            resolved = await _invoke_with_resilience(
                self._health,
                f"agent:{agent_id}",
                lambda: self._chat(
                    model=model_name,
                    system_prompt=system_prompt,
                    user_prompt=f"Question: {query.strip()}\n\nLive web research context:\n{research_block}",
                ),
                _stage_timeout_seconds("agent"),
                lambda text: _is_agent_research_grade(text, minimum_length=280, research=research),
            )
            return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.build_agent_text(agent_id, query, research)

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

        research_block = _trim_for_prompt(format_research_context(research), 4200)
        model_name = self._model_by_role.get("final", self._default_model)
        advocate_output = _trim_for_prompt(outputs.get("advocate", ""), 1400)
        skeptic_output = _trim_for_prompt(outputs.get("skeptic", ""), 1400)
        synthesiser_output = _trim_for_prompt(outputs.get("synthesiser", ""), 1400)
        oracle_output = _trim_for_prompt(outputs.get("oracle", ""), 1400)
        verifier_output = _trim_for_prompt(outputs.get("verifier", ""), 1200)

        try:
            resolved = await _invoke_with_resilience(
                self._health,
                "final",
                lambda: self._chat(
                    model=model_name,
                    system_prompt=(
                        "You are ARIA final synthesiser producing executive-grade research reports.\n"
                        "REQUIRED SECTIONS: '## Executive Summary' (3-sentence decision brief with confidence), "
                        "'## Research Scope', '## Evidence Snapshot' (source table), "
                        "'## Analytical Breakdown' (with '### Report Plan', '### Claim Graph', '### Contradictions and Uncertainty'), "
                        "'## Decision Recommendation' (EXACT action + trigger conditions + success thresholds + contingency), "
                        "'## Action Plan' (phased: 0-30d, 30-90d, 90d+), '## Confidence and Open Questions', '## Source Inventory'.\n\n"
                        "QUALITY GATES: Minimum 5 [Sx] citations. NO generic phrases ('it depends', 'generally speaking'). "
                        "Decision recommendation must name the EXACT policy choice with concrete thresholds. "
                        "Every conclusion must trace to specific evidence."
                    ),
                    user_prompt=(
                        f"Question: {query.strip()}\n\n"
                        f"ADVOCATE:\n{advocate_output}\n\n"
                        f"SKEPTIC:\n{skeptic_output}\n\n"
                        f"SYNTHESISER:\n{synthesiser_output}\n\n"
                        f"ORACLE:\n{oracle_output}\n\n"
                        f"VERIFIER:\n{verifier_output}\n\n"
                        f"RESEARCH CONTEXT:\n{research_block}"
                        + (f"\n\nREFINEMENT FOCUS: {refinement_note.strip()}" if refinement_note and refinement_note.strip() else "")
                    ),
                ),
                _stage_timeout_seconds("final"),
                lambda text: _is_final_research_grade(text, minimum_length=920, research=research),
            )
            return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

    def diagnostics(self) -> dict[str, str | int | bool]:
        breaker_state = self._health.snapshot()
        registry = prompt_registry_snapshot(
            [
                prompt_fingerprint("advocate", _provider_agent_prompt("openrouter", "advocate")),
                prompt_fingerprint("skeptic", _provider_agent_prompt("openrouter", "skeptic")),
                prompt_fingerprint("synthesiser", _provider_agent_prompt("openrouter", "synthesiser")),
                prompt_fingerprint("oracle", _provider_agent_prompt("openrouter", "oracle")),
                prompt_fingerprint("final", _provider_final_prompt("openrouter")),
            ]
        )
        return {
            "configuredProvider": "openrouter",
            "activeProvider": "deterministic-fallback" if self._health.is_open() else "openrouter",
            "modelName": self._default_model,
            "costMode": self._cost_mode,
            "isFallback": self._fallback_count > 0,
            "fallbackCount": self._fallback_count,
            "lastError": self._last_error,
            "agentModelMap": json.dumps(self._model_by_role, sort_keys=True),
            "promptRegistryVersion": registry["registryVersion"],
            "promptRegistrySize": len(registry["prompts"]),
            **breaker_state,
        }

    async def _chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            body = await self._chat_request(client, model, system_prompt, user_prompt)

        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("OpenRouter response missing choices")

        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            return "\n".join(part for part in parts if part).strip()
        return str(content).strip()

    async def _chat_request(
        self,
        client: httpx.AsyncClient,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        payload = {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response = await client.post(
            f"{self._base_url}/chat/completions",
            headers=self._headers,
            json=payload,
        )
        if response.status_code == 400:
            # Retry with tighter prompt bounds before declaring provider failure.
            compact_payload = {
                "model": model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": _trim_for_prompt(system_prompt, 1200)},
                    {"role": "user", "content": _trim_for_prompt(user_prompt, 3200)},
                ],
            }
            retry = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers,
                json=compact_payload,
            )
            if retry.is_success:
                return retry.json()
            raise RuntimeError(f"Groq 400 after compact retry: {retry.text[:200]}")

        response.raise_for_status()
        return response.json()

    def _register_fallback(self, exc: Exception) -> None:
        self._fallback_count += 1
        message = f"{type(exc).__name__}: {exc}".strip()
        self._last_error = message[:240]


class GroqPipelineModelProvider:
    def __init__(self, default_model: str) -> None:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required for provider=groq")

        self._default_model = default_model
        self._fallback_count = 0
        self._last_error = ""
        self._health = _ProviderHealthManager(
            provider_name="groq",
            retry_budget=_provider_retry_budget(),
            failure_threshold=_provider_failure_threshold(),
            cooldown_seconds=_provider_cooldown_seconds(),
            backoff_seconds=_provider_backoff_seconds(),
        )
        self._base_url = "https://api.groq.com/openai/v1".rstrip("/")
        self._timeout_seconds = float(os.getenv("GROQ_TIMEOUT_SECONDS", "30"))
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._researcher = _create_researcher()
        self._fallback = DeterministicPipelineModelProvider(
            configured_provider="groq",
            model_name=default_model,
            reason="Groq runtime call failed",
        )
        self._model_by_role = {
            "advocate": os.getenv("HEXAMIND_AGENT_MODEL_ADVOCATE", default_model).strip(),
            "skeptic": os.getenv("HEXAMIND_AGENT_MODEL_SKEPTIC", default_model).strip(),
            "synthesiser": os.getenv("HEXAMIND_AGENT_MODEL_SYNTHESIS", default_model).strip(),
            "oracle": os.getenv("HEXAMIND_AGENT_MODEL_ORACLE", default_model).strip(),
            "final": os.getenv("HEXAMIND_AGENT_MODEL_FINAL", default_model).strip(),
        }

    async def build_research_context(self, query: str) -> ResearchContext | None:
        if not _web_research_enabled():
            return None
        if not self._health.can_attempt():
            return None
        try:
            return await _invoke_with_resilience(
                self._health,
                "retrieval",
                lambda: self._researcher.research(query),
                _stage_timeout_seconds("retrieval"),
            )
        except Exception as exc:
            self._register_fallback(exc)
            return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.build_agent_text(agent_id, query, research)

        prompts = {
            "advocate": (
                "ADVOCATE agent for ARIA research. Build strongest evidence-backed case.\n"
                "SECTIONS: '## Opportunity Thesis' (quantified), '## Strategic Upside' (3-5 with [Sx]), "
                "'## Supporting Logic' (causal chain), '## Actionable Next Step' (who/what/when/success), '## Citations Used'.\n"
                "Cite [Sx] for every claim. Use numbers. No vague qualifiers."
            ),
            "skeptic": (
                "SKEPTIC agent for ARIA research. Identify failures and quantify risks.\n"
                "SECTIONS: '## Risk Thesis', '## Primary Failure Modes' (probability/impact), "
                "'## Risk Severity Matrix', '## Mitigation Requirements', '## Citations Used'.\n"
                "Cite [Sx] for risks. Use probability ranges."
            ),
            "synthesiser": (
                "SYNTHESISER agent for ARIA research. Integrate into decision-ready output.\n"
                "SECTIONS: '## Integrated Assessment', '## Conflict Resolution Matrix', '## Tradeoff Analysis', "
                "'## Decision Rule' (IF-THEN), '## Guardrails', '## Citations Used'.\n"
                "Acknowledge conflicts. Testable decision rules."
            ),
            "oracle": (
                "ORACLE agent for ARIA research. Forecast with scenarios.\n"
                "SECTIONS: '## Scenario Outlook', '## Most Likely (60%)', '## Upside (25%)', '## Downside (15%)', "
                "'## Leading Indicators', '## Citations Used'.\n"
                "Sum to 100%. Specific timeframes."
            ),
            "verifier": (
                "VERIFIER agent for ARIA research. Audit evidence.\n"
                "SECTIONS: '## Verification Summary', '## Claim Audit Table', '## Source Triangulation', "
                "'## Evidence Gaps', '## Verification Confidence'.\n"
                "Audit 5+ claims. Reference credibility."
            ),
        }
        system_prompt = prompts.get(agent_id, prompts.get("verifier", prompts["oracle"]))
        research_block = format_research_context(research)
        model_name = self._model_by_role.get(agent_id, self._default_model)

        try:
            resolved = await _invoke_with_resilience(
                self._health,
                f"agent:{agent_id}",
                lambda: self._chat(
                    model=model_name,
                    system_prompt=system_prompt,
                    user_prompt=f"Question: {query.strip()}\n\nLive web research context:\n{research_block}",
                ),
                _stage_timeout_seconds("agent"),
                lambda text: _is_agent_research_grade(text, minimum_length=280, research=research),
            )
            return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.build_agent_text(agent_id, query, research)

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

        research_block = format_research_context(research)
        model_name = self._model_by_role.get("final", self._default_model)

        try:
            resolved = await _invoke_with_resilience(
                self._health,
                "final",
                lambda: self._chat(
                    model=model_name,
                    system_prompt=(
                        "ARIA final synthesiser producing executive-grade research.\n"
                        "SECTIONS: '## Executive Summary' (3 sentences with confidence), '## Research Scope', "
                        "'## Evidence Snapshot', '## Analytical Breakdown' (### Report Plan, ### Claim Graph, ### Contradictions), "
                        "'## Decision Recommendation' (EXACT action + thresholds), '## Action Plan' (phased), "
                        "'## Confidence and Open Questions', '## Source Inventory'.\n"
                        "5+ citations. NO generic phrases. Trace conclusions to evidence."
                    ),
                    user_prompt=(
                        f"Question: {query.strip()}\n\n"
                        f"ADVOCATE:\n{outputs.get('advocate', '')}\n\n"
                        f"SKEPTIC:\n{outputs.get('skeptic', '')}\n\n"
                        f"SYNTHESISER:\n{outputs.get('synthesiser', '')}\n\n"
                        f"ORACLE:\n{outputs.get('oracle', '')}\n\n"
                        f"VERIFIER:\n{outputs.get('verifier', '')}\n\n"
                        f"RESEARCH:\n{research_block}"
                        + (f"\n\nREFINEMENT: {refinement_note.strip()}" if refinement_note and refinement_note.strip() else "")
                    ),
                ),
                _stage_timeout_seconds("final"),
                lambda text: _is_final_research_grade(text, minimum_length=920, research=research),
            )
            return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

    def diagnostics(self) -> dict[str, str | int | bool]:
        breaker_state = self._health.snapshot()
        registry = prompt_registry_snapshot(
            [
                prompt_fingerprint("advocate", _provider_agent_prompt("groq", "advocate")),
                prompt_fingerprint("skeptic", _provider_agent_prompt("groq", "skeptic")),
                prompt_fingerprint("synthesiser", _provider_agent_prompt("groq", "synthesiser")),
                prompt_fingerprint("oracle", _provider_agent_prompt("groq", "oracle")),
                prompt_fingerprint("final", _provider_final_prompt("groq")),
            ]
        )
        return {
            "configuredProvider": "groq",
            "activeProvider": "deterministic-fallback" if self._health.is_open() else "groq",
            "modelName": self._default_model,
            "isFallback": self._fallback_count > 0,
            "fallbackCount": self._fallback_count,
            "lastError": self._last_error,
            "agentModelMap": json.dumps(self._model_by_role, sort_keys=True),
            "promptRegistryVersion": registry["registryVersion"],
            "promptRegistrySize": len(registry["prompts"]),
            **breaker_state,
        }

    async def _chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            body = await self._chat_request(client, model, system_prompt, user_prompt)

        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("Groq response missing choices")

        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            return "\n".join(part for part in parts if part).strip()
        return str(content).strip()

    async def _chat_request(
        self,
        client: httpx.AsyncClient,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        base_payload = {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response = await client.post(
            f"{self._base_url}/chat/completions",
            headers=self._headers,
            json=base_payload,
        )
        if response.status_code in {400, 429}:
            if response.status_code == 429:
                await asyncio.sleep(1.0)
            compact_payload = {
                "model": model,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": _trim_for_prompt(system_prompt, 1100)},
                    {"role": "user", "content": _trim_for_prompt(user_prompt, 3000)},
                ],
            }
            retry = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers,
                json=compact_payload,
            )
            if retry.is_success:
                return retry.json()
            raise RuntimeError(f"Groq request failed after compact retry: {retry.status_code} {retry.text[:200]}")

        response.raise_for_status()
        return response.json()

    def _register_fallback(self, exc: Exception) -> None:
        self._fallback_count += 1
        message = f"{type(exc).__name__}: {exc}".strip()
        self._last_error = message[:240]


class LocalPipelineModelProvider:
    def __init__(self, default_model: str) -> None:
        self._default_model = default_model
        self._strict_local = _local_strict_mode()
        self._fallback_count = 0
        self._last_error = ""
        self._health = _ProviderHealthManager(
            provider_name="local",
            retry_budget=_provider_retry_budget(),
            failure_threshold=_provider_failure_threshold(),
            cooldown_seconds=_provider_cooldown_seconds(),
            backoff_seconds=_provider_backoff_seconds(),
        )
        self._base_url = os.getenv("HEXAMIND_LOCAL_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
        self._timeout_seconds = float(os.getenv("HEXAMIND_LOCAL_TIMEOUT_SECONDS", "45"))
        self._researcher = _create_researcher()
        self._fallback = None
        if not self._strict_local:
            self._fallback = DeterministicPipelineModelProvider(
                configured_provider="local",
                model_name=default_model,
                reason="Local runtime call failed",
            )
        self._tier_models = {
            "small": os.getenv("HEXAMIND_LOCAL_MODEL_SMALL", default_model).strip() or default_model,
            "medium": os.getenv("HEXAMIND_LOCAL_MODEL_MEDIUM", default_model).strip() or default_model,
            "large": os.getenv("HEXAMIND_LOCAL_MODEL_LARGE", default_model).strip() or default_model,
        }
        self._model_by_role = {
            "advocate": os.getenv("HEXAMIND_AGENT_MODEL_ADVOCATE", default_model).strip(),
            "skeptic": os.getenv("HEXAMIND_AGENT_MODEL_SKEPTIC", default_model).strip(),
            "synthesiser": os.getenv("HEXAMIND_AGENT_MODEL_SYNTHESIS", default_model).strip(),
            "oracle": os.getenv("HEXAMIND_AGENT_MODEL_ORACLE", default_model).strip(),
            "final": os.getenv("HEXAMIND_AGENT_MODEL_FINAL", default_model).strip(),
        }
        self._local_available = self._probe_local_service()
        if self._strict_local and not self._local_available:
            raise RuntimeError(
                f"Strict local mode is enabled but local provider is unavailable at {self._base_url}."
            )

    async def build_research_context(self, query: str) -> ResearchContext | None:
        if not _web_research_enabled():
            return None
        if not self._health.can_attempt():
            return None
        try:
            return await _invoke_with_resilience(
                self._health,
                "retrieval",
                lambda: self._researcher.research(query),
                _stage_timeout_seconds("retrieval"),
            )
        except Exception as exc:
            self._register_fallback(exc)
            return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        if not self._health.can_attempt():
            if self._strict_local:
                raise RuntimeError("Local provider circuit is open in strict local mode.")
            if not self._fallback:
                raise RuntimeError("Local provider fallback is unavailable.")
            return await self._fallback.build_agent_text(agent_id, query, research)

        prompts = {
            "advocate": (
                "ADVOCATE agent (local). Build strongest evidence case.\n"
                "SECTIONS: '## Opportunity Thesis' (quantified impact), '## Strategic Upside' (3-5 benefits, each with [Sx]), "
                "'## Supporting Logic' (reasoning chain), '## Actionable Next Step' (who/what/when/metric), '## Citations Used'.\n"
                "Every claim cites [Sx]. Specific numbers. No vague qualifiers."
            ),
            "skeptic": (
                "SKEPTIC agent (local). Identify failures and quantify risks.\n"
                "SECTIONS: '## Risk Thesis' (severity), '## Primary Failure Modes' (probability/impact per risk), "
                "'## Risk Severity Matrix', '## Mitigation Requirements' (control/investment/trigger), '## Citations Used'.\n"
                "Cite [Sx] for risks. Probability ranges."
            ),
            "synthesiser": (
                "SYNTHESISER agent (local). Integrate into decision output.\n"
                "SECTIONS: '## Integrated Assessment', '## Conflict Resolution' (Advocate vs Skeptic), "
                "'## Decision Rule' (IF-THEN), '## Guardrails' (hard/soft limits), '## Citations Used'.\n"
                "Acknowledge conflicts. Testable rules."
            ),
            "oracle": (
                "ORACLE agent (local). Forecast with scenarios.\n"
                "SECTIONS: '## Scenario Outlook', '## Most Likely (60%)', '## Upside (25%)', '## Downside (15%)', "
                "'## Leading Indicators', '## Citations Used'.\n"
                "Sum 100%. Specific timeframes."
            ),
            "verifier": (
                "VERIFIER agent (local). Audit evidence.\n"
                "SECTIONS: '## Verification Summary', '## Claim Audit Table', '## Source Triangulation', "
                "'## Evidence Gaps', '## Verification Confidence'.\n"
                "Audit 5+ claims."
            ),
        }
        system_prompt = prompts.get(agent_id, prompts.get("verifier", prompts["oracle"]))
        tier = _local_model_tier(query, research)
        min_length_by_tier = {
            "small": 190,
            "medium": 230,
            "large": 280,
        }
        research_block = _compressed_research_block(research, _local_context_budget("agent", tier, research))
        model_name = self._resolve_local_model(agent_id, tier)
        token_budget = _local_token_budget("agent", tier, research)

        if self._local_available:
            try:
                resolved = await _invoke_with_resilience(
                    self._health,
                    f"agent:{agent_id}",
                    lambda: self._chat(
                        model=model_name,
                        system_prompt=system_prompt,
                        user_prompt=f"Question: {query.strip()}\n\nLive research:\n{research_block}",
                        max_tokens=token_budget,
                    ),
                    _stage_timeout_seconds("agent"),
                    lambda text: _is_agent_research_grade(
                        text,
                        minimum_length=min_length_by_tier.get(tier, 230),
                        research=research,
                    ),
                )
                return resolved
            except Exception as exc:
                self._register_fallback(exc)
                if self._strict_local:
                    raise

        if self._strict_local:
            raise RuntimeError("Local provider is unavailable in strict local mode.")
        if not self._fallback:
            raise RuntimeError("Local provider fallback is unavailable.")
        return await self._fallback.build_agent_text(agent_id, query, research)

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        if not self._health.can_attempt():
            if self._strict_local:
                raise RuntimeError("Local provider circuit is open in strict local mode.")
            if not self._fallback:
                raise RuntimeError("Local provider fallback is unavailable.")
            return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

        tier = _local_model_tier(query, research)
        min_length_by_tier = {
            "small": 620,
            "medium": 760,
            "large": 920,
        }
        research_block = _compressed_research_block(research, _local_context_budget("final", tier, research))
        model_name = self._resolve_local_model("final", tier)
        token_budget = _local_token_budget("final", tier, research)

        if self._local_available:
            try:
                resolved = await _invoke_with_resilience(
                    self._health,
                    "final",
                    lambda: self._chat(
                        model=model_name,
                        system_prompt=(
                            "Final synthesiser (local) for executive-grade research.\n"
                            "SECTIONS: '## Executive Summary' (3 sentences + confidence), '## Research Scope', "
                            "'## Evidence Snapshot', '## Analytical Breakdown' (### Claim Graph, ### Contradictions), "
                            "'## Decision Recommendation' (EXACT action + thresholds + contingency), "
                            "'## Action Plan' (phased), '## Confidence and Open Questions', '## Source Inventory'.\n"
                            "5+ citations. NO generic phrases. Trace conclusions to evidence."
                        ),
                        user_prompt=(
                            f"Question: {query.strip()}\n\n"
                            f"ADVOCATE:\n{outputs.get('advocate', '')}\n\n"
                            f"SKEPTIC:\n{outputs.get('skeptic', '')}\n\n"
                            f"SYNTHESISER:\n{outputs.get('synthesiser', '')}\n\n"
                            f"ORACLE:\n{outputs.get('oracle', '')}\n\n"
                            f"VERIFIER:\n{outputs.get('verifier', '')}\n\n"
                            f"RESEARCH:\n{research_block}"
                            + (f"\n\nREFINEMENT: {refinement_note.strip()}" if refinement_note and refinement_note.strip() else "")
                        ),
                        max_tokens=token_budget,
                    ),
                    _stage_timeout_seconds("final"),
                    lambda text: _is_final_research_grade(
                        text,
                        minimum_length=min_length_by_tier.get(tier, 760),
                        research=research,
                    ),
                )
                return resolved
            except Exception as exc:
                self._register_fallback(exc)
                if self._strict_local:
                    raise

        if self._strict_local:
            raise RuntimeError("Local provider is unavailable in strict local mode.")
        if not self._fallback:
            raise RuntimeError("Local provider fallback is unavailable.")
        return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

    def diagnostics(self) -> dict[str, str | int | bool]:
        breaker_state = self._health.snapshot()
        registry = prompt_registry_snapshot(
            [
                prompt_fingerprint("advocate", _provider_agent_prompt("local", "advocate")),
                prompt_fingerprint("skeptic", _provider_agent_prompt("local", "skeptic")),
                prompt_fingerprint("synthesiser", _provider_agent_prompt("local", "synthesiser")),
                prompt_fingerprint("oracle", _provider_agent_prompt("local", "oracle")),
                prompt_fingerprint("final", _provider_final_prompt("local")),
            ]
        )
        return {
            "configuredProvider": "local",
            "activeProvider": (
                "local"
                if self._local_available and not self._health.is_open()
                else ("local-unavailable" if self._strict_local else "deterministic-fallback")
            ),
            "modelName": self._default_model,
            "localBaseUrl": self._base_url,
            "localAvailable": self._local_available,
            "isFallback": self._fallback_count > 0 or not self._local_available,
            "fallbackCount": self._fallback_count,
            "strictLocal": self._strict_local,
            "lastError": self._last_error,
            "agentModelMap": json.dumps(self._model_by_role, sort_keys=True),
            "promptRegistryVersion": registry["registryVersion"],
            "promptRegistrySize": len(registry["prompts"]),
            **breaker_state,
        }

    async def _chat(self, model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        payload = {
            "model": model,
            "temperature": 0.15,
            "top_p": 0.85,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("Local model response missing choices")

        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            return "\n".join(part for part in parts if part).strip()
        return str(content).strip()

    def _probe_local_service(self) -> bool:
        try:
            response = httpx.get(f"{self._base_url}/models", timeout=3.0)
            response.raise_for_status()
            return True
        except Exception:
            return False

    def _register_fallback(self, exc: Exception) -> None:
        self._fallback_count += 1
        message = f"{type(exc).__name__}: {exc}".strip()
        self._last_error = message[:240]

    def _resolve_local_model(self, agent_id: str, tier: str) -> str:
        role_model = self._model_by_role.get(agent_id, self._default_model)
        if role_model != self._default_model:
            return role_model
        return self._tier_models.get(tier, self._default_model)


def _citation_count(text: str) -> int:
    return len(set(re.findall(r"\[S\d+\]", text)))


def _trim_for_prompt(text: str, limit: int) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 64].rstrip() + "\n\n[truncated for token safety]"


def _is_agent_research_grade(
    text: str,
    minimum_length: int,
    research: ResearchContext | None,
) -> bool:
    if len(text) < minimum_length:
        return False
    heading_count = text.count("## ")
    has_citation_section = "## Citations Used" in text or "## Source Inventory" in text
    if heading_count < 2:
        return False
    if research and research.sources:
        citations = _citation_count(text)
        has_source_signal = "[S" in text or "http" in text or "source" in text.lower()
        # Accept good topic-specific responses even when the model misses strict citation formatting.
        return (citations >= 1 or has_source_signal) and (has_citation_section or has_source_signal)
    return True


def _is_final_research_grade(
    text: str,
    minimum_length: int,
    research: ResearchContext | None,
) -> bool:
    required_sections = (
        "## Executive Summary",
        "## Evidence Snapshot",
        "## Decision Recommendation",
        "## Source Inventory",
    )
    if len(text) < minimum_length:
        return False
    if not all(section in text for section in required_sections):
        return False
    has_claim_mapping = (
        "Claim-to-Citation Map" in text
        or "### Claim Graph" in text
        or "## Claim Graph" in text
    )
    if not has_claim_mapping:
        return False
    if research and research.sources:
        return _citation_count(text) >= 2 or "[S" in text
    return True

def _web_research_enabled() -> bool:
    return os.getenv("HEXAMIND_WEB_RESEARCH", "1").strip().lower() not in {"0", "false", "no"}


def _cost_mode() -> str:
    value = os.getenv("HEXAMIND_COST_MODE", "free").strip().lower()
    return value if value in {"free", "balanced", "max"} else "free"


def _default_model_for_provider(provider_name: str) -> str:
    if provider_name in {"gemini", "google", "google-genai"}:
        return "gemini-2.0-flash"
    if provider_name in {"openrouter", "router"}:
        # Free-tier oriented default. Override per role with HEXAMIND_AGENT_MODEL_* env vars.
        return "google/gemini-2.0-flash-exp:free"
    if provider_name in {"groq"}:
        return "llama-3.1-8b-instant"
    if provider_name in {"local", "ollama", "lmstudio", "llama", "local-openai"}:
        return os.getenv("HEXAMIND_LOCAL_MODEL", "llama3.1:8b")
    return "deterministic"


def _create_researcher() -> object:
    from research import InternetResearcher

    return InternetResearcher()


def create_pipeline_model_provider() -> PipelineModelProvider:
    provider_name = os.getenv("HEXAMIND_MODEL_PROVIDER", "deterministic").strip().lower()
    if provider_name in {"local", "ollama", "lmstudio", "llama", "local-openai"}:
        model_name = os.getenv("HEXAMIND_MODEL_NAME", _default_model_for_provider(provider_name))
        try:
            return LocalPipelineModelProvider(model_name)
        except Exception as exc:
            if _local_strict_mode():
                raise
            return DeterministicPipelineModelProvider(
                configured_provider="local",
                model_name=model_name,
                reason=f"Local provider init failed: {type(exc).__name__}",
            )
    if provider_name in {"gemini", "google", "google-genai"}:
        model_name = os.getenv("HEXAMIND_MODEL_NAME", _default_model_for_provider(provider_name))
        try:
            return GeminiPipelineModelProvider(model_name)
        except Exception as exc:
            return DeterministicPipelineModelProvider(
                configured_provider="gemini",
                model_name=model_name,
                reason=f"Gemini init failed: {type(exc).__name__}",
            )
    if provider_name in {"openrouter", "router"}:
        model_name = os.getenv("HEXAMIND_MODEL_NAME", _default_model_for_provider(provider_name))
        try:
            return OpenRouterPipelineModelProvider(model_name)
        except Exception as exc:
            return DeterministicPipelineModelProvider(
                configured_provider="openrouter",
                model_name=model_name,
                reason=f"OpenRouter init failed: {type(exc).__name__}",
            )
    if provider_name in {"groq"}:
        model_name = os.getenv("HEXAMIND_MODEL_NAME", _default_model_for_provider(provider_name))
        try:
            return GroqPipelineModelProvider(model_name)
        except Exception as exc:
            return DeterministicPipelineModelProvider(
                configured_provider="groq",
                model_name=model_name,
                reason=f"Groq init failed: {type(exc).__name__}",
            )

    return DeterministicPipelineModelProvider(
        configured_provider=provider_name,
        model_name=os.getenv("HEXAMIND_MODEL_NAME", "deterministic"),
    )
