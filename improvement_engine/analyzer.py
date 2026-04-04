"""Analyze gaps in research reports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GapAnalysis:
    missing_evidence_areas: list[str]
    underdeveloped_claims: list[str]
    contradictions_unresolved: list[str]
    source_gaps: list[str]


class GapAnalyzer:
    def analyze(self, report: str, metrics: dict) -> GapAnalysis:
        return GapAnalysis([], [], [], [])
