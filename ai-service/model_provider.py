from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol


class PipelineModelProvider(Protocol):
    async def build_agent_text(self, agent_id: str, query: str) -> str:
        ...

    async def compose_final_answer(self, query: str, outputs: dict[str, str]) -> str:
        ...

    def diagnostics(self) -> dict[str, str | int | bool]:
        ...


@dataclass
class DeterministicPipelineModelProvider:
    configured_provider: str = "deterministic"
    model_name: str = "deterministic"
    reason: str = ""

    async def build_agent_text(self, agent_id: str, query: str) -> str:
        q = query.strip()
        if agent_id == "advocate":
            return self._structured_advocate(q)
        if agent_id == "skeptic":
            return self._structured_skeptic(q)
        if agent_id == "synthesiser":
            return self._structured_synthesiser(q)
        return self._structured_oracle(q)

    async def compose_final_answer(self, query: str, outputs: dict[str, str]) -> str:
        q = query.strip()
        return (
            "## Executive Summary\n"
            f"The decision on '{q}' should proceed through a staged rollout tied to measurable outcomes and explicit risk controls.\n\n"
            "## Evidence Snapshot\n"
            "- Opportunity case indicates upside when implementation scope is constrained and ownership is clear.\n"
            "- Risk analysis highlights dependency volatility, quality drift, and adoption uncertainty as key threats.\n"
            "- Integrated view supports controlled expansion only after milestone validation.\n\n"
            "## Decision Recommendation\n"
            "Proceed with a gated pilot, define kill criteria in advance, and require metric improvement before broad rollout.\n\n"
            "## 30-Day Action Plan\n"
            "1. Establish baseline metrics, owners, and weekly review cadence.\n"
            "2. Run a narrow pilot with explicit acceptance thresholds.\n"
            "3. Execute risk mitigations for top three failure modes before scaling.\n\n"
            "## Confidence and Open Questions\n"
            "Confidence: Moderate. Remaining uncertainty comes from dependency stability and user behavior variance."
        )

    def _structured_advocate(self, query: str) -> str:
        return (
            "## Opportunity Thesis\n"
            f"Question: {query}\n\n"
            "## Strategic Upside\n"
            "- Potential to improve cycle time and decision quality if rollout is scoped.\n"
            "- Creates clearer accountability through explicit ownership and milestone tracking.\n"
            "- Enables compounding improvements via fast feedback loops.\n\n"
            "## Supporting Logic\n"
            "- Value is highest when initial use case is narrow and metrics are unambiguous.\n"
            "- Early instrumentation reduces rework and surfaces blockers quickly.\n\n"
            "## Actionable Next Step\n"
            "Launch a pilot with one constrained workflow and pre-define success thresholds."
        )

    def _structured_skeptic(self, query: str) -> str:
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
            "## Mitigation Requirement\n"
            "Define risk owners, trigger thresholds, and contingency actions before scale-up."
        )

    def _structured_synthesiser(self, query: str) -> str:
        return (
            "## Integrated Assessment\n"
            f"Question: {query}\n\n"
            "## Tradeoff Resolution\n"
            "- Upside is meaningful only when execution discipline is high.\n"
            "- Major risks are manageable with staged deployment and strict governance.\n"
            "- Recommendation depends on measurable checkpoint performance, not narrative confidence.\n\n"
            "## Decision Rule\n"
            "Proceed if pilot metrics exceed baseline and no critical risk trigger fires for two review cycles.\n\n"
            "## Guardrails\n"
            "- Maintain scope limits until stability and ROI are demonstrated.\n"
            "- Stop expansion immediately on quality or reliability regression."
        )

    def _structured_oracle(self, query: str) -> str:
        return (
            "## Scenario Outlook\n"
            f"Question: {query}\n\n"
            "## Most Likely Outcome (60%)\n"
            "Measured gains appear in the pilot phase, followed by cautious expansion.\n\n"
            "## Upside Scenario (25%)\n"
            "Early metric outperformance enables faster scale with manageable operational load.\n\n"
            "## Downside Scenario (15%)\n"
            "Dependency failures and weak adoption force rollback to a narrower operating model.\n\n"
            "## Leading Indicators to Track\n"
            "- Cycle-time improvement vs baseline\n"
            "- Defect/reliability trend\n"
            "- User adoption and retention signal"
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
        self._model = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.35,
        )
        self._fallback = DeterministicPipelineModelProvider(
            configured_provider="gemini",
            model_name=model_name,
            reason="Gemini runtime call failed",
        )

    async def build_agent_text(self, agent_id: str, query: str) -> str:
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
        try:
            response = await self._model.ainvoke(
                f"{instruction}\n\nQuestion: {query.strip()}"
            )
            content = getattr(response, "content", "")
            resolved = str(content).strip()
            if resolved:
                return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.build_agent_text(agent_id, query)

    async def compose_final_answer(self, query: str, outputs: dict[str, str]) -> str:
        try:
            response = await self._model.ainvoke(
                "You are the final synthesiser for a professional multi-agent research pipeline. "
                "Return concise markdown with EXACT sections: "
                "'## Executive Summary', '## Evidence Snapshot', '## Decision Recommendation', "
                "'## 30-Day Action Plan', '## Confidence and Open Questions'. "
                "Base your answer on the supplied outputs and avoid generic wording.\n\n"
                f"Question: {query.strip()}\n\n"
                f"Support: {outputs.get('advocate', '')}\n"
                f"Risks: {outputs.get('skeptic', '')}\n"
                f"Synthesis: {outputs.get('synthesiser', '')}\n"
                f"Outlook: {outputs.get('oracle', '')}"
            )
            content = getattr(response, "content", "")
            resolved = str(content).strip()
            if resolved:
                return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.compose_final_answer(query, outputs)

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