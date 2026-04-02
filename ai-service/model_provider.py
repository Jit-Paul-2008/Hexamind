from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Protocol

import httpx

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
        research_findings = self._research_findings(research)
        tool_analysis = self._tool_analysis_markdown(research)
        return (
            "## Executive Summary\n"
            f"The decision on '{q}' should be treated as a bounded research problem: gather current evidence, separate primary from secondary sources, and validate the recommendation through staged execution.\n\n"
            "## 1. Research Question and Scope\n"
            f"- Core question: {q}\n"
            "- Scope: current public evidence, implementation implications, and decision risks.\n"
            "- Method: internet search, page retrieval, source comparison, and structured synthesis.\n\n"
            "## 2. Evidence Snapshot\n"
            f"- Opportunity case: {self._extract_section_summary(support, '## Strategic Upside', '## Supporting Logic')}\n"
            f"- Risk case: {self._extract_section_summary(risk, '## Primary Failure Modes', '## Risk Severity')}\n"
            f"- Integrated position: {self._extract_section_summary(synthesis, '## Tradeoff Resolution', '## Decision Rule')}\n"
            f"- Forecast: {self._extract_section_summary(outlook, '## Most Likely Outcome (60%)', '## Upside Scenario (25%)')}\n\n"
            "## 3. Comparative Analysis\n"
            "### 3.1 What the evidence supports\n"
            f"- The live source pack indicates where the question is discussed on the web and which pages are directly relevant. {source_block}\n"
            "- The strongest conclusion is not absolute certainty; it is a controlled path that preserves optionality.\n"
            "- The most defensible move is a pilot with measurable gates, not unconstrained scale.\n\n"
            "### 3.2 Tool-by-tool assessment\n"
            f"{tool_analysis}\n"
            "### 3.3 Where uncertainty remains\n"
            "- Source quality can vary widely across summaries, forums, and vendor material.\n"
            "- If current public evidence is thin, the report should explicitly label those gaps rather than infer them.\n"
            "- Operational risk remains material whenever ownership, dependencies, or measurement are unclear.\n\n"
            "## 4. Missing Steps in the Current App\n"
            f"{research_findings}\n\n"
            "## 5. Recommendation\n"
            "1. Proceed only with a narrow pilot and written success criteria.\n"
            "2. Require one owner per risk category and one metric per success claim.\n"
            "3. Expand only after the pilot meets the baseline and no critical triggers are active.\n\n"
            "## 6. 30-Day Action Plan\n"
            "- Week 1: confirm baseline, collect sources, and document assumptions.\n"
            "- Week 2: run a constrained pilot or desk evaluation.\n"
            "- Week 3: review performance, risks, and source contradictions.\n"
            "- Week 4: decide whether to scale, hold, or stop.\n\n"
            "## 7. Confidence and Open Questions\n"
            "- Confidence: Moderate, because the recommendation is grounded but still depends on the quality of current web evidence.\n"
            "- Open questions: whether the newest sources materially change the baseline, and which external dependencies are most fragile.\n\n"
            "## 8. Source Inventory\n"
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
            response = await self._model.ainvoke(
                f"{instruction}\n\nQuestion: {query.strip()}\n\nLive web research context:\n{research_block}"
            )
            content = getattr(response, "content", "")
            resolved = str(content).strip()
            if _is_agent_research_grade(resolved, minimum_length=260, research=research):
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
                "Include a subsection named '### Claim-to-Citation Map' under Analytical Breakdown. "
                "If evidence is weak, state the gap explicitly instead of speculating. "
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
            if _is_final_research_grade(resolved, minimum_length=900, research=research):
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


class OpenRouterPipelineModelProvider:
    def __init__(self, default_model: str) -> None:
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for provider=openrouter")

        self._default_model = default_model
        self._fallback_count = 0
        self._last_error = ""
        self._base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self._timeout_seconds = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "35"))
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
            resolved = await self._chat(
                model=model_name,
                system_prompt=system_prompt,
                user_prompt=f"Question: {query.strip()}\n\nLive web research context:\n{research_block}",
            )
            if _is_agent_research_grade(resolved, minimum_length=280, research=research):
                return resolved

            repaired = await self._chat(
                model=model_name,
                system_prompt=system_prompt,
                user_prompt=(
                    "Regenerate with stronger grounding. Add explicit [Sx] citations to all major claims "
                    "and ensure each section has evidence support.\n\n"
                    f"Question: {query.strip()}\n\nLive web research context:\n{research_block}"
                ),
            )
            if _is_agent_research_grade(repaired, minimum_length=280, research=research):
                return repaired
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
        model_name = self._model_by_role.get("final", self._default_model)

        try:
            resolved = await self._chat(
                model=model_name,
                system_prompt=(
                    "You are ARIA final synthesiser in deep-research mode. Return markdown with EXACT sections: "
                    "'## Executive Summary', '## Research Scope', '## Evidence Snapshot', "
                    "'## Analytical Breakdown', '## Decision Recommendation', '## Action Plan', "
                    "'## Confidence and Open Questions', '## Source Inventory'. Under '## Analytical Breakdown' "
                    "include '### Claim-to-Citation Map' and '### Contradictions and Uncertainty'. "
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
            )
            if _is_final_research_grade(resolved, minimum_length=920, research=research):
                return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.compose_final_answer(query, outputs, research)

    def diagnostics(self) -> dict[str, str | int | bool]:
        return {
            "configuredProvider": "openrouter",
            "activeProvider": "openrouter",
            "modelName": self._default_model,
            "isFallback": self._fallback_count > 0,
            "fallbackCount": self._fallback_count,
            "lastError": self._last_error,
            "agentModelMap": json.dumps(self._model_by_role, sort_keys=True),
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
    if provider_name in {"openrouter", "router"}:
        model_name = os.getenv("HEXAMIND_MODEL_NAME", "openai/gpt-4.1-mini")
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