import json
import os
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class AgentConfig:
    id: str
    codename: str
    role: str
    purpose: str
    accent_color: str
    glow_color: str
    shape: str
    processing_order: int


def _load_agents() -> List[AgentConfig]:
    """Load agents from the shared public/agents.json file to ensure a singular source of truth."""
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public", "agents.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [
                AgentConfig(
                    id=a["id"],
                    codename=a["name"],
                    role=a["role"],
                    purpose=a["purpose"],
                    accent_color=a["accent_color"],
                    glow_color=a["glow_color"],
                    shape=a["shape"],
                    processing_order=a["processing_order"],
                )
                for a in data
            ]
    except Exception as e:
        # Fallback for local development or missing file
        return []


AGENTS: tuple[AgentConfig, ...] = tuple(_load_agents())
