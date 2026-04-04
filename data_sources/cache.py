"""Deduplication and caching for extracted data."""

from __future__ import annotations

import hashlib
from typing import Optional


class DeduplicationCache:
    def __init__(self) -> None:
        self.cache: dict[str, str] = {}
        self.hashes: dict[str, str] = {}

    def compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def is_duplicate(self, content: str) -> bool:
        return self.compute_hash(content) in self.hashes

    def add(self, key: str, content: str) -> None:
        content_hash = self.compute_hash(content)
        self.cache[key] = content
        self.hashes[content_hash] = key

    def get(self, key: str) -> Optional[str]:
        return self.cache.get(key)
