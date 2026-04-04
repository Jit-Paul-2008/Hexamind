"""Track improvement ROI and feedback loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class ImprovementResult:
    """Result of applying an improvement."""
    config_change: dict
    metrics_before: dict
    metrics_after: dict
    roi: float  # (after - before) / max_possible


class FeedbackLoop:
    """Tracks what improvements actually helped."""
    
    def __init__(self, feedback_path: Path | None = None) -> None:
        self.feedback_path = feedback_path or Path.home() / "Desktop" / "Hexamind" / "reports-versioned" / "aggregated" / "feedback.jsonl"
        self.feedback_path.parent.mkdir(parents=True, exist_ok=True)
    
    def record_improvement(self, result: ImprovementResult) -> None:
        """Record the result of an improvement."""
        # TODO: Log improvement result with ROI
        pass
    
    def get_winning_configs(self, top_n: int = 5) -> list[dict]:
        """Retrieve top-performing configurations by ROI."""
        # TODO: Analyze feedback logs and return best performers
        return []
