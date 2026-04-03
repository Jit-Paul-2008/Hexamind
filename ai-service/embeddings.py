from __future__ import annotations

import hashlib
import math
import os
import time
from typing import Iterable

import httpx


class LocalEmbeddingsClient:
    def __init__(self, base_url: str | None = None, model: str | None = None, timeout_seconds: float | None = None) -> None:
        self._base_url = (base_url or os.getenv("HEXAMIND_LOCAL_EMBEDDINGS_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self._model = (model or os.getenv("HEXAMIND_LOCAL_EMBEDDINGS_MODEL", "nomic-embed-text")).strip() or "nomic-embed-text"
        self._timeout_seconds = float(timeout_seconds or os.getenv("HEXAMIND_LOCAL_EMBEDDINGS_TIMEOUT_SECONDS", "20"))
        self._cache_ttl_seconds = max(60.0, _env_float("HEXAMIND_LOCAL_EMBEDDINGS_CACHE_TTL_SECONDS", 3600.0))
        self._cache: dict[str, tuple[float, tuple[float, ...]]]= {}

    async def embed(self, text: str) -> list[float]:
        value = (text or "").strip()
        if not value:
            return []

        cache_key = self._cache_key(value)
        cached = self._cache.get(cache_key)
        if cached and time.time() - cached[0] <= self._cache_ttl_seconds:
            return list(cached[1])

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": value},
            )
            response.raise_for_status()
            payload = response.json()

        embedding = payload.get("embedding")
        if not isinstance(embedding, list):
            raise RuntimeError("Local embeddings response missing embedding vector")

        vector = tuple(float(item) for item in embedding)
        self._cache[cache_key] = (time.time(), vector)
        return list(vector)

    async def similarity(self, left: str, right: str) -> float:
        left_vector, right_vector = await self._embed_pair(left, right)
        if not left_vector or not right_vector:
            return 0.0
        return self.cosine_similarity(left_vector, right_vector)

    async def _embed_pair(self, left: str, right: str) -> tuple[list[float], list[float]]:
        left_vector = await self.embed(left)
        right_vector = await self.embed(right)
        return left_vector, right_vector

    @staticmethod
    def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
        left_values = list(left)
        right_values = list(right)
        if not left_values or not right_values:
            return 0.0

        length = min(len(left_values), len(right_values))
        dot_product = sum(left_values[index] * right_values[index] for index in range(length))
        left_norm = math.sqrt(sum(value * value for value in left_values))
        right_norm = math.sqrt(sum(value * value for value in right_values))
        if not left_norm or not right_norm:
            return 0.0
        return dot_product / (left_norm * right_norm)

    @staticmethod
    def _cache_key(text: str) -> str:
        return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default