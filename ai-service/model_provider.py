from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from research import ResearchContext, format_research_context, source_inventory_markdown


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
        source_block = self._source_block(research)
        source_inventory = source_inventory_markdown(research)
        support = outputs.get("advocate", "")
        risk = outputs.get("skeptic", "")
        synthesis = outputs.get("synthesiser", "")
        outlook = outputs.get("oracle", "")
        return (
            "## Executive Summary\n"
            f"The decision on '{q}' should be treated as a bounded research problem: gather current evidence, separate primary from secondary sources, and validate the recommendation through staged execution.\n\n"
            "## 1. Research Question and Scope\n"
            f"- Core question: {q}\n"
            "- Scope: current public evidence, implementation implications, and decision risks.\n"
            "- Method: internet search, page retrieval, source comparison, and structured synthesis.\n\n"
            "## 2. Evidence Snapshot\n"
            f"- Opportunity case: {self._extract_one_line(support, 'Strategic Upside', 'Opportunity Thesis')}\n"
            f"- Risk case: {self._extract_one_line(risk, 'Primary Failure Modes', 'Risk Thesis')}\n"
            f"- Integrated position: {self._extract_one_line(synthesis, 'Decision Rule', 'Integrated Assessment')}\n"
            f"- Forecast: {self._extract_one_line(outlook, 'Most Likely Outcome (60%)', 'Scenario Outlook')}\n\n"
            "## 3. Comparative Analysis\n"
            "### 3.1 What the evidence supports\n"
            f"- The live source pack indicates how the question is discussed on the web and where direct evidence exists. {source_block}\n"
            "- The strongest conclusion is not absolute certainty; it is a controlled path that preserves optionality.\n"
            "- The most defensible move is a pilot with measurable gates, not unconstrained scale.\n\n"
            "### 3.2 Where uncertainty remains\n"
            "- Source quality can vary widely across summaries, forums, and vendor material.\n"
            "- If current public evidence is thin, the report should explicitly label those gaps rather than infer them.\n"
            "- Operational risk remains material whenever ownership, dependencies, or measurement are unclear.\n\n"
            "## 4. Recommendation\n"
            "1. Proceed only with a narrow pilot and written success criteria.\n"
            "2. Require one owner per risk category and one metric per success claim.\n"
            "3. Expand only after the pilot meets the baseline and no critical triggers are active.\n\n"
            "## 5. 30-Day Action Plan\n"
            "- Week 1: confirm baseline, collect sources, and document assumptions.\n"
            "- Week 2: run a constrained pilot or desk evaluation.\n"
            "- Week 3: review performance, risks, and source contradictions.\n"
            "- Week 4: decide whether to scale, hold, or stop.\n\n"
            "## 6. Confidence and Open Questions\n"
            "- Confidence: Moderate, because the recommendation is grounded but still depends on the quality of current web evidence.\n"
            "- Open questions: whether the newest sources materially change the baseline, and which external dependencies are most fragile.\n\n"
            "## 7. Source Inventory\n"
            f"{source_inventory}"
        )

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

    def _extract_one_line(self, text: str, preferred: str, fallback: str) -> str:
        for marker in (preferred, fallback):
            marker_index = text.find(marker)
            if marker_index != -1:
                tail = text[marker_index:]
                line = tail.split("\n", 1)[0]
                return line.replace("##", "").strip(" -:")
        return text.split("\n", 1)[0].strip() or "Not available"

    def diagnostics(self) -> dict[str, str | int | bool]:
        return {
            "configuredProvider": self.configured_provider,
            "activeProvider": "deterministic",
            "modelName": self.model_name,
            "isFallback": self.configured_provider != "deterministic",
            "fallbackCount": 0,
            "lastError": self.reason,
        }


class GeminiPipelineModelProvider:
    def __init__(self, model_name: str) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        self._model_name = model_name
        self._fallback_count = 0
        self._last_error = ""
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
        try:
            return await self._researcher.research(query)
        except Exception as exc:
            self._register_fallback(exc)
            return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        prompts = {
            "advocate": (
                "You are the Advocate agent for a professional research workflow. "
                "Produce concise markdown with EXACT sections: "
                "'## Opportunity Thesis', '## Strategic Upside', '## Supporting Logic', "
                "'## Actionable Next Step'. Include specific, execution-oriented claims "
                "and avoid generic language."
            ),
            "skeptic": (
                "You are the Skeptic agent for a professional research workflow. "
                "Produce concise markdown with EXACT sections: "
                "'## Risk Thesis', '## Primary Failure Modes', '## Risk Severity', "
                "'## Mitigation Requirement'. Quantify risk level where possible and "
                "avoid generic language."
            ),
            "synthesiser": (
                "You are the Synthesiser agent for a professional research workflow. "
                "Produce concise markdown with EXACT sections: "
                "'## Integrated Assessment', '## Tradeoff Resolution', '## Decision Rule', "
                "'## Guardrails'. Resolve tradeoffs explicitly and define a clear go/no-go rule."
            ),
            "oracle": (
                "You are the Oracle agent for a professional research workflow. "
                "Produce concise markdown with EXACT sections: "
                "'## Scenario Outlook', '## Most Likely Outcome (60%)', "
                "'## Upside Scenario (25%)', '## Downside Scenario (15%)', "
                "'## Leading Indicators to Track'."
            ),
        }
        instruction = prompts.get(agent_id, prompts["oracle"])
        research_block = format_research_context(research)
        try:
            response = await self._model.ainvoke(
                f"{instruction}\n\nQuestion: {query.strip()}\n\nLive web research context:\n{research_block}"
            )
            content = getattr(response, "content", "")
            resolved = str(content).strip()
            if self._is_research_grade(resolved, minimum_length=260):
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
        research_block = format_research_context(research)
        try:
            response = await self._model.ainvoke(
                "You are the final synthesiser for a professional multi-agent research pipeline. "
                "Return a thesis-style markdown report with EXACT sections: "
                "'## Executive Summary', '## Research Scope', '## Evidence Snapshot', "
                "'## Analytical Breakdown', '## Decision Recommendation', '## Action Plan', "
                "'## Confidence and Open Questions', '## Source Inventory'. "
                "Use numbered subsections, bullet lists, and cite source IDs inline like [S1]. "
                "The report should be detailed enough to fill a full A4 page and avoid generic wording.\n\n"
                f"Question: {query.strip()}\n\n"
                f"Support: {outputs.get('advocate', '')}\n"
                f"Risks: {outputs.get('skeptic', '')}\n"
                f"Synthesis: {outputs.get('synthesiser', '')}\n"
                f"Outlook: {outputs.get('oracle', '')}"
                f"\n\nLive web research context:\n{research_block}"
            )
            content = getattr(response, "content", "")
            resolved = str(content).strip()
            if self._is_research_grade(resolved, minimum_length=900):
                return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.compose_final_answer(query, outputs, research)

    def diagnostics(self) -> dict[str, str | int | bool]:
        return {
            "configuredProvider": "gemini",
            "activeProvider": "gemini",
            "modelName": self._model_name,
            "isFallback": self._fallback_count > 0,
            "fallbackCount": self._fallback_count,
            "lastError": self._last_error,
        }

    def _register_fallback(self, exc: Exception) -> None:
        self._fallback_count += 1
        message = f"{type(exc).__name__}: {exc}".strip()
        self._last_error = message[:240]

    def _is_research_grade(self, text: str, minimum_length: int) -> bool:
        required_sections = (
            "## Executive Summary",
            "## Evidence Snapshot",
            "## Decision Recommendation",
        )
        if len(text) < minimum_length:
            return False
        return all(section in text for section in required_sections)


def _web_research_enabled() -> bool:
    return os.getenv("HEXAMIND_WEB_RESEARCH", "1").strip().lower() not in {"0", "false", "no"}


def _create_researcher() -> object:
    from research import InternetResearcher

    return InternetResearcher()


def create_pipeline_model_provider() -> PipelineModelProvider:
    provider_name = os.getenv("HEXAMIND_MODEL_PROVIDER", "deterministic").strip().lower()
    if provider_name in {"gemini", "google", "google-genai"}:
        model_name = os.getenv("HEXAMIND_MODEL_NAME", "gemini-2.0-flash")
        try:
            return GeminiPipelineModelProvider(model_name)
        except Exception as exc:
            return DeterministicPipelineModelProvider(
                configured_provider="gemini",
                model_name=model_name,
                reason=f"Gemini init failed: {type(exc).__name__}",
            )

    return DeterministicPipelineModelProvider(
        configured_provider=provider_name,
        model_name=os.getenv("HEXAMIND_MODEL_NAME", "deterministic"),
    )