from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol


class PipelineModelProvider(Protocol):
    async def build_agent_text(self, agent_id: str, query: str) -> str:
        ...

    async def compose_final_answer(self, query: str, outputs: dict[str, str]) -> str:
        ...


@dataclass(frozen=True)
class DeterministicPipelineModelProvider:
    async def build_agent_text(self, agent_id: str, query: str) -> str:
        q = query.strip()
        if agent_id == "advocate":
            return (
                f"Strongest case for '{q}': measurable upside exists if scope is narrow, "
                "constraints are explicit, and early metrics are tracked from day one."
            )
        if agent_id == "skeptic":
            return (
                f"Primary risks for '{q}': noisy assumptions, hidden dependency costs, "
                "and unclear ownership can break delivery quality and reliability."
            )
        if agent_id == "synthesiser":
            return (
                f"Balanced synthesis for '{q}': proceed in phased slices with guardrails, "
                "validate each increment, and stop expansion if confidence regresses."
            )
        return (
            f"Forecast for '{q}': likely positive outcome under controlled rollout, "
            "with biggest gains from fast feedback loops and strict review checkpoints."
        )

    async def compose_final_answer(self, query: str, outputs: dict[str, str]) -> str:
        advocate = outputs.get("advocate", "")
        skeptic = outputs.get("skeptic", "")
        synthesis = outputs.get("synthesiser", "")
        oracle = outputs.get("oracle", "")
        return (
            f"Final synthesis for '{query}': {synthesis} "
            f"Support: {advocate} "
            f"Risks: {skeptic} "
            f"Outlook: {oracle}"
        )


class GeminiPipelineModelProvider:
    def __init__(self, model_name: str) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        self._model = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.35,
        )
        self._fallback = DeterministicPipelineModelProvider()

    async def build_agent_text(self, agent_id: str, query: str) -> str:
        prompts = {
            "advocate": (
                "You are the Advocate agent. Build the strongest possible case for the "
                "question below in 2 short sentences. Emphasize concrete upside and "
                "practical execution."
            ),
            "skeptic": (
                "You are the Skeptic agent. Challenge the question below in 2 short "
                "sentences. Emphasize risks, hidden costs, and failure modes."
            ),
            "synthesiser": (
                "You are the Synthesiser agent. Integrate the arguments in 2 short "
                "sentences. Give a balanced recommendation with guardrails."
            ),
            "oracle": (
                "You are the Oracle agent. Predict the likely outcome in 2 short "
                "sentences. Focus on rollout risk and expected impact."
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
        except Exception:
            pass

        return await self._fallback.build_agent_text(agent_id, query)

    async def compose_final_answer(self, query: str, outputs: dict[str, str]) -> str:
        try:
            response = await self._model.ainvoke(
                "You are the final synthesiser for a multi-agent research pipeline. "
                "Using the agent outputs below, produce a concise final answer in 3-4 "
                "sentences. Mention the strongest support, main risk, and a clear next step.\n\n"
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
        except Exception:
            pass

        return await self._fallback.compose_final_answer(query, outputs)


def create_pipeline_model_provider() -> PipelineModelProvider:
    provider_name = os.getenv("HEXAMIND_MODEL_PROVIDER", "deterministic").strip().lower()
    if provider_name in {"gemini", "google", "google-genai"}:
        model_name = os.getenv("HEXAMIND_MODEL_NAME", "gemini-1.5-flash")
        try:
            return GeminiPipelineModelProvider(model_name)
        except Exception:
            return DeterministicPipelineModelProvider()

    return DeterministicPipelineModelProvider()