"""Track and manage source inventory."""

from __future__ import annotations

from pathlib import Path
import json


class SourceInventory:
    """Maintains inventory of extracted sources to prevent re-processing."""
    
    def __init__(self, inventory_path: Path) -> None:
        self.inventory_path = inventory_path
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)
        self.inventory: dict = self._load()
    
    def _load(self) -> dict:
        """Load inventory from disk."""
        if self.inventory_path.exists():
            with open(self.inventory_path) as f:
                return json.load(f)
        return {}
    
    def _save(self) -> None:
        """Save inventory to disk."""
        with open(self.inventory_path, "w") as f:
            json.dump(self.inventory, f, indent=2)
    
    def mark_extracted(self, source_key: str, metadata: dict) -> None:
        """Mark source as extracted."""
        self.inventory[source_key] = {
            "extracted_at": __import__("datetime").datetime.utcnow().isoformat(),
            "metadata": metadata,
        }
        self._save()
    
    def is_extracted(self, source_key: str) -> bool:
        """Check if source was already extracted."""
        return source_key in self.inventory
