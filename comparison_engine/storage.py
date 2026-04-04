"""Storage and versioning of comparisons."""

from __future__ import annotations

import json
from pathlib import Path


class ComparisonStorage:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_comparison(self, iteration_id: str, comparison: dict) -> None:
        (self.storage_path / f"{iteration_id}-comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    def load_latest_comparison(self) -> dict | None:
        return None
