"""Deduplication and caching for extracted data."""

from __future__ import annotations

import hashlib
from typing import Optional


class DeduplicationCache:
    """Cache and deduplicate extracted content."""
    
    def __init__(self) -> None:
        self.cache: dict[str, str] = {}
        self.hashes: dict[str, str] = {}
    
    def compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def is_duplicate(self, content: str) -> bool:
        """Check if content was already extracted."""
        content_hash = self.compute_hash(content)
        return content_hash in self.hashes
    
    def add(self, key: str, content: str) -> None:
        """Add content to cache."""
        content_hash = self.compute_hash(content)
        self.cache[key] = content
        self.hashes[content_hash] = key
    
    def get(self, key: str) -> Optional[str]:
        """Retrieve cached content."""
        return self.cache.get(key)
