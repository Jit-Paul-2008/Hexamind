"""Detect changes between iterations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IterationDelta:
    new_claims: int
    modified_claims: int
    retracted_claims: int
    avg_claim_confidence_change: float
    evidence_base_delta: float


class ChangeDetector:
    def detect_changes(self, current: dict, previous: dict | None) -> IterationDelta:
        if not previous:
            return IterationDelta(0, 0, 0, 0.0, 0.0)
        return IterationDelta(0, 0, 0, 0.0, 0.0)
