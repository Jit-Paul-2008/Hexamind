"""Semantic difference detection between reports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SemanticChange:
    """Represents a semantic change between reports."""
    claim_id: str
    original_claim: str
    new_claim: str
    change_type: str  # "added", "modified", "retracted"
    confidence: float


class SemanticDiff:
    """Detects semantic differences between two reports."""
    
    def __init__(self) -> None:
        # TODO: Could use embeddings for semantic similarity
        pass
    
    def compare(self, report_a: str, report_b: str) -> list[SemanticChange]:
        """Compare two reports and identify semantic changes."""
        # TODO: Extract claims from both reports and diff them
        return []
    
    def extract_claims(self, report: str) -> list[dict]:
        """Extract structured claims from a report."""
        # TODO: Parse report structure and identify claims
        return []
