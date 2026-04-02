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

    lines = block.splitlines()
    prefix: list[str] = []
    source_lines: list[str] = []
    in_sources = False
    for line in lines:
        if not in_sources:
            if line.startswith(("Query:", "Search terms:", "Subquestions:")):
                prefix.append(line[:180].rstrip() + ("…" if len(line) > 180 else ""))
            else:
                prefix.append(line)
            if line.strip() == "Source pack:":
                in_sources = True
            continue
        source_lines.append(line)
        if len("\n".join(prefix + source_lines)) >= char_budget:
            break

    compressed = "\n".join(prefix + source_lines)
    return compressed[:char_budget].rstrip()


def _deterministic_prompt_text(agent_id: str) -> str:
    prompts = {
        "advocate": (
            "## Opportunity Thesis\n"
            "Produce a concise research-grounded advocate response with strategic upside, supporting logic, and an actionable next step."
        ),
        "skeptic": (
            "## Risk Thesis\n"
            "Produce a concise research-grounded skeptic response with failure modes, severity, and mitigation requirements."
        ),
        "synthesiser": (
            "## Integrated Assessment\n"
            "Produce a concise synthesis that resolves tradeoffs, gives a decision rule, and lists guardrails."
        ),
        "oracle": (
            "## Scenario Outlook\n"
            "Produce a concise forward-looking assessment with likely, upside, and downside scenarios plus leading indicators."
        ),
        "final": (
            "## Executive Summary\n"
            "Produce a thesis-style report with evidence snapshot, claim graph, contradictions, recommendation, action plan, and source inventory."
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

    async def build_research_context(self, query: str) -> ResearchContext | None:
        return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        q = query.strip()
        source_block = self._source_block(research)
        if agent_id == "advocate":
            return self._structured_advocate(q, source_block)
        if agent_id == "skeptic":
            return self._structured_skeptic(q, source_block)
        if agent_id == "synthesiser":
            return self._structured_synthesiser(q, source_block)
        return self._structured_oracle(q, source_block)

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
    ) -> str:
        q = query.strip()
        report_mode = self._report_mode(q, research)
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
            f"- Core question: {q}\n"
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
        return (
            "## Opportunity Thesis\n"
            f"Question: {query}\n\n"
            "## Strategic Upside\n"
            "- Potential to improve cycle time and decision quality if rollout is scoped.\n"
            "- Creates clearer accountability through explicit ownership and milestone tracking.\n"
            "- Enables compounding improvements via fast feedback loops.\n"
            f"- Live web grounding reviewed: {source_block}\n\n"
            "## Supporting Logic\n"
            "- Value is highest when initial use case is narrow and metrics are unambiguous.\n"
            "- Early instrumentation reduces rework and surfaces blockers quickly.\n"
            "- Current public sources should be used to validate operational feasibility before scaling.\n\n"
            "## Actionable Next Step\n"
            "Launch a pilot with one constrained workflow and pre-define success thresholds."
        )

    def _structured_skeptic(self, query: str, source_block: str) -> str:
        return (
            "## Risk Thesis\n"
            f"Question: {query}\n\n"
            "## Primary Failure Modes\n"
            "- Hidden integration complexity can erase projected gains.\n"
            "- Ambiguous ownership can cause quality regressions and missed deadlines.\n"
            "- Weak measurement design can produce false confidence.\n\n"
            "## Risk Severity\n"
            "- Execution risk: High if dependencies are not controlled.\n"
            "- Adoption risk: Medium if change management is underfunded.\n"
            "- Reliability risk: Medium to High without clear operational guardrails.\n\n"
            f"## Source Quality Check\n- Live evidence reviewed: {source_block}\n\n"
            "## Mitigation Requirement\n"
            "Define risk owners, trigger thresholds, and contingency actions before scale-up."
        )

    def _structured_synthesiser(self, query: str, source_block: str) -> str:
        return (
            "## Integrated Assessment\n"
            f"Question: {query}\n\n"
            "## Tradeoff Resolution\n"
            "- Upside is meaningful only when execution discipline is high.\n"
            "- Major risks are manageable with staged deployment and strict governance.\n"
            "- Recommendation depends on measurable checkpoint performance, not narrative confidence.\n\n"
            "## Decision Rule\n"
            "Proceed if pilot metrics exceed baseline and no critical risk trigger fires for two review cycles.\n\n"
            f"## Evidence Used\n- {source_block}\n\n"
            "## Guardrails\n"
            "- Maintain scope limits until stability and ROI are demonstrated.\n"
            "- Stop expansion immediately on quality or reliability regression."
        )

    def _structured_oracle(self, query: str, source_block: str) -> str:
        return (
            "## Scenario Outlook\n"
            f"Question: {query}\n\n"
            "## Most Likely Outcome (60%)\n"
            "Measured gains appear in the pilot phase, followed by cautious expansion.\n\n"
            "## Upside Scenario (25%)\n"
            "Early metric outperformance enables faster scale with manageable operational load.\n\n"
            "## Downside Scenario (15%)\n"
            "Dependency failures and weak adoption force rollback to a narrower operating model.\n\n"
            f"## Evidence Basis\n- {source_block}\n\n"
            "## Leading Indicators to Track\n"
            "- Cycle-time improvement vs baseline\n"
            "- Defect/reliability trend\n"
            "- User adoption and retention signal"
        )

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
                "You are the Advocate agent for a professional research workflow. "
                "Produce concise markdown with EXACT sections: "
                "'## Opportunity Thesis', '## Strategic Upside', '## Supporting Logic', "
                "'## Actionable Next Step'. Include specific, execution-oriented claims, "
                "and attach source IDs like [S1] to every non-trivial claim. End with "
                "'## Citations Used' listing each cited source ID and one-line relevance."
            ),
            "skeptic": (
                "You are the Skeptic agent for a professional research workflow. "
                "Produce concise markdown with EXACT sections: "
                "'## Risk Thesis', '## Primary Failure Modes', '## Risk Severity', "
                "'## Mitigation Requirement'. Quantify risk level where possible, and attach "
                "source IDs like [S1] to every major risk claim. End with "
                "'## Citations Used' listing each cited source ID and one-line relevance."
            ),
            "synthesiser": (
                "You are the Synthesiser agent for a professional research workflow. "
                "Produce concise markdown with EXACT sections: "
                "'## Integrated Assessment', '## Tradeoff Resolution', '## Decision Rule', "
                "'## Guardrails'. Resolve tradeoffs explicitly, include conflict notes when "
                "sources disagree, and cite [Sx] on each major claim. End with "
                "'## Citations Used' listing each cited source ID and one-line relevance."
            ),
            "oracle": (
                "You are the Oracle agent for a professional research workflow. "
                "Produce concise markdown with EXACT sections: "
                "'## Scenario Outlook', '## Most Likely Outcome (60%)', "
                "'## Upside Scenario (25%)', '## Downside Scenario (15%)', "
                "'## Leading Indicators to Track'. Use [Sx] citations for external evidence "
                "and end with '## Citations Used' listing each cited source ID and one-line relevance."
            ),
        }
        instruction = prompts.get(agent_id, prompts["oracle"])
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
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.compose_final_answer(query, outputs, research)

        research_block = format_research_context(research)
        try:
            resolved = await _invoke_with_resilience(
                self._health,
                "final",
                lambda: self._ainvoke(
                    "You are the final synthesiser for a professional multi-agent research pipeline. "
                    "Return a thesis-style markdown report with EXACT sections: "
                    "'## Executive Summary', '## Research Scope', '## Evidence Snapshot', "
                    "'## Analytical Breakdown', '## Decision Recommendation', '## Action Plan', "
                    "'## Confidence and Open Questions', '## Source Inventory'. "
                    "Use numbered subsections, bullet lists, and cite source IDs inline like [S1]. "
                    "Include a dynamic '### Report Plan', a '### Claim Graph', and a query-type-aware Analytical Breakdown. "
                    "If evidence is weak, state the gap explicitly instead of speculating. "
                    "The report should be detailed enough to fill a full A4 page and avoid generic wording.\n\n"
                    f"Question: {query.strip()}\n\n"
                    f"Support: {outputs.get('advocate', '')}\n"
                    f"Risks: {outputs.get('skeptic', '')}\n"
                    f"Synthesis: {outputs.get('synthesiser', '')}\n"
                    f"Outlook: {outputs.get('oracle', '')}"
                    f"\n\nLive web research context:\n{research_block}"
                ),
                _stage_timeout_seconds("final"),
                lambda text: _is_final_research_grade(text, minimum_length=900, research=research),
            )
            return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.compose_final_answer(query, outputs, research)

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
                "You are Advocate in ARIA deep-research mode. Output markdown with EXACT sections: "
                "'## Opportunity Thesis', '## Strategic Upside', '## Supporting Logic', "
                "'## Actionable Next Step', '## Citations Used'. Every non-trivial claim must include [Sx]."
            ),
            "skeptic": (
                "You are Skeptic in ARIA deep-research mode. Output markdown with EXACT sections: "
                "'## Risk Thesis', '## Primary Failure Modes', '## Risk Severity', "
                "'## Mitigation Requirement', '## Citations Used'. Every major risk must include [Sx]."
            ),
            "synthesiser": (
                "You are Synthesiser in ARIA deep-research mode. Output markdown with EXACT sections: "
                "'## Integrated Assessment', '## Tradeoff Resolution', '## Decision Rule', "
                "'## Guardrails', '## Contradictions Observed', '## Citations Used'. "
                "Mention source disagreements explicitly."
            ),
            "oracle": (
                "You are Oracle in ARIA deep-research mode. Output markdown with EXACT sections: "
                "'## Scenario Outlook', '## Most Likely Outcome (60%)', '## Upside Scenario (25%)', "
                "'## Downside Scenario (15%)', '## Leading Indicators to Track', '## Citations Used'. "
                "Ground forecasts with [Sx] citations."
            ),
        }
        system_prompt = prompts.get(agent_id, prompts["oracle"])
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
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.compose_final_answer(query, outputs, research)

        research_block = format_research_context(research)
        model_name = self._model_by_role.get("final", self._default_model)

        try:
            resolved = await _invoke_with_resilience(
                self._health,
                "final",
                lambda: self._chat(
                    model=model_name,
                    system_prompt=(
                        "You are ARIA final synthesiser in deep-research mode. Return markdown with EXACT sections: "
                        "'## Executive Summary', '## Research Scope', '## Evidence Snapshot', "
                        "'## Analytical Breakdown', '## Decision Recommendation', '## Action Plan', "
                        "'## Confidence and Open Questions', '## Source Inventory'. Under '## Analytical Breakdown' "
                        "include a dynamic '### Report Plan', '### Claim Graph', and '### Contradictions and Uncertainty'. "
                        "Every key claim must cite [Sx]. If evidence is weak, state the evidence gap explicitly."
                    ),
                    user_prompt=(
                        f"Question: {query.strip()}\n\n"
                        f"Advocate output:\n{outputs.get('advocate', '')}\n\n"
                        f"Skeptic output:\n{outputs.get('skeptic', '')}\n\n"
                        f"Synthesiser output:\n{outputs.get('synthesiser', '')}\n\n"
                        f"Oracle output:\n{outputs.get('oracle', '')}\n\n"
                        f"Live web research context:\n{research_block}"
                    ),
                ),
                _stage_timeout_seconds("final"),
                lambda text: _is_final_research_grade(text, minimum_length=920, research=research),
            )
            return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.compose_final_answer(query, outputs, research)

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
        payload = {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("OpenRouter response missing choices")

        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            return "\n".join(part for part in parts if part).strip()
        return str(content).strip()

    def _register_fallback(self, exc: Exception) -> None:
        self._fallback_count += 1
        message = f"{type(exc).__name__}: {exc}".strip()
        self._last_error = message[:240]


class LocalPipelineModelProvider:
    def __init__(self, default_model: str) -> None:
        self._default_model = default_model
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
                "You are the Advocate agent in local deep-research mode. Use the provided live evidence only. "
                "Produce concise markdown with EXACT sections: '## Opportunity Thesis', '## Strategic Upside', "
                "'## Supporting Logic', '## Actionable Next Step'. Avoid generic filler. Every non-trivial claim "
                "must cite a source ID like [S1]. End with '## Citations Used' listing each cited source ID and one-line relevance."
            ),
            "skeptic": (
                "You are the Skeptic agent in local deep-research mode. Use the provided live evidence only. "
                "Produce concise markdown with EXACT sections: '## Risk Thesis', '## Primary Failure Modes', "
                "'## Risk Severity', '## Mitigation Requirement'. Quantify risk where possible, avoid boilerplate, "
                "and cite [Sx] on each major risk claim. End with '## Citations Used' listing each cited source ID and one-line relevance."
            ),
            "synthesiser": (
                "You are the Synthesiser agent in local deep-research mode. Use the provided live evidence only. "
                "Produce concise markdown with EXACT sections: '## Integrated Assessment', '## Tradeoff Resolution', "
                "'## Decision Rule', '## Guardrails'. Resolve conflicts explicitly, explain why, and cite [Sx] on each major claim. "
                "End with '## Citations Used' listing each cited source ID and one-line relevance."
            ),
            "oracle": (
                "You are the Oracle agent in local deep-research mode. Use the provided live evidence only. "
                "Produce concise markdown with EXACT sections: '## Scenario Outlook', '## Most Likely Outcome (60%)', "
                "'## Upside Scenario (25%)', '## Downside Scenario (15%)', '## Leading Indicators to Track'. "
                "Forecast conservatively, avoid generic framing, and cite [Sx] for external evidence. End with '## Citations Used' listing each cited source ID and one-line relevance."
            ),
        }
        system_prompt = prompts.get(agent_id, prompts["oracle"])
        tier = _local_model_tier(query, research)
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
                        user_prompt=f"Question: {query.strip()}\n\nLive web research context:\n{research_block}",
                        max_tokens=token_budget,
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
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.compose_final_answer(query, outputs, research)

        tier = _local_model_tier(query, research)
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
                            "You are the final synthesiser in local deep-research mode. Return markdown with EXACT sections: "
                            "'## Executive Summary', '## Research Scope', '## Evidence Snapshot', '## Analytical Breakdown', "
                            "'## Decision Recommendation', '## Action Plan', '## Confidence and Open Questions', '## Source Inventory'. "
                            "Under '## Analytical Breakdown' include '### Claim-to-Citation Map' and '### Contradictions and Uncertainty'. "
                            "Use the live evidence only, avoid generic statements, and include a dynamic report plan plus claim graph."
                        ),
                        user_prompt=(
                            f"Question: {query.strip()}\n\n"
                            f"Advocate output:\n{outputs.get('advocate', '')}\n\n"
                            f"Skeptic output:\n{outputs.get('skeptic', '')}\n\n"
                            f"Synthesiser output:\n{outputs.get('synthesiser', '')}\n\n"
                            f"Oracle output:\n{outputs.get('oracle', '')}\n\n"
                            f"Live web research context:\n{research_block}"
                        ),
                        max_tokens=token_budget,
                    ),
                    _stage_timeout_seconds("final"),
                    lambda text: _is_final_research_grade(text, minimum_length=920, research=research),
                )
                return resolved
            except Exception as exc:
                self._register_fallback(exc)

        return await self._fallback.compose_final_answer(query, outputs, research)

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
            "activeProvider": "local" if self._local_available and not self._health.is_open() else "deterministic-fallback",
            "modelName": self._default_model,
            "localBaseUrl": self._base_url,
            "localAvailable": self._local_available,
            "isFallback": self._fallback_count > 0 or not self._local_available,
            "fallbackCount": self._fallback_count,
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


def _is_agent_research_grade(
    text: str,
    minimum_length: int,
    research: ResearchContext | None,
) -> bool:
    if len(text) < minimum_length:
        return False
    if "## " not in text or "## Citations Used" not in text:
        return False
    if research and research.sources:
        return _citation_count(text) >= min(2, len(research.sources))
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
    if "Claim-to-Citation Map" not in text:
        return False
    if research and research.sources:
        return _citation_count(text) >= min(4, len(research.sources))
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

    return DeterministicPipelineModelProvider(
        configured_provider=provider_name,
        model_name=os.getenv("HEXAMIND_MODEL_NAME", "deterministic"),
    )