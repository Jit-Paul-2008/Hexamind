"""Suggest improvements using 70B model."""

from __future__ import annotations

import json
from dataclasses import dataclass
import os
import sys
from pathlib import Path
import re
from importlib import import_module

project_root = Path(__file__).resolve().parents[1]
ai_service_path = project_root / "ai-service"
if str(ai_service_path) not in sys.path:
    sys.path.insert(0, str(ai_service_path))

create_pipeline_model_provider = import_module("model_provider").create_pipeline_model_provider


@dataclass
class ImprovementSuggestion:
    title: str
    description: str
    config_changes: dict
    expected_impact: float
    confidence: float = 0.0


class ImprovementSuggester:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("HEXAMIND_LOCAL_MODEL_LARGE", "llama3.1:70b-instruct-q4_K_M")
        self._provider = create_pipeline_model_provider()

    async def suggest(
        self,
        report: str,
        metrics: dict,
        gaps: dict,
        coverage_summary: dict | None = None,
        comparison: dict | None = None,
        max_suggestions: int = 3,
    ) -> list[ImprovementSuggestion]:
        prompt = (
            "You are improving an autonomous local research loop. "
            "Return a JSON array of at most "
            f"{max_suggestions} items with keys: title, description, config_changes, expected_impact, confidence. "
            "Prefer concrete changes to source coverage, extraction depth, and loop gating. "
            "Allowed config keys: AUTONOMOUS_DATA_SOURCES, AUTONOMOUS_MIN_SOURCE_COVERAGE, AUTONOMOUS_MIN_SOURCE_COUNT, AUTONOMOUS_MIN_SOURCE_DIVERSITY, AUTONOMOUS_MIN_EXTRACTED_CHARS, AUTONOMOUS_IMPROVEMENT_MIN_DELTA, AUTONOMOUS_IMPROVEMENT_MIN_CONFIDENCE, AUTONOMOUS_IMPROVEMENT_MAX_SUGGESTIONS, HEXAMIND_WEB_RESEARCH. "
            f"Current metrics: {json.dumps(metrics, sort_keys=True)}\n"
            f"Coverage: {json.dumps(coverage_summary or {}, sort_keys=True)}\n"
            f"Comparison: {json.dumps(comparison or {}, sort_keys=True)}\n"
            f"Gaps: {json.dumps(gaps, sort_keys=True)}\n"
            f"Report excerpt:\n{report[:6000]}"
        )
        try:
            response = await self._provider.compose_final_answer(
                query="Autonomous loop improvement suggestions",
                outputs={"advocate": prompt, "skeptic": prompt, "synthesiser": prompt, "oracle": prompt, "verifier": prompt},
                research=None,
            )
            parsed = self._parse_suggestions(response)
            if parsed:
                return parsed[:max_suggestions]
        except Exception:
            pass
        return self._heuristic_suggestions(metrics, gaps, coverage_summary or {}, max_suggestions)

    async def recommend_config(self, suggestions: list[ImprovementSuggestion], min_confidence: float = 0.65, min_delta: float = 0.10) -> dict:
        recommended: dict = {}
        for suggestion in suggestions:
            if suggestion.expected_impact >= min_delta and suggestion.confidence >= min_confidence:
                recommended.update(suggestion.config_changes)
        return recommended

    def _parse_suggestions(self, response: str) -> list[ImprovementSuggestion]:
        text = response.strip()
        json_candidates = []
        fenced = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if fenced:
            json_candidates.append(fenced.group(1))
        json_candidates.append(text)
        for candidate in json_candidates:
            for payload in self._candidate_payloads(candidate):
                try:
                    loaded = json.loads(payload)
                    if isinstance(loaded, dict):
                        loaded = loaded.get("suggestions", loaded.get("items", []))
                    if isinstance(loaded, list):
                        suggestions: list[ImprovementSuggestion] = []
                        for item in loaded:
                            if not isinstance(item, dict):
                                continue
                            suggestions.append(
                                ImprovementSuggestion(
                                    title=str(item.get("title", "Improvement"))[:80],
                                    description=str(item.get("description", "")),
                                    config_changes=item.get("config_changes", {}) if isinstance(item.get("config_changes", {}), dict) else {},
                                    expected_impact=float(item.get("expected_impact", 0.0) or 0.0),
                                    confidence=float(item.get("confidence", 0.0) or 0.0),
                                )
                            )
                        if suggestions:
                            return suggestions
                except Exception:
                    continue
        return []

    def _candidate_payloads(self, text: str) -> list[str]:
        payloads = [text]
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            payloads.append(text[start : end + 1])
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            payloads.append(text[start : end + 1])
        return payloads

    def _heuristic_suggestions(self, metrics: dict, gaps: dict, coverage_summary: dict, max_suggestions: int) -> list[ImprovementSuggestion]:
        suggestions: list[ImprovementSuggestion] = []
        overall_coverage = float(coverage_summary.get("overallCoverage", 0.0) or 0.0)
        source_count = int(coverage_summary.get("sourceCount", 0) or 0)
        unique_domains = int(coverage_summary.get("uniqueDomains", 0) or 0)
        extracted_chars = int(coverage_summary.get("extractedChars", 0) or 0)

        if overall_coverage < 0.85 or source_count < 3 or unique_domains < 3:
            suggestions.append(
                ImprovementSuggestion(
                    title="Broaden source coverage",
                    description="Add more diverse local sources and enable live web research for corroboration.",
                    config_changes={
                        "AUTONOMOUS_MIN_SOURCE_COVERAGE": "0.9",
                        "AUTONOMOUS_MIN_SOURCE_COUNT": str(max(3, source_count + 1)),
                        "AUTONOMOUS_MIN_SOURCE_DIVERSITY": str(max(3, unique_domains + 1)),
                        "HEXAMIND_WEB_RESEARCH": "1",
                    },
                    expected_impact=0.35,
                    confidence=0.9,
                )
            )

        if extracted_chars < 4000 or float(metrics.get("citationCount", 0) or 0) < 4:
            suggestions.append(
                ImprovementSuggestion(
                    title="Strengthen extraction depth",
                    description="Increase extracted character budget and require richer source corpora before research starts.",
                    config_changes={
                        "AUTONOMOUS_MIN_EXTRACTED_CHARS": str(max(4000, extracted_chars + 1000)),
                        "AUTONOMOUS_IMPROVEMENT_MIN_DELTA": "0.08",
                    },
                    expected_impact=0.28,
                    confidence=0.85,
                )
            )

        if float(metrics.get("claimVerificationRate", 0.0) or 0.0) < 0.75:
            suggestions.append(
                ImprovementSuggestion(
                    title="Tighten improvement gating",
                    description="Require higher confidence before applying model suggestions and cap the number of changes per run.",
                    config_changes={
                        "AUTONOMOUS_IMPROVEMENT_MIN_CONFIDENCE": "0.75",
                        "AUTONOMOUS_IMPROVEMENT_MAX_SUGGESTIONS": "2",
                    },
                    expected_impact=0.22,
                    confidence=0.92,
                )
            )

        if gaps.get("source_gaps") or gaps.get("missing_evidence_areas"):
            suggestions.append(
                ImprovementSuggestion(
                    title="Bias toward corroboration",
                    description="Force the next run to include gap-driven follow-up queries and counter-evidence retrieval.",
                    config_changes={
                        "AUTONOMOUS_IMPROVEMENT_MIN_CONFIDENCE": "0.7",
                    },
                    expected_impact=0.2,
                    confidence=0.88,
                )
            )

        return suggestions[:max_suggestions]
