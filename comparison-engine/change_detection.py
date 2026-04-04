"""Detect changes between iterations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IterationDelta:
    """Difference between two iterations."""
    new_claims: int
    modified_claims: int
    retracted_claims: int
    avg_claim_confidence_change: float
    evidence_base_delta: float


class ChangeDetector:
    """Detects what changed between iterations."""
    
    def detect_changes(self, current: dict, previous: dict | None) -> IterationDelta:
        """Compute delta between current and previous iteration."""
        if not previous:
            return IterationDelta(
                new_claims=0,
                modified_claims=0,
                retracted_claims=0,
                avg_claim_confidence_change=0.0,
                evidence_base_delta=0.0,
            )
        
        # TODO: Compare iterations and compute deltas
        return IterationDelta(
            new_claims=0,
            modified_claims=0,
            retracted_claims=0,
            avg_claim_confidence_change=0.0,
            evidence_base_delta=0.0,
        )
