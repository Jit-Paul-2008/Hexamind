"""Track improvement ROI and feedback loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class ImprovementResult:
    config_change: dict
    metrics_before: dict
    metrics_after: dict
    roi: float


class FeedbackLoop:
    def __init__(self, feedback_path: Path | None = None) -> None:
        self.feedback_path = feedback_path or Path.home() / "Desktop" / "Hexamind" / "reports-versioned" / "aggregated" / "feedback.jsonl"
        self.feedback_path.parent.mkdir(parents=True, exist_ok=True)

    def record_improvement(self, result: ImprovementResult) -> None:
        with self.feedback_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result.__dict__) + "\n")

    def get_winning_configs(self, top_n: int = 5) -> list[dict]:
        return []
