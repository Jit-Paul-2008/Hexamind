from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any


class LocalKnowledgeCache:
    def __init__(self, cache_dir: Path | None = None) -> None:
        if cache_dir is None:
            env_cache_dir = os.getenv("HEXAMIND_KNOWLEDGE_CACHE_DIR", "").strip()
            if env_cache_dir:
                cache_dir = Path(env_cache_dir)
            else:
                cache_dir = Path(__file__).resolve().with_name(".data").joinpath("knowledge-cache")
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._ttl_seconds = max(60.0, _env_float("HEXAMIND_KNOWLEDGE_CACHE_TTL_SECONDS", 7 * 24 * 60 * 60))

    def cache_research(self, query: str, research: Any) -> None:
        if not query.strip() or research is None:
            return

        payload = {
            "query": query,
            "cached_at": time.time(),
            "expires_at": time.time() + self._ttl_seconds,
            "research": _serialize_research_context(research),
        }
        self._cache_path(query).write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def get_cached_research(self, query: str) -> Any | None:
        path = self._cache_path(query)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

        expires_at = float(payload.get("expires_at", 0.0))
        if expires_at and expires_at < time.time():
            return None

        research_payload = payload.get("research")
        if not isinstance(research_payload, dict):
            return None

        return _deserialize_research_context(research_payload)

    def _cache_path(self, query: str) -> Path:
        key = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:16]
        return self._cache_dir / f"{key}.json"


def _serialize_research_context(research: Any) -> dict[str, Any]:
    payload = asdict(research)
    payload["workflow_profile"] = asdict(research.workflow_profile)
    return payload


def _deserialize_research_context(payload: dict[str, Any]) -> Any:
    from research import ResearchContext, ResearchSource
    from workflow import ResearchWorkflowProfile

    profile_payload = dict(payload.get("workflow_profile", {}))
    for field_name in (
        "subquestions",
        "search_intents",
        "search_passes",
        "adversarial_queries",
        "stakeholder_perspectives",
    ):
        if field_name in profile_payload:
            profile_payload[field_name] = tuple(profile_payload.get(field_name, ()))

    workflow_profile = ResearchWorkflowProfile(**profile_payload)

    sources = tuple(
        ResearchSource(
            **dict(source_payload),
            )
        for source_payload in payload.get("sources", [])
        if isinstance(source_payload, dict)
    )

    def _tupleize(name: str) -> tuple[Any, ...]:
        value = payload.get(name, ())
        if not isinstance(value, list):
            return tuple(value) if isinstance(value, tuple) else ()
        if name in {"evidence_graph", "corroboration_pairs", "contradictions"}:
            return tuple(tuple(item) if isinstance(item, list) else item for item in value)
        return tuple(value)

    return ResearchContext(
        query=str(payload.get("query", "")),
        workflow_profile=workflow_profile,
        search_terms=tuple(payload.get("search_terms", ())),
        search_passes=tuple(payload.get("search_passes", ())),
        sources=sources,
        generated_at=float(payload.get("generated_at", time.time())),
        contradictions=_tupleize("contradictions"),
        evidence_graph=_tupleize("evidence_graph"),
        corroboration_pairs=_tupleize("corroboration_pairs"),
        topic_coverage_score=float(payload.get("topic_coverage_score", 0.0)),
        research_depth_score=float(payload.get("research_depth_score", 0.0)),
    )


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default