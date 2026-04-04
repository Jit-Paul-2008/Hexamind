"""Track and manage source inventory."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path


class SourceInventory:
    def __init__(self, inventory_path: Path) -> None:
        self.inventory_path = inventory_path
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)
        self.inventory: dict = self._load()

    def _load(self) -> dict:
        if self.inventory_path.exists():
            return json.loads(self.inventory_path.read_text(encoding="utf-8"))
        return {}

    def _save(self) -> None:
        self.inventory_path.write_text(json.dumps(self.inventory, indent=2), encoding="utf-8")

    def mark_extracted(self, source_key: str, metadata: dict) -> None:
        self.inventory[source_key] = {"extracted_at": datetime.utcnow().isoformat(), "metadata": metadata}
        self._save()

    def is_extracted(self, source_key: str) -> bool:
        return source_key in self.inventory
