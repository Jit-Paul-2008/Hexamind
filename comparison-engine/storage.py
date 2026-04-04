"""Storage and versioning of comparisons."""

from __future__ import annotations

from pathlib import Path
import json


class ComparisonStorage:
    """Persists comparison results between iterations."""
    
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save_comparison(self, iteration_id: str, comparison: dict) -> None:
        """Save comparison result to disk."""
        comparison_path = self.storage_path / f"{iteration_id}-comparison.json"
        with open(comparison_path, "w") as f:
            json.dump(comparison, f, indent=2)
    
    def load_latest_comparison(self) -> dict | None:
        """Load most recent comparison."""
        # TODO: Find and load latest comparison file
        return None
