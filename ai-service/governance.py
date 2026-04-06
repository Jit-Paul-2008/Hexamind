from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Mapping

from workflow import ResearchWorkflowProfile


_PII_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[EMAIL]"),
    (r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b", "[PHONE]"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
    (r"\b(?:\d[ -]*?){13,19}\b", "[CARD]"),
)


@dataclass(frozen=True)
class TenantConfig:
    tenant_id: str
    api_keys: dict[str, str] = field(default_factory=dict)
    rate_limits: dict[str, int] = field(default_factory=dict)
    token_budget: int = 50000
    allowed_models: list[str] = field(default_factory=list)
    isolation_mode: str = "shared"


@dataclass(frozen=True)
class TenantResolution:
    tenant_id: str
    config: TenantConfig


def redact_pii(text: str) -> str:
    value = text or ""
    for pattern, replacement in _PII_PATTERNS:
        value = re.sub(pattern, replacement, value)
    return value


def resolve_tenant_resolution(headers: Mapping[str, str] | None = None) -> TenantResolution:
    tenant_id = _resolve_tenant_id(headers)
    config = _load_tenant_config(tenant_id)
    return TenantResolution(tenant_id=tenant_id, config=config)


def select_agent_sequence(
    query: str,
    workflow_profile: ResearchWorkflowProfile | None = None,
) -> tuple[str, ...]:
    framework_version = _framework_version()
    if framework_version == "v3":
        return _v3_twobrain_sequence(query, workflow_profile)
    if framework_version == "v2":
        return _v2_multiagent_sequence(query, workflow_profile)

    # v1 default: single-pass efficient framework (minimal token usage).
    _ = query, workflow_profile
    return ("synthesiser",)


def _framework_version() -> str:
    value = os.getenv("HEXAMIND_FRAMEWORK_VERSION", "v1").strip().lower()
    return value if value in {"v1", "v2", "v3"} else "v1"


def _v2_multiagent_sequence(
    query: str,
    workflow_profile: ResearchWorkflowProfile | None = None,
) -> tuple[str, ...]:
    normalized = (query or "").lower()
    profile = workflow_profile
    query_type = profile.query_type if profile else _query_type_from_text(normalized)
    complexity = profile.complexity_score if profile else _query_complexity_score(normalized)

    if query_type == "comparison" or any(token in normalized for token in ("compare", "versus", " vs ")):
        return ("advocate", "skeptic", "oracle", "verifier", "synthesiser")

    if query_type == "technical":
        return ("verifier", "skeptic", "oracle", "synthesiser")

    if query_type == "decision":
        return ("advocate", "skeptic", "synthesiser", "oracle", "verifier")

    if query_type == "forecast":
        return ("oracle", "verifier", "synthesiser")

    if complexity < 0.35:
        return ("advocate", "skeptic", "synthesiser", "oracle", "verifier")

    if complexity >= 0.75:
        return ("advocate", "skeptic", "oracle", "verifier", "synthesiser")

    return ("advocate", "skeptic", "synthesiser", "oracle", "verifier")


def _v3_twobrain_sequence(
    query: str,
    workflow_profile: ResearchWorkflowProfile | None = None,
) -> tuple[str, ...]:
    """Two-Brain framework: Researcher + Critic for balanced analysis"""
    _ = query, workflow_profile  # Query complexity doesn't change the sequence
    return ("researcher", "critic")


def _resolve_tenant_id(headers: Mapping[str, str] | None = None) -> str:
    if not headers:
        return "default"
    for key in ("X-Tenant-ID", "x-tenant-id", "tenant-id"):
        value = headers.get(key, "")
        if value:
            return _sanitize_identifier(value)
    return "default"


def _sanitize_identifier(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    return cleaned[:64] or "default"


def _load_tenant_config(tenant_id: str) -> TenantConfig:
    raw = os.getenv("HEXAMIND_TENANT_CONFIG_JSON", "").strip()
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            tenant_payload = payload.get(tenant_id) or payload.get("default") or {}
            if isinstance(tenant_payload, dict):
                return _tenant_config_from_payload(tenant_id, tenant_payload)

    return TenantConfig(
        tenant_id=tenant_id,
        token_budget=_env_int("HEXAMIND_TENANT_TOKEN_BUDGET", 50000),
        isolation_mode=os.getenv("HEXAMIND_TENANT_ISOLATION_MODE", "shared").strip().lower() or "shared",
    )


def _tenant_config_from_payload(tenant_id: str, payload: dict[str, object]) -> TenantConfig:
    api_keys = _coerce_str_map(payload.get("api_keys"))
    rate_limits = _coerce_int_map(payload.get("rate_limits"))
    allowed_models = _coerce_str_list(payload.get("allowed_models"))
    token_budget = _coerce_int(payload.get("token_budget"), _env_int("HEXAMIND_TENANT_TOKEN_BUDGET", 50000))
    isolation_mode = str(payload.get("isolation_mode", "shared")).strip().lower() or "shared"
    return TenantConfig(
        tenant_id=tenant_id,
        api_keys=api_keys,
        rate_limits=rate_limits,
        token_budget=token_budget,
        allowed_models=allowed_models,
        isolation_mode=isolation_mode,
    )


def _coerce_str_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if item is not None}


def _coerce_int_map(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for key, item in value.items():
        integer = _coerce_int(item, 0)
        if integer > 0:
            result[str(key)] = integer
    return result


def _coerce_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None and str(item).strip()]


def _coerce_int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _query_type_from_text(query: str) -> str:
    if any(token in query for token in ("compare", "versus", " vs ", "tradeoff", "between")):
        return "comparison"
    if any(token in query for token in ("risk", "failure", "safety", "hazard", "threat")):
        return "technical"
    if any(token in query for token in ("should", "recommend", "decide", "choice", "optimize")):
        return "decision"
    if any(token in query for token in ("forecast", "predict", "outlook", "future", "scenario")):
        return "forecast"
    return "exploratory"


def _query_complexity_score(query: str) -> float:
    words = re.findall(r"[a-zA-Z0-9]{3,}", query.lower())
    unique_words = set(words)
    score = min(1.0, (len(words) / 24.0) + (len(unique_words) / 18.0) * 0.35)
    if any(token in query.lower() for token in ("compare", "versus", "vs", "tradeoff", "benchmark")):
        score += 0.1
    if any(token in query.lower() for token in ("policy", "medical", "clinical", "engineering", "architecture", "reliability")):
        score += 0.08
    return max(0.0, min(1.0, score))
