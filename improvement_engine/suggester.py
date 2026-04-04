"""Suggest improvements using 70B model."""

from __future__ import annotations

from dataclasses import dataclass
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
ai_service_path = project_root / "ai-service"
if str(ai_service_path) not in sys.path:
    sys.path.insert(0, str(ai_service_path))

from model_provider import create_pipeline_model_provider


@dataclass
class ImprovementSuggestion:
    title: str
    description: str
    config_changes: dict
    expected_impact: float


class ImprovementSuggester:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("HEXAMIND_LOCAL_MODEL_LARGE", "llama3.1:70b-instruct-q4_K_M")
        self._provider = create_pipeline_model_provider()

    async def suggest(self, report: str, metrics: dict, gaps: dict) -> list[ImprovementSuggestion]:
        prompt = (
            "You are improving an autonomous local research loop. "
            "Return concise, actionable configuration improvements only. "
            f"Current metrics: {metrics}\nGaps: {gaps}\nReport excerpt:\n{report[:6000]}"
        )
        try:
            response = await self._provider.compose_final_answer(
                query="Autonomous loop improvement suggestions",
                outputs={"advocate": prompt, "skeptic": prompt, "synthesiser": prompt, "oracle": prompt, "verifier": prompt},
                research=None,
            )
            suggestions: list[ImprovementSuggestion] = []
            for line in response.splitlines():
                cleaned = line.strip("-• ")
                if not cleaned:
                    continue
                suggestions.append(ImprovementSuggestion(title=cleaned[:80], description=cleaned, config_changes={}, expected_impact=0.5))
            return suggestions[:3]
        except Exception:
            return []

    async def recommend_config(self, suggestions: list[ImprovementSuggestion]) -> dict:
        recommended: dict = {}
        for suggestion in suggestions:
            if suggestion.expected_impact >= 0.5:
                recommended.update(suggestion.config_changes)
        return recommended
