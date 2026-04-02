from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptRecord:
    name: str
    version: str
    fingerprint: str


def prompt_fingerprint(name: str, text: str) -> PromptRecord:
    fingerprint = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:12]
    version = f"{name}-v1"
    return PromptRecord(name=name, version=version, fingerprint=fingerprint)


def prompt_registry_snapshot(records: list[PromptRecord]) -> dict[str, object]:
    registry_version = hashlib.sha256(
        "|".join(f"{record.name}:{record.version}:{record.fingerprint}" for record in records).encode("utf-8")
    ).hexdigest()[:12]
    return {
        "registryVersion": registry_version,
        "prompts": [
            {
                "name": record.name,
                "version": record.version,
                "fingerprint": record.fingerprint,
            }
            for record in records
        ],
    }