"""Semantic difference detection between reports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SemanticChange:
    claim_id: str
    original_claim: str
    new_claim: str
    change_type: str
    confidence: float


class SemanticDiff:
    def compare(self, report_a: str, report_b: str) -> list[SemanticChange]:
        return []

    def extract_claims(self, report: str) -> list[dict]:
        return []
