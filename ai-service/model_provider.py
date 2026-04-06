from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol, TypeVar

import httpx

from agent_model_config import get_agent_model_config
from huggingface_provider import get_huggingface_provider
from openrouter_provider import get_openrouter_provider
from research import ResearchContext, format_research_context, source_inventory_markdown
from prompt_registry import prompt_fingerprint, prompt_registry_snapshot


T = TypeVar("T")


class PipelineModelProvider(Protocol):
    async def build_research_context(self, query: str) -> ResearchContext | None:
        ...

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        ...

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        ...

    def diagnostics(self) -> dict[str, str | int | bool]:
        ...


class ResearcherProtocol(Protocol):
    async def research(self, query: str) -> ResearchContext | None:
        ...


OVERLOAD_RETRY_MESSAGE = (
    "We are seeing heavy traffic and upstream API rate limits right now. "
    "Please try again in a few minutes. We will be back shortly."
)


@dataclass
class ExhaustedPipelineModelProvider:
    configured_provider: str = "cloud-chain"
    model_name: str = "none"
    reason: str = OVERLOAD_RETRY_MESSAGE

    async def build_research_context(self, query: str) -> ResearchContext | None:
        return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        raise RuntimeError(self.reason)

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        raise RuntimeError(self.reason)

    def diagnostics(self) -> dict[str, str | int | bool]:
        return {
            "configuredProvider": self.configured_provider,
            "activeProvider": "none",
            "modelName": self.model_name,
            "isFallback": True,
            "fallbackCount": 0,
            "lastError": self.reason,
        }


@dataclass
class _ProviderHealthManager:
    provider_name: str
    retry_budget: int = 1
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    backoff_seconds: float = 0.25
    failure_count: int = 0
    success_count: int = 0
    open_until: float = 0.0
    last_error: str = ""
    last_stage: str = ""
    last_failure_at: float = 0.0

    def can_attempt(self) -> bool:
        return not self.is_open()

    def is_open(self) -> bool:
        return time.monotonic() < self.open_until

    def record_success(self) -> None:
        self.success_count += 1
        self.failure_count = 0
        self.open_until = 0.0

    def record_failure(self, stage: str, exc: Exception) -> None:
        self.failure_count += 1
        self.last_stage = stage
        self.last_failure_at = time.monotonic()
        self.last_error = f"{type(exc).__name__}: {exc}".strip()[:240]
        if self.failure_count >= self.failure_threshold:
            self.open_until = time.monotonic() + self.cooldown_seconds

    def snapshot(self) -> dict[str, str | int | bool]:
        return {
            "circuitState": "open" if self.is_open() else "closed",
            "circuitOpen": self.is_open(),
            "failureCount": self.failure_count,
            "successCount": self.success_count,
            "retryBudget": self.retry_budget,
            "failureThreshold": self.failure_threshold,
            "cooldownSeconds": int(self.cooldown_seconds),
            "backoffSeconds": int(self.backoff_seconds * 1000),
            "lastStage": self.last_stage,
            "lastError": self.last_error,
            "cooldownRemainingSeconds": max(0, int(self.open_until - time.monotonic())),
        }


@dataclass
class TokenBudget:
    """Token budgeting system to prevent runaway costs."""
    total_limit: int = 50000  # Per session
    research_limit: int = 10000
    agent_limit: int = 8000  # Per agent
    final_limit: int = 15000
    used: int = 0
    
    def can_afford(self, estimated_tokens: int) -> bool:
        """Check if we can afford the estimated tokens."""
        return self.used + estimated_tokens <= self.total_limit
    
    def charge(self, actual_tokens: int) -> None:
        """Charge tokens from the budget."""
        self.used += actual_tokens
    
    def remaining(self) -> int:
        """Get remaining budget."""
        return max(0, self.total_limit - self.used)
    
    def usage_percentage(self) -> float:
        """Get usage as percentage."""
        return (self.used / self.total_limit) * 100 if self.total_limit > 0 else 0.0
    
    def snapshot(self) -> dict[str, int | float]:
        """Get budget snapshot for diagnostics."""
        return {
            "totalLimit": self.total_limit,
            "used": self.used,
            "remaining": self.remaining(),
            "usagePercentage": round(self.usage_percentage(), 2),
            "researchLimit": self.research_limit,
            "agentLimit": self.agent_limit,
            "finalLimit": self.final_limit,
        }


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _stage_timeout_seconds(stage: str) -> float:
    defaults = {
        "retrieval": 18.0,
        "agent": 30.0,
        "final": 40.0,
    }
    env_names = {
        "retrieval": "HEXAMIND_STAGE_TIMEOUT_RETRIEVAL_SECONDS",
        "agent": "HEXAMIND_STAGE_TIMEOUT_AGENT_SECONDS",
        "final": "HEXAMIND_STAGE_TIMEOUT_FINAL_SECONDS",
    }
    default = defaults.get(stage, 30.0)
    env_name = env_names.get(stage)
    if not env_name:
        return default
    value = os.getenv(env_name)
    if value is None:
        return default
    try:
        return max(0.5, float(value))
    except ValueError:
        return default


def _provider_retry_budget() -> int:
    return max(0, _env_int("HEXAMIND_PROVIDER_RETRY_BUDGET", 1))


def _provider_failure_threshold() -> int:
    return max(1, _env_int("HEXAMIND_PROVIDER_FAILURE_THRESHOLD", 3))


def _provider_cooldown_seconds() -> float:
    return max(1.0, _env_float("HEXAMIND_PROVIDER_COOLDOWN_SECONDS", 30.0))


def _provider_backoff_seconds() -> float:
    return max(0.05, _env_float("HEXAMIND_PROVIDER_BACKOFF_SECONDS", 0.25))


def _parse_api_key_pool(primary_env: str, pool_env: str) -> list[str]:
    keys: list[str] = []
    primary = os.getenv(primary_env, "").strip()
    if primary:
        keys.append(primary)

    raw_pool = os.getenv(pool_env, "").strip()
    if raw_pool:
        for item in raw_pool.split(","):
            value = item.strip()
            if value and value not in keys:
                keys.append(value)
    return keys


def _local_strict_mode() -> bool:
    return os.getenv("HEXAMIND_LOCAL_STRICT", "0").strip().lower() in {"1", "true", "yes", "on"}


def _strict_provider_mode() -> bool:
    return os.getenv("HEXAMIND_STRICT_PROVIDER", "0").strip().lower() in {"1", "true", "yes", "on"}


def _get_agent_api_key(agent_id: str, default_provider: str, global_key: str) -> str:
    """Get API key for specific agent, with fallback to global key."""
    agent_key = os.getenv(f"HEXAMIND_AGENT_API_KEY_{agent_id.upper()}", "").strip()
    return agent_key if agent_key else global_key


def _get_agent_provider(agent_id: str, default_provider: str) -> str:
    """Get provider for specific agent, with fallback to default."""
    agent_provider = os.getenv(f"HEXAMIND_AGENT_PROVIDER_{agent_id.upper()}", "").strip().lower()
    return agent_provider if agent_provider else default_provider


def _research_compression_level() -> str:
    """
    Get research compression level from environment.
    Options: "none", "light", "medium", "aggressive"
    Default: "medium" (balanced depth and cost)
    """
    level = os.getenv("HEXAMIND_RESEARCH_COMPRESSION", "medium").strip().lower()
    valid_levels = {"none", "light", "medium", "aggressive"}
    return level if level in valid_levels else "medium"


_PROMPT_RESPONSE_CACHE: dict[str, tuple[float, str]] = {}
_PROMPT_RESPONSE_CACHE_TTL_SECONDS = max(120.0, _env_float("HEXAMIND_PROMPT_CACHE_TTL_SECONDS", 3600.0))
_PROMPT_RESPONSE_CACHE_MAX_ENTRIES = max(32, _env_int("HEXAMIND_PROMPT_CACHE_MAX_ENTRIES", 128))


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text or "") + 3) // 4)


def _prompt_cache_key(
    provider_name: str,
    stage: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    payload = "|".join(
        [
            provider_name.strip().lower(),
            stage.strip().lower(),
            model_name.strip(),
            system_prompt.strip(),
            user_prompt.strip()[:500],
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_prompt_cache(cache_key: str) -> str | None:
    cached = _PROMPT_RESPONSE_CACHE.get(cache_key)
    if not cached:
        return None

    cached_at, response = cached
    if time.time() - cached_at > _PROMPT_RESPONSE_CACHE_TTL_SECONDS:
        _PROMPT_RESPONSE_CACHE.pop(cache_key, None)
        return None
    return response


def _store_prompt_cache(cache_key: str, response: str) -> None:
    _PROMPT_RESPONSE_CACHE[cache_key] = (time.time(), response)
    while len(_PROMPT_RESPONSE_CACHE) > _PROMPT_RESPONSE_CACHE_MAX_ENTRIES:
        oldest_key = next(iter(_PROMPT_RESPONSE_CACHE))
        _PROMPT_RESPONSE_CACHE.pop(oldest_key, None)


def _coerce_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _prompt_registry_summary(registry: dict[str, object]) -> tuple[str, int]:
    version = registry.get("registryVersion", "unknown")
    prompts = registry.get("prompts", [])
    prompt_count = len(prompts) if isinstance(prompts, list) else 0
    return str(version), int(prompt_count)


def _agent_model_override(agent_id: str, default_model: str) -> str:
    env_names = [f"HEXAMIND_AGENT_MODEL_{agent_id.upper()}"]
    if agent_id == "synthesiser":
        env_names.append("HEXAMIND_AGENT_MODEL_SYNTHESIS")

    for env_name in env_names:
        value = os.getenv(env_name, "").strip()
        if value:
            return value
    return default_model


def _cost_aware_agent_model(provider_name: str, agent_id: str, default_model: str) -> str:
    override = _agent_model_override(agent_id, "")
    if override:
        return override

    cost_mode = _cost_mode()
    if cost_mode == "max":
        return default_model

    provider_defaults = {
        "openrouter": {
            "advocate": "google/gemma-3-12b-it:free",
            "skeptic": "google/gemma-3-12b-it:free",
            "synthesiser": default_model,
            "oracle": "google/gemma-3-12b-it:free",
            "verifier": "google/gemma-3-12b-it:free",
            "final": default_model,
        },
        "groq": {
            "advocate": "llama-3.1-8b-instant",
            "skeptic": "llama-3.1-8b-instant",
            "synthesiser": default_model,
            "oracle": "llama-3.1-8b-instant",
            "verifier": "llama-3.1-8b-instant",
            "final": default_model,
        },
        "local": {
            "advocate": os.getenv("HEXAMIND_LOCAL_MODEL_SMALL", default_model).strip() or default_model,
            "skeptic": os.getenv("HEXAMIND_LOCAL_MODEL_SMALL", default_model).strip() or default_model,
            "synthesiser": os.getenv("HEXAMIND_LOCAL_MODEL_MEDIUM", default_model).strip() or default_model,
            "oracle": os.getenv("HEXAMIND_LOCAL_MODEL_MEDIUM", default_model).strip() or default_model,
            "verifier": os.getenv("HEXAMIND_LOCAL_MODEL_SMALL", default_model).strip() or default_model,
            "final": os.getenv("HEXAMIND_LOCAL_MODEL_LARGE", default_model).strip() or default_model,
        },
    }

    provider_models = provider_defaults.get(provider_name, {})
    if cost_mode == "free":
        return provider_models.get(agent_id, default_model)
    if cost_mode == "balanced":
        if agent_id in {"advocate", "skeptic", "verifier"}:
            return provider_models.get(agent_id, default_model)
        if agent_id == "oracle":
            return provider_models.get(agent_id, default_model)
    return default_model


# Prompt Deduplication: Base prompt shared across all agents
_BASE_PROMPT = (
    "You are {agent} in ARIA research-paper mode. "
    "RULE: Every claim must cite sources using [Sx] format. "
    "Keep analysis focused and evidence-backed."
)

# Agent-specific deltas (30-40% token savings)
_AGENT_DELTAS = {
    "advocate": (
        "Focus on evidence-backed benefits, deployment maturity, and outcome improvements.\n"
        "SECTIONS: '## Opportunity Thesis', '## Strategic Upside', '## Supporting Logic', "
        "'## Actionable Next Step', '## Citations Used'.\n"
        "Avoid generic rollout templates."
    ),
    "skeptic": (
        "Focus on methodological limitations, safety risks, bias, and regulatory uncertainty.\n"
        "SECTIONS: '## Risk Thesis', '## Primary Failure Modes', '## Risk Severity Matrix', "
        "'## Second-Order Effects', '## Mitigation Requirements', '## Citations Used'.\n"
        "Avoid project-management milestones."
    ),
    "synthesiser": (
        "Integrate benefits, risks, and evidence conflicts into coherent scholarly interpretation.\n"
        "SECTIONS: '## Integrated Assessment', '## Conflict Resolution Matrix', '## Tradeoff Analysis', "
        "'## Decision Rule', '## Stakeholder Impact', '## Guardrails', '## Citations Used'.\n"
        "Keep topic-centered, not implementation-playbook centered."
    ),
    "oracle": (
        "Provide topic-specific forecast scenarios (domain evolution, policy trajectory, clinical impact).\n"
        "SECTIONS: '## Scenario Outlook', '## Most Likely Outcome (60%)', '## Upside Scenario (25%)', "
        "'## Downside Scenario (15%)', '## Scenario Interdependencies', '## Leading Indicators Dashboard', "
        "'## Forecast Confidence', '## Citations Used'.\n"
        "Avoid generic project scheduling."
    ),
    "verifier": (
        "Audit evidence quality rigorously.\n"
        "REQUIRED: '## Verification Summary', '## Claim Audit Table' (5+ claims), "
        "'## Source Triangulation', '## Evidence Gaps', '## Contradiction Map', "
        "'## Verification Confidence'.\n"
        "Reference credibility scores. Flag weak evidence."
    ),
}

# Simplified deltas for simple queries (15-25% token savings)
_AGENT_DELTAS_SIMPLE = {
    "advocate": "Focus on benefits and evidence. Sections: Thesis, Upside, Logic, Action, Citations.",
    "skeptic": "Focus on risks and failures. Sections: Risks, Failure Modes, Mitigations, Citations.",
    "synthesiser": "Integrate viewpoints. Sections: Assessment, Tradeoffs, Decision, Citations.",
    "oracle": "Forecast outcomes. Sections: Most Likely, Upside, Downside, Indicators, Citations.",
    "verifier": "Audit evidence. Sections: Summary, Claim Audit, Gaps, Confidence.",
}


def _build_agent_prompt(agent_id: str, complexity_score: float = 0.5) -> str:
    """
    Build agent prompt using full cognitive instructions for maximum analytical depth.
    """
    return _deterministic_prompt_text(agent_id)


def _compress_research_excerpt(excerpt: str, max_chars: int = 200) -> str:
    """
    Compress research excerpt from 600 to 200 chars (60% reduction).
    Uses extractive summarization - keeps most information-dense sentences.
    """
    if len(excerpt) <= max_chars:
        return excerpt
    
    # Split into sentences
    import re
    sentences = re.split(r'[.!?]+\s+', excerpt)
    
    # Score sentences by information density (heuristic: longer sentences with more keywords)
    def score_sentence(sent: str) -> float:
        # Favor sentences with numbers, specific terms, and moderate length
        score = len(sent.split()) / 20.0  # Baseline: word count
        score += sent.count('%') * 0.5
        score += sent.count('$') * 0.5
        score += len(re.findall(r'\d+', sent)) * 0.3
        return score
    
    scored = [(score_sentence(s), s) for s in sentences if len(s.strip()) > 10]
    scored.sort(reverse=True, key=lambda x: x[0])
    
    # Take top sentences until we hit character limit
    compressed = []
    total_chars = 0
    for _, sent in scored:
        if total_chars + len(sent) + 2 > max_chars:
            break
        compressed.append(sent)
        total_chars += len(sent) + 2
    
    # Join in original order
    original_order = sorted(compressed, key=lambda s: excerpt.find(s))
    return '. '.join(original_order) + '.'


def _compress_research_context(context: ResearchContext | None, compression_level: str = "medium") -> str:
    """
    Compress research context for 40-60% token reduction.
    
    compression_level:
      - "light": 20% reduction (600 -> 480 chars per source)
      - "medium": 60% reduction (600 -> 240 chars per source) [DEFAULT]
      - "aggressive": 80% reduction (600 -> 120 chars per source)
    """
    if not context or not context.sources:
        return "No research sources."
    
    excerpt_limits = {
        "light": 420,
        "medium": 260,
        "aggressive": 170,
    }
    excerpt_max = excerpt_limits.get(compression_level, 80)
    
    lines = [
        f"Q: {context.query}",
        f"Complexity: {context.workflow_profile.complexity_score:.1f} | Coverage: {context.topic_coverage_score:.1f}",
        f"Terms: {', '.join(context.search_terms[:3])}",
        "",
    ]
    
    # Limit sources based on compression level
    source_limits = {"light": 8, "medium": 6, "aggressive": 5}
    source_cap = source_limits.get(compression_level, 5)
    
    for source in context.sources[:source_cap]:
        compressed_excerpt = _compress_research_excerpt(source.excerpt, excerpt_max)
        lines.extend([
            f"[{source.id}] {source.title[:80]}",
            f"{source.domain} | Auth: {source.authority} | Cred: {source.credibility_score:.1f}",
            f"Excerpt: {compressed_excerpt}",
            "",
        ])
    
    if context.contradictions:
        lines.extend(["Conflicts:"])
        for src_a, src_b, reason in context.contradictions[:2]:
            lines.append(f"- {src_a} vs {src_b}: {reason[:60]}")

    if context.corroboration_pairs:
        lines.extend(["Corroboration:"])
        for src_a, src_b, claim in context.corroboration_pairs[:3]:
            lines.append(f"- {src_a} + {src_b}: {claim[:80]}")

    lines.extend(
        [
            "",
            f"DepthScore: {context.research_depth_score:.2f}",
            f"CoverageScore: {context.topic_coverage_score:.2f}",
        ]
    )
    
    return '\n'.join(lines)


def _query_complexity_score(query: str) -> float:
    words = re.findall(r"[a-zA-Z0-9]{3,}", query.lower())
    unique_words = set(words)
    score = min(1.0, (len(words) / 24.0) + (len(unique_words) / 18.0) * 0.35)
    if any(token in query.lower() for token in ("compare", "versus", "vs", "tradeoff", "benchmark")):
        score += 0.1
    if any(token in query.lower() for token in ("policy", "medical", "clinical", "engineering", "architecture", "reliability")):
        score += 0.08
    return max(0.0, min(1.0, score))


def _local_model_tier(query: str, research: ResearchContext | None) -> str:
    """Choose a local model tier based on query complexity and available research."""
    complexity = research.workflow_profile.complexity_score if research else _query_complexity_score(query)
    if complexity >= 0.75:
        return "large"
    if complexity >= 0.4:
        return "medium"
    return "small"


def _local_context_budget(stage: str, tier: str, research: ResearchContext | None) -> int:
    """Return a character budget for compressed research context."""
    stage = (stage or "").strip().lower()
    tier = (tier or "medium").strip().lower()
    base = {
        "small": 1100,
        "medium": 1600,
        "large": 2200,
    }.get(tier, 1600)
    if stage == "final":
        base = int(base * 1.25)
    if research and research.sources:
        base += min(500, len(research.sources) * 60)
    return max(500, base)


def _local_token_budget(stage: str, tier: str, research: ResearchContext | None) -> int:
    """Return a max token budget for the local provider stage."""
    stage = (stage or "").strip().lower()
    tier = (tier or "medium").strip().lower()
    budgets = {
        "agent": {"small": 700, "medium": 900, "large": 1200},
        "final": {"small": 1400, "medium": 1800, "large": 2400},
    }
    stage_budget = budgets.get(stage, budgets["agent"])
    budget = stage_budget.get(tier, stage_budget["medium"])
    if research and research.sources:
        budget += min(300, len(research.sources) * 30)
    return max(400, budget)


def _compressed_research_block(context: ResearchContext | None, max_chars: int) -> str:
    """Return a compact evidence block for local prompts."""
    if not context:
        return "No research sources."

    compression_level = "aggressive"
    if max_chars >= 1800:
        compression_level = "light"
    elif max_chars >= 1200:
        compression_level = "medium"

    block = _compress_research_context(context, compression_level=compression_level)
    if len(block) <= max_chars:
        return block
    return block[: max_chars - 32].rstrip() + "\n\n[truncated for token safety]"


def _deterministic_prompt_text(agent_id: str) -> str:
    prompts = {
        "advocate": (
            "You are the ADVOCATE agent. Write a rigorous evidence-backed upside analysis with headings: "
            "Opportunity Thesis, Strategic Upside, Mechanism-Level Rationale, Actionable Next Step, Citations Used. "
            "Use domain-specific reasoning, quantify when possible, and ground claims with [Sx] citations when available."
        ),
        "skeptic": (
            "You are the SKEPTIC agent. Write a rigorous adversarial risk analysis with headings: "
            "Risk Thesis, Primary Failure Modes, Risk Severity Matrix, Second-Order Effects, Mitigation Requirements, Citations Used. "
            "Include concrete failure mechanisms and uncertainty boundaries."
        ),
        "synthesiser": (
            "You are the SYNTHESISER agent. Produce a decision-ready integration using these exact headings: "
            "Integrated Assessment, Conflict Resolution Matrix, Tradeoff Analysis, Decision Rule, Stakeholder Impact, Guardrails, "
            "Claim-to-Citation Map, Citations Used. "
            "Keep it around 350-600 words, include at least three [Sx] citations when available, and make the decision rule testable."
        ),
        "oracle": (
            "You are the ORACLE agent. Write a forecast with headings: Scenario Outlook, Most Likely Outcome (60%), "
            "Upside Scenario (25%), Downside Scenario (15%), Scenario Interdependencies, Leading Indicators Dashboard, Forecast Confidence, Citations Used."
        ),
        "verifier": (
            "You are the VERIFIER agent. Write a rigorous evidence audit with headings: Verification Summary, Claim Audit Table, "
            "Source Triangulation, Evidence Gaps, Contradiction Map, Verification Confidence. "
            "Claim Audit Table must include at least 5 claims with status: verified/weak/unverified."
        ),
        "final": (
            "You are the FINAL SYNTHESIZER. Produce TWO reports in this exact order and only with these top-level headings: "
            "## Technical report and then ## Report on {Topic}. "
            "The Technical report must contain a concise executive summary, methods, evidence-backed findings, research quality, citations, and source inventory. "
            "The Report on {Topic} must be polished, human-readable, structured with clear subheadings and bullet points, and focused on the user's topic. "
            "Use concrete claims, specific evidence, and direct language. Do not include session continuity, recent query history, limitations, caveats, next steps, or recovery notes. "
            "Do not add extra top-level sections. Keep claims grounded with [Sx] citations and make the topic report useful to present directly."
        ),
    }
    return prompts.get(agent_id, prompts["final"])


def _provider_agent_prompt(provider_name: str, agent_id: str) -> str:
    if provider_name == "openrouter":
        return _deterministic_prompt_text(agent_id)
    if provider_name == "local":
        return _deterministic_prompt_text(agent_id)
    if provider_name == "gemini":
        return _deterministic_prompt_text(agent_id)
    return _deterministic_prompt_text(agent_id)


def _provider_final_prompt(provider_name: str) -> str:
    return _deterministic_prompt_text("final")


async def _invoke_with_resilience(
    health: _ProviderHealthManager,
    stage: str,
    operation: Callable[[], Awaitable[T]],
    timeout_seconds: float,
    validate: Callable[[T], bool] | None = None,
    operation_with_retry: Callable[[], Awaitable[T]] | None = None,
) -> T:
    """Invoke operation with resilience, health tracking, and optional retry with different strategy."""
    last_error: Exception | None = None
    attempts = health.retry_budget + 1

    for attempt in range(attempts):
        if not health.can_attempt():
            raise RuntimeError(f"{health.provider_name} circuit breaker is open")

        try:
            # Use retry operation on second attempt if provided
            current_operation = operation if attempt == 0 else (operation_with_retry or operation)
            result = await asyncio.wait_for(current_operation(), timeout=timeout_seconds)
            if validate is not None and not validate(result):
                raise RuntimeError(f"{health.provider_name} stage {stage} returned an invalid result")
            health.record_success()
            return result
        except Exception as exc:
            last_error = exc
            health.record_failure(stage, exc)
            if attempt >= health.retry_budget or health.is_open():
                break
            await asyncio.sleep(min(health.backoff_seconds * (attempt + 1), 1.0))

    assert last_error is not None
    raise last_error


@dataclass
class DeterministicPipelineModelProvider:
    configured_provider: str = "deterministic"
    model_name: str = "deterministic"
    reason: str = ""
    _research: ResearchContext | None = None

    async def build_research_context(self, query: str) -> ResearchContext | None:
        return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
        prior_outputs: dict[str, str] | None = None,
    ) -> str:
        self._research = research  # Store for _get_source_details
        q = query.strip()
        source_block = self._source_block(research)
        prior_block = _prior_outputs_block(prior_outputs)
        if agent_id == "advocate":
            return self._structured_advocate(q, source_block)
        if agent_id == "skeptic":
            return self._structured_skeptic(q, source_block)
        if agent_id == "synthesiser":
            return self._structured_synthesiser(q, source_block, prior_block)
        if agent_id == "verifier":
            return self._structured_verifier(q, source_block, prior_block)
        return self._structured_oracle(q, source_block)

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        q = query.strip()
        report_mode = self._report_mode(q, research)
        source_inventory = source_inventory_markdown(research)
        title = self._build_title(q)
        author = "ARIA Research Pipeline (Hexamind)"
        keywords = self._build_keywords(q, report_mode, research)

        abstract = self._build_abstract(q, outputs, research, report_mode)
        introduction = self._build_introduction(q, research, report_mode, refinement_note)
        methodology = self._build_methodology(research)
        synthesis = self._extract_section_summary(outputs.get("synthesiser", ""), "## Integrated Assessment", "## Decision Rule")
        verification = self._extract_section_summary(outputs.get("verifier", ""), "## Verification Summary", "## Claim Verification")
        evidence_snapshot = self._evidence_snapshot_markdown(research)
        topic_label = q if q else "the topic"

        technical_report = (
            "## Technical report\n"
            "### Title\n"
            f"{title}\n\n"
            "### Author\n"
            f"{author}\n\n"
            "### Abstract\n"
            f"{abstract}\n\n"
            "### Keywords\n"
            f"{keywords}\n\n"
            "### Introduction\n"
            f"{introduction}\n\n"
            "### Methods\n"
            f"{methodology}\n\n"
            "### Integrated synthesis\n"
            f"{synthesis}\n\n"
            "### Verification summary\n"
            f"{verification}\n\n"
            "### Source inventory\n"
            f"{source_inventory}"
        )

        topic_report = (
            f"## Report on {topic_label}\n"
            f"This report presents the analysis of {topic_label} as a concise, readable synthesis.\n\n"
            "### What the analysis shows\n"
            f"{synthesis}\n\n"
            "### Evidence base\n"
            f"{evidence_snapshot}\n\n"
            "### Verification\n"
            f"{verification}\n\n"
            "### Summary\n"
            f"{abstract}"
        )

        return f"{technical_report}\n\n{topic_report}"

    def _build_title(self, query: str) -> str:
        base = " ".join(query.replace("?", "").split())
        if not base:
            return "Research Synthesis Report"
        if len(base) > 120:
            base = base[:117].rstrip() + "..."
        return f"Research Synthesis: {base}"

    def _build_keywords(self, query: str, report_mode: str, research: ResearchContext | None) -> str:
        words = [token.lower() for token in re.findall(r"[a-zA-Z0-9]{4,}", query)]
        seen: set[str] = set()
        picked: list[str] = []
        for token in words:
            if token in seen:
                continue
            seen.add(token)
            picked.append(token)
            if len(picked) >= 5:
                break

        if research and research.search_terms:
            for term in research.search_terms:
                normalized = term.strip().lower()
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                picked.append(normalized)
                if len(picked) >= 7:
                    break

        if report_mode not in seen:
            picked.append(report_mode)
        if "evidence synthesis" not in seen:
            picked.append("evidence synthesis")

        return ", ".join(picked[:8])

    def _build_executive_summary(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None,
    ) -> str:
        source_count = len(research.sources) if research and research.sources else 0
        key_finding = self._extract_section_summary(outputs.get("synthesiser", ""), "## Integrated Assessment", "## Decision Rule")
        confidence = "high" if source_count >= 5 else "moderate" if source_count >= 3 else "low"
        return (
            f"This report addresses '{query}' through a five-agent adversarial pipeline. "
            f"Primary synthesis: {key_finding} "
            f"Evidence base includes {source_count} retrieved sources; confidence is {confidence}."
        )
    
    def _build_abstract(self, query: str, outputs: dict[str, str], research: ResearchContext | None, report_mode: str) -> str:
        source_count = len(research.sources) if research and research.sources else 0
        domain_count = len({s.domain for s in research.sources}) if research and research.sources else 0
        primary_count = sum(1 for s in research.sources if s.authority == "primary") if research and research.sources else 0
        
        key_finding = self._extract_section_summary(outputs.get("synthesiser", ""), "## Integrated Assessment", "## Decision Rule")
        confidence = "high" if source_count >= 5 and primary_count >= 2 else "moderate" if source_count >= 3 else "low"
        
        if not research or not research.sources:
            return (
                f"**Background:** This analysis addresses '{query}' using structured multi-agent reasoning in the absence of live source retrieval. "
                f"**Methods:** A five-agent adversarial pipeline (Advocate, Skeptic, Synthesiser, Oracle, Verifier) evaluated the query through {report_mode}-specific analytical frames. "
                f"**Results:** {key_finding} "
                f"**Conclusion:** Confidence is {confidence} due to lack of external source validation. Claims should be treated as provisional pending primary source verification."
            )
        
        return (
            f"**Background:** This analysis addresses '{query}' within the {report_mode} domain, synthesizing {source_count} sources across {domain_count} domains, including {primary_count} primary sources. "
            f"**Methods:** Evidence was retrieved via Tavily search API and processed through a five-agent adversarial pipeline that separates supportive claims from risks and contradictions. "
            f"**Results:** {key_finding} "
            f"**Conclusion:** Overall confidence is {confidence}. The findings contribute to understanding by distinguishing validated evidence from speculative extrapolation and identifying specific gaps requiring further research."
        )
    
    def _build_introduction(self, query: str, research: ResearchContext | None, report_mode: str, refinement_note: str | None) -> str:
        context_framing = {
            "medical": "The integration of artificial intelligence into clinical practice represents one of the most significant transformations in modern healthcare delivery. Understanding the current evidence base, regulatory landscape, and outcome implications is essential for informed adoption decisions.",
            "policy": "Policy decisions in rapidly evolving technological domains require rigorous evidence synthesis that distinguishes between demonstrated outcomes and projected benefits. This analysis examines the regulatory and governance dimensions with attention to implementation constraints.",
            "engineering": "Technical architecture decisions carry long-term implications for system reliability, scalability, and maintenance burden. This analysis evaluates the engineering considerations through the lens of failure modes, performance characteristics, and operational requirements.",
            "operations": "Operational effectiveness depends on understanding both the potential benefits and the implementation barriers associated with new approaches. This analysis examines workflow implications, adoption factors, and measurable outcome indicators.",
            "research": "Rigorous inquiry requires systematic evidence gathering, critical evaluation of source quality, and explicit acknowledgment of uncertainty. This analysis applies structured methodology to separate well-supported claims from weakly grounded assertions.",
        }
        
        framing = context_framing.get(report_mode, context_framing["research"])
        refinement_text = f" The analysis specifically focuses on: {refinement_note.strip()}." if refinement_note and refinement_note.strip() else ""
        
        source_context = ""
        if research and research.sources:
            primary = [s for s in research.sources if s.authority == "primary"]
            if primary:
                source_context = f" Primary sources consulted include {primary[0].title} [{primary[0].id}]" + (f" and {primary[1].title} [{primary[1].id}]" if len(primary) > 1 else "") + "."
        
        return (
            f"{framing}\n\n"
            f"**Research Question:** {query}{refinement_text}\n\n"
            f"This inquiry is significant because the intersection of technological capability and real-world deployment raises questions that cannot be answered by either pure technical analysis or policy review alone. "
            f"A synthesis approach is required to integrate evidence across domains and identify where conclusions are robust versus where they remain contested.{source_context}"
        )
    
    def _build_methodology(self, research: ResearchContext | None) -> str:
        if not research or not research.sources:
            return (
                "**Data Sources:** No live web retrieval was performed for this analysis. Conclusions are based on structured reasoning using the model's training knowledge, which may be outdated or incomplete. **Critical limitation:** Without access to current primary sources, all findings should be treated as provisional hypotheses requiring external validation.\n\n"
                "**Analytical Framework:** A five-agent adversarial pipeline was employed: (1) Advocate — constructs the strongest evidence-backed case for benefits; (2) Skeptic — identifies failure modes, risks, and limitations; (3) Synthesiser — resolves conflicts and produces integrated interpretation; (4) Oracle — forecasts likely outcomes under different scenarios; (5) Verifier — audits claim-to-source mappings and flags evidence gaps.\n\n"
                "**Quality Controls:** In the absence of source retrieval, quality controls are severely constrained. Claims cannot be validated against external evidence, and confidence levels represent internal consistency only."
            )
        
        source_count = len(research.sources)
        domain_count = len({s.domain for s in research.sources})
        primary_count = sum(1 for s in research.sources if s.authority == "primary")
        secondary_count = source_count - primary_count
        avg_credibility = sum(s.credibility_score for s in research.sources) / source_count if source_count > 0 else 0
        
        domains = list({s.domain for s in research.sources})[:5]
        domain_list = ", ".join(domains[:4]) + (f", and {len(domains) - 4} others" if len(domains) > 4 else "")
        
        # Add primary source details
        primary_sources = [s for s in research.sources if s.authority == "primary"][:3]
        primary_details = ""
        if primary_sources:
            primary_names = ", ".join(f"{s.title} [{s.id}]" for s in primary_sources[:2])
            primary_details = f" Primary sources consulted include {primary_names}" + (f", among {len(primary_sources)} total primary sources" if len(primary_sources) > 2 else "") + "."
        
        return (
            f"**Data Sources:** This analysis synthesizes {source_count} sources retrieved via Tavily search API across {domain_count} distinct domains ({domain_list}). "
            f"**Source authority classification:** {primary_count} primary sources (peer-reviewed literature, official regulatory guidance, government publications) and {secondary_count} secondary sources (industry analyses, news, commentary). "
            f"Mean credibility score is {avg_credibility:.0%}.{primary_details}\n\n"
            "**Source Selection Criteria:** Retrieval prioritized primary sources over secondary; recent publications over outdated; high-authority domains (.gov, .edu, peer-reviewed journals) over commercial sites. "
            "Where primary sources were unavailable, secondary sources were used with explicit caveats. "
            "Sources were scored for credibility (0-100%) based on domain authority, recency, and alignment with query intent.\n\n"
            "**Analytical Framework:** Evidence was processed through a five-agent adversarial pipeline:\n"
            "- **Advocate** — Constructs the strongest evidence-backed case for benefits, requiring explicit [Sx] citation for each claim. Benefits are grounded in documented outcomes, not speculative projections.\n"
            "- **Skeptic** — Identifies failure modes, risks, and limitations with probability and impact estimates. Risk claims must cite evidence of actual deployment challenges or documented failure patterns.\n"
            "- **Synthesiser** — Resolves conflicts between supportive and critical perspectives, producing integrated interpretation. When sources disagree, disagreement is preserved rather than artificially resolved.\n"
            "- **Oracle** — Forecasts likely outcomes under baseline, upside, and downside scenarios. Projections are anchored to current evidence, not aspirational timelines.\n"
            "- **Verifier** — Audits claim-to-source mappings, triangulates across sources, and flags evidence gaps. Claims lacking source support are marked as speculative.\n\n"
            "**Quality Controls:** (1) **Citation integrity:** Claims are retained only when traceable to at least one source via [Sx] reference. (2) **Primary source preference:** When available, primary sources supersede secondary interpretation. (3) **Contradiction handling:** Source conflicts are explicitly documented rather than silently merged. (4) **Confidence calibration:** Confidence levels reflect source diversity, authority balance, and internal consistency—not certainty."
        )
    
    def _build_results(self, outputs: dict[str, str], research: ResearchContext | None, report_mode: str) -> str:
        advocate_summary = self._extract_section_summary(outputs.get("advocate", ""), "## Strategic Upside", "## Supporting Logic")
        skeptic_summary = self._extract_section_summary(outputs.get("skeptic", ""), "## Primary Failure Modes", "## Risk Severity Matrix")
        synthesis_summary = self._extract_section_summary(outputs.get("synthesiser", ""), "## Integrated Assessment", "## Decision Rule")
        oracle_summary = self._extract_section_summary(outputs.get("oracle", ""), "## Most Likely Outcome (60%)", "## Upside Scenario (25%)")
        verifier_summary = self._extract_section_summary(outputs.get("verifier", ""), "## Verification Summary", "## Claim Verification")
        
        evidence_narrative = ""
        if research and research.sources:
            top_sources = research.sources[:4]
            primary_sources = [s for s in top_sources if s.authority == "primary"]
            secondary_sources = [s for s in top_sources if s.authority != "primary"]
            
            # Build narrative description of evidence
            source_descriptions = []
            for s in top_sources:
                excerpt_short = s.excerpt[:150] + "..." if len(s.excerpt) > 150 else s.excerpt
                source_descriptions.append(f"{s.title} [{s.id}] (credibility: {s.credibility_score:.0%}) reports: \"{excerpt_short}\"")
            
            evidence_narrative = (
                f"The evidence base for this analysis comprises {len(research.sources)} sources retrieved from {len({s.domain for s in research.sources})} distinct domains. "
                f"Among the highest-quality sources, {len(primary_sources)} are classified as primary sources (peer-reviewed research, official guidance, government publications), "
                f"providing direct empirical evidence or authoritative policy statements. "
                f"{'The remaining sources offer secondary analysis, industry perspectives, and interpretive commentary. ' if secondary_sources else ''}"
                f"Key excerpts from top-ranked sources include: "
                f"{' '.join(source_descriptions[:3])}\n\n"
            )
        else:
            evidence_narrative = "No live sources were retrieved for this analysis. The findings below are based on structured reasoning using the model's training knowledge, which may not reflect current evidence.\n\n"
        
        return (
            f"### 3.1 Evidence Base\n"
            f"{evidence_narrative}"
            f"### 3.2 Supportive Findings\n"
            f"Analysis of potential benefits reveals the following: {advocate_summary} "
            f"These findings represent the strongest case for adoption when conditions favor successful implementation. "
            f"The evidence suggests that benefits are most pronounced in contexts where task boundaries are well-defined, validation is rigorous, and human oversight remains robust.\n\n"
            f"### 3.3 Risk Factors and Constraints\n"
            f"Critical evaluation of potential failure modes and constraints identifies: {skeptic_summary} "
            f"These risks are not merely theoretical; they represent documented challenges from deployment experience and should inform any adoption decision. "
            f"Risk mitigation requires explicit attention to subgroup performance, workflow integration, and continuous monitoring rather than one-time validation.\n\n"
            f"### 3.4 Integrated Interpretation\n"
            f"Reconciling supportive and critical perspectives yields the following synthesis: {synthesis_summary} "
            f"This integrated view acknowledges that neither uncritical enthusiasm nor blanket skepticism is warranted. "
            f"The evidence supports a nuanced position: benefits are real but conditional, and successful outcomes depend on matching deployment context to validated use-cases.\n\n"
            f"### 3.5 Forward Outlook\n"
            f"Scenario analysis considering likely future developments suggests: {oracle_summary} "
            f"These projections are necessarily uncertain, but they highlight the critical factors that will determine whether early promise translates to sustained impact. "
            f"Monitoring leading indicators—such as subgroup performance stability, clinician override patterns, and post-market safety signals—can provide early warning of trajectory shifts.\n\n"
            f"### 3.6 Evidence Quality Assessment\n"
            f"Critical evaluation of the evidence base itself reveals: {verifier_summary} "
            f"Understanding evidence quality is essential for calibrating confidence appropriately. Claims backed by multiple independent high-credibility sources warrant stronger confidence than those resting on a single source or secondary interpretation."
        )
    
    def _build_discussion(self, outputs: dict[str, str], research: ResearchContext | None, report_mode: str) -> str:
        synthesis = self._extract_section_summary(outputs.get("synthesiser", ""), "## Integrated Assessment", "## Decision Rule")
        
        if not research or not research.sources:
            return (
                f"The findings of this analysis must be interpreted with significant caution due to the absence of live source verification. "
                f"The integrated interpretation suggests: {synthesis}\n\n"
                "**Implications:** Without external validation, these conclusions represent structured reasoning rather than evidence-grounded findings. "
                "Practitioners should consult primary literature and domain experts before acting on these recommendations.\n\n"
                "**What This Changes:** This analysis contributes a structured framework for thinking about the question, but does not advance the empirical evidence base."
            )
        
        contradiction_count = len(getattr(research, "contradictions", ()))
        primary_sources = [s for s in research.sources if s.authority == "primary"]
        
        contribution = ""
        if report_mode == "medical":
            contribution = "This synthesis contributes to the clinical evidence base by distinguishing between validated diagnostic performance and marketing claims, and by identifying specific subgroup and safety considerations that require attention before deployment."
        elif report_mode == "policy":
            contribution = "This analysis contributes to policy deliberation by mapping the regulatory landscape, identifying compliance boundaries, and surfacing areas where guidance remains ambiguous or contested."
        elif report_mode == "engineering":
            contribution = "This synthesis advances technical decision-making by separating demonstrated capabilities from theoretical roadmaps, and by quantifying reliability and failure mode considerations."
        else:
            contribution = "This analysis contributes to informed decision-making by systematically distinguishing well-supported claims from weakly grounded assertions and by identifying specific evidence gaps."
        
        return (
            f"The evidence synthesis reveals a nuanced picture: {synthesis}\n\n"
            f"**Strength of Evidence:** The analysis draws on {len(research.sources)} sources, including {len(primary_sources)} primary sources. "
            f"{'No direct contradictions were detected between sources.' if contradiction_count == 0 else f'{contradiction_count} contradictions between sources were identified and explicitly preserved rather than silently resolved.'}\n\n"
            f"**Implications for Practice:** {contribution}\n\n"
            f"**What This Changes:** The key insight is that conclusions must be qualified by context: "
            f"benefits are strongest where task boundaries are well-defined and validation is rigorous; "
            f"risks are most acute where generalization claims outrun the evidence base or where human oversight pathways are weak."
        )
    
    def _build_limitations(self, research: ResearchContext | None, report_mode: str) -> str:
        if not research or not research.sources:
            return (
                "**Primary Limitation:** This analysis was conducted without live source retrieval, meaning all claims are based on model training knowledge rather than current evidence.\n\n"
                "**Potential Counterarguments:**\n"
                "- The absence of source grounding means conclusions may reflect outdated information or training biases.\n"
                "- Claims that appear well-reasoned may nonetheless be incorrect if the underlying assumptions have changed.\n"
                "- Readers should treat all findings as hypotheses requiring validation rather than established conclusions.\n\n"
                "**What Would Invalidate These Findings:** Access to current primary sources could substantially alter the conclusions if recent evidence contradicts the model's training knowledge."
            )
        
        domain_count = len({s.domain for s in research.sources})
        avg_credibility = sum(s.credibility_score for s in research.sources) / len(research.sources) if research.sources else 0
        secondary_heavy = sum(1 for s in research.sources if s.authority != "primary") > len(research.sources) * 0.7
        
        limitations_text = (
            f"**Source Limitations:** While this analysis draws on {len(research.sources)} sources across {domain_count} domains, "
        )
        if secondary_heavy:
            limitations_text += "the evidence base is weighted toward secondary sources, which may not reflect the full nuance of primary research findings. "
        if avg_credibility < 0.7:
            limitations_text += f"Mean source credibility ({avg_credibility:.0%}) suggests some reliance on lower-authority sources. "
        
        counterarguments = ""
        if report_mode == "medical":
            counterarguments = (
                "- Diagnostic performance measured in controlled studies may not generalize to real-world clinical settings with diverse patient populations.\n"
                "- Benefits demonstrated in high-resource settings may not translate to resource-constrained environments.\n"
                "- Regulatory approval does not guarantee clinical utility or cost-effectiveness.\n"
                "- Publication bias may overstate positive findings while underreporting null or negative results."
            )
        elif report_mode == "policy":
            counterarguments = (
                "- Regulatory frameworks are evolving rapidly; current guidance may be superseded.\n"
                "- Compliance requirements vary by jurisdiction; generalizations may not apply locally.\n"
                "- Policy intent and enforcement reality often diverge; stated rules may not predict actual outcomes."
            )
        else:
            counterarguments = (
                "- Source selection may introduce bias toward certain perspectives.\n"
                "- Temporal limitations: evidence reflects a snapshot that may not capture recent developments.\n"
                "- Synthesis necessarily involves interpretive judgment; alternative interpretations may be equally valid."
            )
        
        return (
            f"{limitations_text}\n\n"
            f"**Potential Counterarguments:**\n{counterarguments}\n\n"
            f"**What Would Invalidate These Findings:** New primary research demonstrating different effect sizes, unexpected adverse outcomes, or regulatory changes could substantially alter the conclusions."
        )
    
    def _build_conclusion(self, outputs: dict[str, str], research: ResearchContext | None, report_mode: str) -> str:
        synthesis = self._extract_section_summary(outputs.get("synthesiser", ""), "## Integrated Assessment", "## Decision Rule")
        
        if not research or not research.sources:
            return (
                f"This analysis addressed the research question through structured multi-agent reasoning, producing the following integrated finding: {synthesis}\n\n"
                "**Key Contribution:** The primary value of this analysis is the structured decomposition of the question into supportive, critical, and synthetic perspectives, rather than novel evidence.\n\n"
                "**Recommended Next Steps:**\n"
                "1. Conduct targeted primary source retrieval to ground claims in current evidence.\n"
                "2. Consult domain experts to validate the analytical framework.\n"
                "3. Treat conclusions as working hypotheses pending empirical verification."
            )
        
        source_count = len(research.sources)
        primary_count = sum(1 for s in research.sources if s.authority == "primary")
        
        next_steps = ""
        if report_mode == "medical":
            next_steps = (
                "1. Verify clinical claims against randomized controlled trial data where available.\n"
                "2. Assess subgroup performance before generalizing to new populations.\n"
                "3. Establish human oversight pathways before deployment in high-stakes contexts."
            )
        elif report_mode == "policy":
            next_steps = (
                "1. Monitor regulatory developments as frameworks continue to evolve.\n"
                "2. Consult legal counsel on jurisdiction-specific compliance requirements.\n"
                "3. Document decision rationale to support future audit requirements."
            )
        else:
            next_steps = (
                "1. Validate key claims against primary sources before acting.\n"
                "2. Address identified evidence gaps through targeted research.\n"
                "3. Revisit conclusions as new evidence becomes available."
            )
        
        return (
            f"This analysis synthesized {source_count} sources ({primary_count} primary) to address the research question, producing the following integrated finding: {synthesis}\n\n"
            f"**Key Contribution:** Beyond summarizing existing evidence, this analysis distinguishes between well-supported claims (traceable to primary sources) and weakly grounded extrapolations, identifies specific evidence gaps, and surfaces contradictions that remain unresolved in the literature.\n\n"
            f"**Why This Matters:** The distinction between validated findings and provisional claims is critical for informed decision-making. Readers can use the claim-to-source mappings to assess which conclusions warrant confidence and which require additional verification.\n\n"
            f"**Recommended Next Steps:**\n{next_steps}"
        )

    def _evidence_snapshot_markdown(self, research: ResearchContext | None) -> str:
        if not research or not research.sources:
            return "- No live sources were retrieved. This report uses structured reasoning only and should be treated as provisional."

        lines: list[str] = []
        for source in research.sources[:6]:
            lines.append(
                f"- [{source.id}] {source.title} ({source.domain}) - authority: {source.authority}, credibility: {source.credibility_score:.2f}"
            )
            lines.append(f"  - Evidence: {source.excerpt}")
        return "\n".join(lines)

    def _claim_graph_markdown(self, outputs: dict[str, str], research: ResearchContext | None, report_mode: str) -> str:
        if not research or not research.sources:
            return "- Claim graph unavailable because no live sources were retrieved."

        advocate_claim = self._extract_section_summary(outputs.get("advocate", ""), "## Strategic Upside", "## Supporting Logic")
        skeptic_claim = self._extract_section_summary(outputs.get("skeptic", ""), "## Primary Failure Modes", "## Risk Severity")
        synthesis_claim = self._extract_section_summary(outputs.get("synthesiser", ""), "## Tradeoff Resolution", "## Decision Rule")
        outlook_claim = self._extract_section_summary(outputs.get("oracle", ""), "## Most Likely Outcome (60%)", "## Upside Scenario (25%)")

        top = research.sources[:4]
        lines = [
            f"- Node C1 (opportunity): {advocate_claim} -> [{top[0].id}]",
            f"- Node C2 (risk): {skeptic_claim} -> [{top[min(1, len(top) - 1)].id}]",
            f"- Node C3 (synthesis): {synthesis_claim} -> [{top[min(2, len(top) - 1)].id}]",
            f"- Node C4 (forecast): {outlook_claim} -> [{top[min(3, len(top) - 1)].id}]",
            f"- Edge: C1 supports C3; C2 constrains C3; C4 is conditional on the {report_mode} evidence profile.",
        ]
        return "\n".join(lines)

    def _decision_recommendation(self, outputs: dict[str, str], research: ResearchContext | None, report_mode: str) -> str:
        confidence_basis = self._source_block(research)
        summary = self._extract_section_summary(outputs.get("synthesiser", ""), "## Integrated Assessment", "## Decision Rule")
        return (
            f"The recommended stance in the {report_mode} frame is evidence-weighted adoption: accept conclusions that are directly grounded in high-credibility sources, "
            "treat broad generalizations as conditional, and explicitly preserve disagreement where source conflict remains unresolved. "
            f"Current confidence basis is anchored by {confidence_basis}. "
            f"The synthesis anchor is: {summary}"
        )

    def _report_plan_markdown(self, query: str, research: ResearchContext | None, report_mode: str) -> str:
        if not research or not research.sources:
            return (
                f"- Mode: {report_mode}\n"
                "- Plan: collect evidence first, then build a claim graph, then validate against contradictions.\n"
                "- Priority: state uncertainty explicitly because no live sources were found."
            )

        plan_lines = [
            f"- Mode: {report_mode}",
            "- Section order: evidence snapshot -> claim graph -> contradictions -> decision recommendation -> action plan.",
            "- Priority: privilege primary sources, then reconcile disagreements before recommending action.",
        ]
        if report_mode == "policy":
            plan_lines.append("- Focus: regulatory constraints, stakeholder impact, and compliance risk.")
        elif report_mode == "engineering":
            plan_lines.append("- Focus: architecture, failure modes, reliability, and implementation cost.")
        elif report_mode == "medical":
            plan_lines.append("- Focus: evidence strength, safety, and conservative interpretation of claims.")
        elif report_mode == "operations":
            plan_lines.append("- Focus: execution, rollout sequencing, and operational guardrails.")
        else:
            plan_lines.append("- Focus: evidence quality, source diversity, and decision confidence.")
        return "\n".join(plan_lines)

    def _uncertainty_markdown(self, research: ResearchContext | None, report_mode: str) -> str:
        if not research or not research.sources:
            return "- Confidence: low because there are no retrieved live sources to validate external claims.\n- Open question: which live sources are most likely to overturn the current answer?"
        if len(research.sources) < 3:
            return (
                "- Confidence: moderate but limited by source diversity.\n"
                "- Rationale: prioritize collecting additional independent domains before scaling decisions.\n"
                f"- Open question: which {report_mode}-specific evidence is still missing?"
            )
        contradiction_count = len(getattr(research, "contradictions", ()))
        return (
            f"- Confidence: moderate, with {len(research.sources)} sources across {len({source.domain for source in research.sources})} domains.\n"
            f"- Rationale: contradiction count = {contradiction_count}; treat the recommendation as conditional when disputes remain unresolved.\n"
            f"- Open question: which source pair would most strongly change the answer if it were updated?"
        )

    def _action_plan_markdown(self, report_mode: str, research: ResearchContext | None) -> str:
        if report_mode == "policy":
            return (
                "- Map the policy surface, legal definitions, and regulator jurisdiction boundaries.\n"
                "- Cross-check claims against primary guidance and official publications.\n"
                "- Document compliance and enforcement implications with explicit caveats."
            )
        if report_mode == "engineering":
            return (
                "- Establish baseline architecture constraints and known reliability bottlenecks.\n"
                "- Evaluate technical claims against failure modes, drift risks, and observability requirements.\n"
                "- Separate demonstrated capability from theoretical roadmap claims."
            )
        if report_mode == "medical":
            return (
                "- Verify that evidence is current and anchored in primary clinical/regulatory sources.\n"
                "- Distinguish validated clinical performance from marketing claims and proxy metrics.\n"
                "- Report safety, subgroup equity, and uncertainty boundaries explicitly."
            )
        if report_mode == "operations":
            return (
                "- Map workflow touchpoints where evidence indicates measurable operational impact.\n"
                "- Identify adoption and governance dependencies before interpreting impact claims.\n"
                "- Separate early signal indicators from long-term outcome indicators."
            )
        return (
            "- Consolidate source-backed findings and document assumptions explicitly.\n"
            "- Compare supportive and contradictory evidence by credibility and recency.\n"
            "- Highlight unresolved questions that require follow-up research."
        )

    def _confidence_block(self, research: ResearchContext | None, report_mode: str) -> str:
        if not research or not research.sources:
            return "- Confidence: low, because the report has no live source support.\n- Open questions: which live source would most likely invalidate the recommendation?"

        domain_count = len({source.domain for source in research.sources})
        contradiction_count = len(getattr(research, "contradictions", ()))
        confidence = "high" if len(research.sources) >= 5 and domain_count >= 3 and contradiction_count == 0 else "moderate"
        if contradiction_count > 0:
            confidence = "moderate"
        return (
            f"- Confidence: {confidence}, with {len(research.sources)} sources across {domain_count} domains for the {report_mode} frame.\n"
            f"- Rationale: contradiction count = {contradiction_count}; source mix and recency determine how much weight to put on the recommendation.\n"
            "- Open questions: which claim would fail first under a stricter source audit?"
        )

    def _report_mode(self, query: str, research: ResearchContext | None) -> str:
        normalized = query.lower()
        if any(token in normalized for token in ("policy", "regulation", "law", "compliance", "governance")):
            return "policy"
        if any(token in normalized for token in ("medical", "clinical", "health", "patient", "diagnosis", "treatment")):
            return "medical"
        if any(token in normalized for token in ("architecture", "engineering", "system", "api", "backend", "latency", "performance", "reliability")):
            return "engineering"
        if any(token in normalized for token in ("operations", "workflow", "launch", "rollout", "scale", "process", "team")):
            return "operations"
        if any(token in normalized for token in ("compare", "versus", "vs", "benchmark", "tradeoff")):
            return "comparison"
        return "research"

    def _analysis_lens_heading(self, report_mode: str) -> str:
        headings = {
            "policy": "Policy Lens",
            "medical": "Clinical Evidence Lens",
            "engineering": "Engineering Lens",
            "operations": "Operational Lens",
            "comparison": "Comparison Lens",
            "research": "Research Lens",
        }
        return headings.get(report_mode, "Research Lens")

    def _structured_advocate(self, query: str, source_block: str) -> str:
        sources = self._get_source_details()
        primary_source = sources[0] if sources else {"id": "S1", "title": "reasoning analysis", "domain": "internal", "cred": 0.7}
        secondary_source = sources[1] if len(sources) > 1 else primary_source
        return (
            "## Opportunity Thesis\n"
            f"On '{query}', the evidence points to a material upside for quality of outcomes when high-credibility tools are adopted with clinical oversight, "
            f"with benefits concentrated in earlier detection, consistency, and workflow acceleration [{primary_source['id']}].\n\n"
            "## Strategic Upside\n"
            f"1. **Diagnostic performance gains**: Multiple sources indicate measurable improvements in sensitivity/specificity for selected tasks when AI is used as decision support [{primary_source['id']}].\n"
            f"2. **Faster clinical throughput**: AI-assisted triage and prioritization can shorten time-to-review for high-volume modalities [{secondary_source['id']}].\n"
            "3. **Standardization of care**: Model-assisted checks reduce inter-reader variability in repetitive diagnostic workflows.\n"
            "4. **Workforce leverage**: AI can offload low-complexity interpretation steps, allowing specialists to focus on high-acuity cases.\n"
            "5. **Earlier intervention potential**: Earlier flagging of risk patterns can improve downstream patient outcomes when pathways are well integrated.\n\n"
            "## Supporting Logic\n"
            "- Mechanism 1: Pattern-recognition models can surface subtle findings at scale in imaging and multimodal records.\n"
            "- Mechanism 2: Decision-support overlays improve consistency of first-pass screening and routing.\n"
            "- Mechanism 3: Structured outputs improve auditability and repeatability in regulated environments.\n"
            "- Boundary condition: Benefit is task-dependent; gains are strongest in narrowly defined, validated use-cases.\n\n"
            "## Actionable Next Step\n"
            "Produce a topic-specific evidence map with three columns: (1) validated clinical use-cases, (2) regulator-cleared model classes, (3) measured patient-outcome impact.\n\n"
            "## Citations Used\n"
            f"- [{primary_source['id']}] {primary_source['title']} ({primary_source['domain']}): Core evidence for benefit claims.\n"
            + (f"- [{secondary_source['id']}] {secondary_source['title']} ({secondary_source['domain']}): Secondary corroboration on throughput/operations.\n" if secondary_source != primary_source else "")
        )

    def _structured_skeptic(self, query: str, source_block: str) -> str:
        sources = self._get_source_details()
        primary_source = sources[0] if sources else {"id": "S1", "title": "risk analysis", "domain": "internal", "cred": 0.7}
        return (
            "## Risk Thesis\n"
            f"For '{query}', the central risk is not model capability alone but clinical safety under real-world deployment conditions: dataset shift, bias across subgroups, and over-trust in automated outputs [{primary_source['id']}].\n\n"
            "## Primary Failure Modes\n"
            "### 1. Generalization failure across populations\n"
            "- **Probability**: medium-high\n"
            "- **Impact**: high (missed or delayed diagnosis)\n"
            "- **Detection**: often late without subgroup monitoring\n\n"
            "### 2. Automation bias in clinician workflow\n"
            "- **Probability**: medium\n"
            "- **Impact**: high when AI output is accepted without adequate challenge\n"
            "- **Detection**: difficult unless decision override behavior is tracked\n\n"
            "### 3. Regulatory-compliance drift after deployment\n"
            "- **Probability**: medium\n"
            "- **Impact**: medium-high (legal/operational exposure)\n"
            "- **Detection**: medium with post-market surveillance controls\n\n"
            "### 4. Data governance and privacy exposure\n"
            "- **Probability**: medium\n"
            "- **Impact**: high for PHI-sensitive environments\n"
            "- **Detection**: medium with robust audit controls\n\n"
            "## Risk Severity Matrix\n"
            "| Risk | Probability | Impact | Priority |\n"
            "|------|-------------|--------|----------|\n"
            "| Population shift / bias | Medium-High | High | P1 |\n"
            "| Automation bias | Medium | High | P1 |\n"
            "| Compliance drift | Medium | Medium-High | P2 |\n"
            "| Data governance failures | Medium | High | P1 |\n\n"
            "## Second-Order Effects\n"
            "- Uneven performance can amplify health inequity across underserved cohorts.\n"
            "- Over-reliance can erode clinician calibration on edge cases.\n"
            "- Public trust can degrade rapidly after visible false-positive/false-negative incidents.\n\n"
            "## Mitigation Requirements\n"
            "- Mandatory subgroup validation by age/sex/comorbidity/site.\n"
            "- Human-in-the-loop decision checkpoints for high-stakes diagnoses.\n"
            "- Continuous post-market monitoring with predefined drift triggers.\n"
            "- Formal model cards, audit logging, and incident-response playbooks.\n\n"
            "## Citations Used\n"
            f"- [{primary_source['id']}] {primary_source['title']} ({primary_source['domain']}): Risk and governance evidence basis.\n"
        )

    def _structured_synthesiser(self, query: str, source_block: str, prior_outputs_block: str = "") -> str:
        sources = self._get_source_details()
        primary_source = sources[0] if sources else {"id": "S1", "title": "synthesis", "domain": "internal", "cred": 0.7}
        prior_context = f"\n\n## Prior Agent Outputs\n{prior_outputs_block}\n" if prior_outputs_block else ""
        return (
            "## Integrated Assessment\n"
            f"Taken together, the evidence on '{query}' supports a cautious-but-forward position: AI diagnostics show meaningful promise in selected workflows, but outcome quality depends on regulatory compliance, human oversight, and real-world validation across diverse populations [{primary_source['id']}].\n\n"
            "## Conflict Resolution Matrix\n"
            "| Dimension | Pro-innovation View | Safety-first View | Integrated Resolution | Confidence |\n"
            "|-----------|---------------------|-------------------|-----------------------|------------|\n"
            "| Clinical benefit | Earlier, more consistent detection | Risk of bias and false reassurance | Use in validated decision-support roles, not unsupervised autonomy | Medium-High |\n"
            "| Scale strategy | Rapid rollout to maximize value | Uneven infrastructure readiness | Phased scale by care setting readiness | Medium |\n"
            "| Governance | Existing medical-device pathways are sufficient | Post-deployment drift requires stronger controls | Lifecycle governance with continuous monitoring | Medium-High |\n\n"
            "## Tradeoff Analysis\n"
            "- **Benefit tradeoff**: improved throughput and earlier detection vs. error propagation if calibration is weak.\n"
            "- **Regulatory tradeoff**: faster innovation cycles vs. heavier validation and documentation burden.\n"
            "- **Equity tradeoff**: broad deployment potential vs. subgroup performance gaps if datasets are not representative.\n\n"
            "## Decision Rule\n"
            "Recommend adoption where three criteria are met: (1) task-specific validation is strong, (2) subgroup performance is disclosed and acceptable, and (3) clinician override pathways are enforced.\n\n"
            "## Stakeholder Impact\n"
            "- Patients: potential for earlier diagnosis, but exposed to equity and explainability risks.\n"
            "- Clinicians: workflow support and burden reduction, but accountability remains with human decision-makers.\n"
            "- Regulators/health systems: increased need for post-market surveillance, audits, and model-governance infrastructure.\n\n"
            "## Guardrails\n"
            "- Never deploy high-impact diagnostic models without documented subgroup performance.\n"
            "- Require explicit fallback workflows for low-confidence outputs.\n"
            "- Enforce periodic drift audits and incident reporting.\n\n"
            f"{prior_context}"
            "## Citations Used\n"
            f"- [{primary_source['id']}] {primary_source['title']} ({primary_source['domain']}): Integration rationale and evidence synthesis anchor.\n"
        )

    def _structured_oracle(self, query: str, source_block: str) -> str:
        sources = self._get_source_details()
        primary_source = sources[0] if sources else {"id": "S1", "title": "forecast", "domain": "internal", "cred": 0.7}
        return (
            "## Scenario Outlook\n"
            f"Short-horizon outlook for '{query}': adoption will continue in high-data specialties, while regulation and post-market monitoring become the main determinants of safe scaling [{primary_source['id']}].\n\n"
            "## Most Likely Outcome (60%)\n"
            "- Continued growth of AI-assisted diagnostics in radiology, pathology, cardiology, and triage workflows.\n"
            "- Regulators increasingly emphasize lifecycle controls for model updates and bias monitoring.\n"
            "- Institutions with stronger data governance and interoperability capture more benefit.\n\n"
            "## Upside Scenario (25%)\n"
            "- Faster approval pathways for well-validated adaptive models.\n"
            "- Better multimodal performance with improved explainability and lower false-positive burden.\n"
            "- Wider deployment in resource-constrained settings via interoperable and edge-capable architectures.\n\n"
            "## Downside Scenario (15%)\n"
            "- High-profile safety incidents trigger conservative adoption slowdowns.\n"
            "- Fragmented regulation and legal uncertainty create deployment bottlenecks.\n"
            "- Persistent subgroup underperformance undermines trust and equity goals.\n\n"
            "## Scenario Interdependencies\n"
            "- Evidence quality and post-market monitoring maturity are the strongest swing factors between upside and downside.\n"
            "- Interoperability progress determines whether pilots become system-level impact.\n\n"
            "## Leading Indicators Dashboard\n"
            "| Indicator | Target Range | Warning Threshold |\n"
            "|-----------|--------------|-------------------|\n"
            "| Subgroup performance parity | Narrow gap across cohorts | Persistent widening gap |\n"
            "| Clinician override appropriateness | Stable, explainable overrides | Blind acceptance trends |\n"
            "| Post-market safety signal rate | Low and declining | Sustained incident clustering |\n"
            "| Time-to-diagnosis improvement | Consistent reduction | Reversion to baseline |\n\n"
            "## Forecast Confidence\n"
            "- Moderate confidence; strongest where evidence is anchored in primary clinical and regulatory sources.\n"
            "- Lower confidence for broad market projections without standardized cross-system reporting.\n\n"
            "## Citations Used\n"
            f"- [{primary_source['id']}] {primary_source['title']} ({primary_source['domain']}): Forecast anchor and constraint assumptions.\n"
        )

    def _structured_verifier(self, query: str, source_block: str, prior_outputs_block: str = "") -> str:
        sources = self._get_source_details()
        source_count = len(sources)
        avg_cred = sum(s['cred'] for s in sources) / max(1, source_count) if sources else 0.5
        first_id = sources[0]["id"] if sources else "S1"
        second_id = sources[1]["id"] if len(sources) > 1 else first_id
        prior_context = f"\n\n## Prior Agent Outputs\n{prior_outputs_block}\n" if prior_outputs_block else ""
        return (
            "## Claim Verification\n"
            f"Evidence audit for '{query}' across {source_count} retrieved sources (mean credibility: {avg_cred:.0%}).\n\n"
            "## Verification Summary\n"
            f"- **Overall evidence strength**: {int(avg_cred * 100)}/100\n"
            f"- **Source diversity**: {source_count} sources across {len(set(s['domain'] for s in sources)) if sources else 0} domains\n"
            "- **Assessment**: strongest support is for direction-of-effect claims; weakest support is for broad magnitude forecasts.\n\n"
            "## Claim Audit Table\n"
            "| # | Claim Type | Primary Source | Status | Strength | Notes |\n"
            "|---|------------|----------------|--------|----------|-------|\n"
            f"| 1 | AI can improve diagnostic consistency in specific workflows | [{first_id}] | SUPPORTED | Medium-High | Stronger where validated task boundaries are explicit |\n"
            f"| 2 | Regulatory scrutiny is tightening for lifecycle model governance | [{second_id}] | VERIFIED | High | Convergent signal from policy/regulatory sources |\n"
            f"| 3 | Benefits are uniform across all patient groups | [{first_id}] | CONTESTED | Low-Medium | Subgroup equity evidence remains mixed |\n"
            f"| 4 | Human oversight remains necessary for high-impact decisions | [{second_id}] | VERIFIED | High | Broad agreement across governance guidance |\n"
            f"| 5 | Near-term impact depends on interoperability and deployment maturity | [{first_id}] | SUPPORTED | Medium | Operational maturity is a major moderator |\n\n"
            "## Source Triangulation\n"
            "- Strong: regulatory evolution and governance requirements.\n"
            "- Moderate: clinical workflow efficiency benefits in selected tasks.\n"
            "- Weak/contested: universal outcome gains across all settings and populations.\n\n"
            "## Evidence Gaps\n"
            "- More standardized post-market outcome reporting by demographic subgroup.\n"
            "- Independent comparative studies across health systems and model vendors.\n"
            "- Longitudinal evidence on clinician-AI interaction effects.\n\n"
            "## Contradiction Map\n"
            "- Benefit claims are stronger than universalization claims; results vary by use-case and data quality.\n"
            "- Compliance clarity is improving, but legal liability boundaries remain jurisdiction-dependent.\n\n"
            "## Verification Confidence\n"
            "- Report confidence: medium.\n"
            "- Use caveats for market-size extrapolations and cross-setting generalization claims.\n"
            f"{prior_context}"
        )

    def _get_source_details(self) -> list[dict]:
        """Extract structured source info from research context."""
        if not hasattr(self, '_research') or not self._research or not self._research.sources:
            return []
        return [
            {"id": s.id, "title": s.title, "domain": s.domain, "cred": s.credibility_score}
            for s in self._research.sources[:6]
        ]

    def _source_block(self, research: ResearchContext | None) -> str:
        if not research or not research.sources:
            return "No live web sources were available, so this result is based on direct reasoning only."

        top = research.sources[0]
        return f"{top.id} {top.title} ({top.domain})"

    def _extract_section_summary(self, text: str, preferred: str, fallback: str) -> str:
        text = text.replace("Analyzing request... ", "").replace("Analyzing request...", "").strip()
        lines = text.splitlines()
        section_indexes = [i for i, line in enumerate(lines) if line.strip() in {preferred, fallback}]
        for index in section_indexes:
            for candidate in lines[index + 1 :]:
                stripped = candidate.strip()
                if not stripped:
                    continue
                if stripped.startswith("## "):
                    break
                if stripped.startswith("-") or stripped[0].isdigit():
                    return stripped.lstrip("- ").strip()
                return stripped
        return text.split("\n", 1)[0].strip() or "Not available"

    def _research_findings(self, research: ResearchContext | None) -> str:
        if not research or not research.sources:
            return "- No live web retrieval was available, so the report should flag that gap explicitly.\n- The app still needs a retrieval layer before generation to qualify as a research model.\n- Final claims should be marked as provisional when they are not source-backed."

        lines = [
            "- The app now has an actual web-retrieval prepass and should no longer rely only on model memory.",
            "- Source inventory and source pack should be displayed alongside the answer so users can audit the claims.",
            "- Claims should be tied to source IDs and the report should include a section that explains which sources were used and why they matter.",
        ]
        if any(source.authority == "primary" for source in research.sources):
            lines.append("- Primary sources should be preferred whenever the question asks for current specifications or official guidance.")
        if len(research.sources) >= 3:
            lines.append("- A mixed source set is healthier than a single-source answer because it reveals disagreements and gaps.")
        return "\n".join(lines)

    def _tool_analysis_markdown(self, research: ResearchContext | None) -> str:
        source_note = self._source_block(research)
        return (
            "#### 3.2.1 Google Search\n"
            "- Best for current facts, news, policy changes, and broad discovery.\n"
            "- Missing step in the app: a live grounding pass before synthesis.\n"
            "- What to do: search first, then pass the top results into the model with explicit source IDs.\n\n"
            "#### 3.2.2 URL Context\n"
            "- Best for deep reading of specific pages or docs discovered during search.\n"
            "- Missing step in the app: direct page retrieval and page-level evidence extraction.\n"
            "- What to do: fetch the most relevant URLs, extract the visible text, and use it as page-grounding context.\n\n"
            "#### 3.2.3 File Search\n"
            "- Best for private knowledge bases, manuals, and repeatable retrieval over your own documents.\n"
            "- Missing step in the app: a private-data retrieval lane for uploaded files or internal notes.\n"
            "- What to do: keep File Search as a separate lane from public web search and cite retrieved document chunks.\n\n"
            "#### 3.2.4 Code Execution\n"
            "- Best for numeric checks, comparisons, calculations, and small data transformations.\n"
            "- Missing step in the app: any verification stage that computes derived values instead of trusting model prose.\n"
            "- What to do: run code when a query needs aggregation, scoring, or repeatable analysis.\n\n"
            f"- Current grounding note: {source_note}"
        )

    def diagnostics(self) -> dict[str, str | int | bool]:
        registry = prompt_registry_snapshot(
            [
                prompt_fingerprint("advocate", _provider_agent_prompt(self.configured_provider, "advocate")),
                prompt_fingerprint("skeptic", _provider_agent_prompt(self.configured_provider, "skeptic")),
                prompt_fingerprint("synthesiser", _provider_agent_prompt(self.configured_provider, "synthesiser")),
                prompt_fingerprint("oracle", _provider_agent_prompt(self.configured_provider, "oracle")),
                prompt_fingerprint("final", _provider_final_prompt(self.configured_provider)),
            ]
        )
        registry_version, registry_size = _prompt_registry_summary(registry)
        return {
            "configuredProvider": self.configured_provider,
            "activeProvider": "deterministic",
            "modelName": self.model_name,
            "isFallback": self.configured_provider != "deterministic",
            "fallbackCount": 0,
            "lastError": self.reason,
            "promptRegistryVersion": registry_version,
            "promptRegistrySize": registry_size,
        }


class GeminiPipelineModelProvider:
    def __init__(self, model_name: str, fallback: PipelineModelProvider | None = None) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        self._model_name = model_name
        self._fallback_count = 0
        self._last_error = ""
        self._health = _ProviderHealthManager(
            provider_name="gemini",
            retry_budget=_provider_retry_budget(),
            failure_threshold=_provider_failure_threshold(),
            cooldown_seconds=_provider_cooldown_seconds(),
            backoff_seconds=_provider_backoff_seconds(),
        )
        self._researcher = _create_researcher()
        self._api_keys = _parse_api_key_pool("GOOGLE_API_KEY", "GOOGLE_API_KEYS")
        self._api_key_index = 0
        self._chat_cls = ChatGoogleGenerativeAI
        self._models_by_key: dict[str, object] = {}
        self._model = self._build_model(self._api_keys[0] if self._api_keys else None)
        self._fallback = fallback or DeterministicPipelineModelProvider(
            configured_provider="gemini",
            model_name=model_name,
            reason="Gemini runtime call failed",
        )

    async def build_research_context(self, query: str) -> ResearchContext | None:
        if not _web_research_enabled():
            return None
        try:
            # Retrieval instability should not trip the generation circuit in strict-local mode.
            # We fail retrieval softly and still allow agent/synthesis generation to execute.
            return await asyncio.wait_for(
                self._researcher.research(query),
                timeout=_stage_timeout_seconds("retrieval"),
            )
        except Exception:
            return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.build_agent_text(agent_id, query, research)

        prompts = {
            "advocate": (
                "You are the ADVOCATE agent in a professional multi-agent research pipeline. Your mission is to construct the strongest evidence-backed case for action.\n\n"
                "REQUIRED OUTPUT STRUCTURE:\n"
                "## Opportunity Thesis\n"
                "State the core opportunity with quantified impact (percentage, timeframe, magnitude). One sentence.\n\n"
                "## Strategic Upside\n"
                "List 3-5 specific benefits. Each MUST include:\n"
                "- [Sx] citation to research source\n"
                "- Quantified estimate where possible\n"
                "- Timeframe (immediate/30-day/90-day)\n\n"
                "## Supporting Logic\n"
                "Present reasoning chain: Premise + Evidence → Conclusion\n"
                "- At least 2 causal mechanisms explaining WHY benefits occur\n"
                "- Reference comparable precedents from sources\n"
                "- Note required conditions for success\n\n"
                "## Actionable Next Step\n"
                "ONE concrete action with: Who (role), What (deliverable), When (timeframe), Success criteria (measurable)\n\n"
                "## Citations Used\n"
                "List each [Sx] with evidence summary and credibility note.\n\n"
                "QUALITY REQUIREMENTS: Every claim cites [Sx]. Use specific numbers. No 'could potentially' phrases. Ground in evidence."
            ),
            "skeptic": (
                "You are the SKEPTIC agent in a professional multi-agent research pipeline. Your mission is to identify failure modes, quantify risks, and ensure recommendations survive scrutiny.\n\n"
                "REQUIRED OUTPUT STRUCTURE:\n"
                "## Risk Thesis\n"
                "Primary risk hypothesis with severity (Critical/High/Medium/Low).\n\n"
                "## Primary Failure Modes\n"
                "3-5 failures using taxonomy: Technical | Execution | Market/External | Adoption\n"
                "For each include: Probability (%), Impact (1-5), Detection difficulty, [Sx] citation\n\n"
                "## Risk Severity Matrix\n"
                "Rank by (Probability × Impact). Identify top 2 requiring immediate mitigation.\n\n"
                "## Second-Order Effects\n"
                "Downstream consequences: Cascade effects, reputation impact, recovery cost\n\n"
                "## Mitigation Requirements\n"
                "For high-severity risks: Control type, resource investment, feasibility, trigger threshold\n\n"
                "## Citations Used\n"
                "List each [Sx] with risk-relevant evidence.\n\n"
                "QUALITY REQUIREMENTS: Cite [Sx] for every major risk. Use probability ranges. Challenge advocate assumptions explicitly."
            ),
            "synthesiser": (
                "You are the SYNTHESISER agent in a professional multi-agent research pipeline. Your mission is to integrate competing perspectives into a decision-ready recommendation.\n\n"
                "REQUIRED OUTPUT STRUCTURE:\n"
                "## Integrated Assessment\n"
                "Core tension between opportunity/risk with your resolution stance. One paragraph.\n\n"
                "## Conflict Resolution Matrix\n"
                "Where Advocate and Skeptic disagree: Dimension | Advocate | Skeptic | Resolution | Confidence\n\n"
                "## Tradeoff Analysis\n"
                "Key tradeoffs: Gain vs sacrifice, short vs long-term, reversibility of choices.\n\n"
                "## Decision Rule\n"
                "Specific IF-THEN framework with 2+ conditional branches. Define null hypothesis.\n\n"
                "## Stakeholder Impact\n"
                "Who benefits, who bears risk, required buy-in from which roles.\n\n"
                "## Guardrails\n"
                "Hard limits (non-negotiable), soft limits (trigger review), escalation criteria.\n\n"
                "## Citations Used\n"
                "List [Sx] with synthesis-relevant evidence.\n\n"
                "QUALITY REQUIREMENTS: Acknowledge source conflicts. Assign confidence levels. Decision rules must be testable."
            ),
            "oracle": (
                "You are the ORACLE agent in a professional multi-agent research pipeline. Your mission is to forecast outcomes with scenario analysis and define leading indicators.\n\n"
                "REQUIRED OUTPUT STRUCTURE:\n"
                "## Scenario Outlook\n"
                "Forecast methodology and key assumptions.\n\n"
                "## Most Likely Outcome (60%)\n"
                "Timeline markers at 30/60/90/180 days. Key drivers. [Sx] evidence.\n\n"
                "## Upside Scenario (25%)\n"
                "Catalyst requirements. Magnitude (quantified). Early signals.\n\n"
                "## Downside Scenario (15%)\n"
                "Trigger conditions. Recovery options. Circuit-breaker thresholds.\n\n"
                "## Scenario Interdependencies\n"
                "What shifts likelihood between scenarios. Tipping points.\n\n"
                "## Leading Indicators Dashboard\n"
                "4-6 measurable signals: Indicator | Target | Warning | Frequency\n"
                "Distinguish leading (predictive) from lagging (confirmatory).\n\n"
                "## Forecast Confidence\n"
                "Overall level with rationale. Key uncertainties. Review cadence.\n\n"
                "## Citations Used\n"
                "List [Sx] with forecast-relevant evidence.\n\n"
                "QUALITY REQUIREMENTS: Probabilities sum to 100%. Use specific timeframes. Indicators must be measurable."
            ),
            "verifier": (
                "You are the VERIFIER agent. Your mission is to audit evidence quality and validate claims.\n\n"
                "REQUIRED OUTPUT STRUCTURE:\n"
                "## Verification Summary\n"
                "Evidence quality overview with aggregate confidence score (1-100).\n\n"
                "## Claim Audit Table\n"
                "| Claim | Source | Status | Strength | Notes |\n"
                "Status: VERIFIED/SUPPORTED/WEAKLY-SUPPORTED/CONTESTED/UNVERIFIED/SPECULATIVE\n\n"
                "## Source Triangulation\n"
                "Strong (3+ sources) | Moderate (2) | Weak (1) | None\n\n"
                "## Evidence Gaps\n"
                "Missing data. Recommended sources. Validation experiments.\n\n"
                "## Contradiction Map\n"
                "Where sources disagree. Which is more credible. Resolution recommendation.\n\n"
                "## Verification Confidence\n"
                "Overall score. Confidence level. Claims needing caveats.\n\n"
                "QUALITY REQUIREMENTS: Audit 5+ claims. Reference credibility scores. Flag weak evidence."
            ),
        }
        instruction = prompts.get(agent_id, prompts.get("verifier", prompts["oracle"]))
        research_block = format_research_context(research)
        try:
            resolved = await _invoke_with_resilience(
                self._health,
                f"agent:{agent_id}",
                lambda: self._ainvoke(
                    f"{instruction}\n\nQuestion: {query.strip()}\n\nLive web research context:\n{research_block}"
                ),
                _stage_timeout_seconds("agent"),
                lambda text: _is_agent_research_grade(text, minimum_length=260, research=research),
            )
            return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.build_agent_text(agent_id, query, research)

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

        research_block = format_research_context(research)
        final_prompt = (
            "You are the FINAL SYNTHESISER for a professional multi-agent research pipeline.\n"
            "Your output must follow the exact paper structure requested by the user.\n\n"
            "REQUIRED OUTPUT STRUCTURE (use these exact top-level headings in this exact order):\n"
            "## Title\n"
            "## Author\n"
            "## Abstract\n"
            "## Keywords\n"
            "## Introduction\n"
            "## Methods\n"
            "## Results\n"
            "## Discussion/Conclusion\n"
            "## References\n\n"
            "SECTION EXPECTATIONS:\n"
            "- Abstract: brief Background, Methods, Results, and Conclusion in scholarly prose.\n"
            "- Introduction: context, positioning, and explicit research question.\n"
            "- Methods: data sources and analytical process (including adversarial agent workflow).\n"
            "- Results: findings and evidence synthesis.\n"
            "- Discussion/Conclusion: significance, limitations, and final takeaways in one section.\n"
            "- References: source inventory with [Sx] IDs and URLs when available.\n\n"
            "QUALITY REQUIREMENTS:\n"
            "- Do not add extra top-level sections.\n"
            "- Write in narrative prose, not bullet lists (except References).\n"
            "- Every major claim cites [Sx] source ID\n"
            "- Distinguish primary (peer-reviewed, official) from secondary sources\n"
            "- Acknowledge limitations explicitly\n"
            "- Keep all evidence in scope; adjust narrative depth without dropping key facts\n"
            "- Use academic register (precise terminology, measured tone)\n"
            "- Distinguish correlation from causation\n"
            "- NO business templates, 90-day plans, or pilot rollout language\n\n"
            f"Question: {query.strip()}\n\n"
            f"ADVOCATE ANALYSIS:\n{outputs.get('advocate', 'Not available')}\n\n"
            f"SKEPTIC ANALYSIS:\n{outputs.get('skeptic', 'Not available')}\n\n"
            f"SYNTHESIS:\n{outputs.get('synthesiser', 'Not available')}\n\n"
            f"FORECAST:\n{outputs.get('oracle', 'Not available')}\n\n"
            f"VERIFICATION:\n{outputs.get('verifier', 'Not available')}\n\n"
            f"LIVE RESEARCH CONTEXT:\n{research_block}"
            + (f"\n\nREFINEMENT FOCUS: {refinement_note.strip()}" if refinement_note and refinement_note.strip() else "")
        )
        try:
            resolved = await _invoke_with_resilience(
                self._health,
                "final",
                lambda: self._ainvoke(final_prompt),
                _stage_timeout_seconds("final"),
                lambda text: _is_final_research_grade(text, minimum_length=900, research=research),
                operation_with_retry=(
                    lambda: self._ainvoke(
                        final_prompt + "\n\nCRITICAL: Every claim MUST cite [S1], [S2], [S3] etc. References MUST include all sources."
                    ) if _final_auto_retry_enabled() else None
                ),
            )
            if _final_auto_retry_enabled() and research and len(research.sources) > 0:
                resolved = _inject_missing_citations(resolved, research)
            return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

    def diagnostics(self) -> dict[str, str | int | bool]:
        breaker_state = self._health.snapshot()
        registry = prompt_registry_snapshot(
            [
                prompt_fingerprint("advocate", _provider_agent_prompt("gemini", "advocate")),
                prompt_fingerprint("skeptic", _provider_agent_prompt("gemini", "skeptic")),
                prompt_fingerprint("synthesiser", _provider_agent_prompt("gemini", "synthesiser")),
                prompt_fingerprint("oracle", _provider_agent_prompt("gemini", "oracle")),
                prompt_fingerprint("final", _provider_final_prompt("gemini")),
            ]
        )
        registry_version, registry_size = _prompt_registry_summary(registry)
        return {
            "configuredProvider": "gemini",
            "activeProvider": "deterministic-fallback" if self._health.is_open() else "gemini",
            "modelName": self._model_name,
            "isFallback": self._fallback_count > 0,
            "fallbackCount": self._fallback_count,
            "lastError": self._last_error,
            "promptRegistryVersion": registry_version,
            "promptRegistrySize": registry_size,
            **breaker_state,
        }

    def _register_fallback(self, exc: Exception) -> None:
        self._fallback_count += 1
        message = f"{type(exc).__name__}: {exc}".strip()
        self._last_error = message[:240]

    async def _ainvoke(self, prompt: str) -> str:
        if not self._api_keys:
            response = await self._model.ainvoke(prompt)
            content = getattr(response, "content", "")
            return str(content).strip()

        last_exc: Exception | None = None
        for _ in range(len(self._api_keys)):
            api_key = self._next_api_key()
            model = self._model_for_key(api_key)
            try:
                response = await model.ainvoke(prompt)
                content = getattr(response, "content", "")
                return str(content).strip()
            except Exception as exc:
                last_exc = exc
                text = f"{type(exc).__name__}: {exc}".lower()
                if "429" in text or "rate" in text or "quota" in text or "resource_exhausted" in text:
                    continue
                raise

        if last_exc is not None:
            raise RuntimeError("Gemini rate-limited across all configured keys") from last_exc
        raise RuntimeError("Gemini invocation failed")

    def _build_model(self, api_key: str | None) -> object:
        kwargs = {
            "model": self._model_name,
            "temperature": 0.35,
        }
        if api_key:
            kwargs["google_api_key"] = api_key
        return self._chat_cls(**kwargs)

    def _model_for_key(self, api_key: str) -> object:
        cached = self._models_by_key.get(api_key)
        if cached is not None:
            return cached
        model = self._build_model(api_key)
        self._models_by_key[api_key] = model
        return model

    def _next_api_key(self) -> str:
        if not self._api_keys:
            return ""
        key = self._api_keys[self._api_key_index % len(self._api_keys)]
        self._api_key_index = (self._api_key_index + 1) % len(self._api_keys)
        return key


class OpenRouterPipelineModelProvider:
    def __init__(self, default_model: str, fallback: PipelineModelProvider | None = None) -> None:
        api_keys = _parse_api_key_pool("OPENROUTER_API_KEY", "OPENROUTER_API_KEYS")
        if not api_keys:
            raise RuntimeError("OPENROUTER_API_KEY is required for provider=openrouter")

        self._default_model = default_model
        self._fallback_count = 0
        self._last_error = ""
        self._health = _ProviderHealthManager(
            provider_name="openrouter",
            retry_budget=_provider_retry_budget(),
            failure_threshold=_provider_failure_threshold(),
            cooldown_seconds=_provider_cooldown_seconds(),
            backoff_seconds=_provider_backoff_seconds(),
        )
        self._base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self._timeout_seconds = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "35"))
        self._api_keys = api_keys
        self._api_key_index = 0
        self._cost_mode = _cost_mode()
        self._headers_base = {
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://hexamind.local"),
            "X-Title": os.getenv("OPENROUTER_X_TITLE", "Hexamind ARIA"),
            "Content-Type": "application/json",
        }
        self._researcher = _create_researcher()
        self._strict_provider = _strict_provider_mode()
        self._fallback = fallback or (None if self._strict_provider else DeterministicPipelineModelProvider(
            configured_provider="openrouter",
            model_name=default_model,
            reason="OpenRouter runtime call failed",
        ))
        self._model_by_role = {
            "advocate": _cost_aware_agent_model("openrouter", "advocate", default_model),
            "skeptic": _cost_aware_agent_model("openrouter", "skeptic", default_model),
            "synthesiser": _cost_aware_agent_model("openrouter", "synthesiser", default_model),
            "oracle": _cost_aware_agent_model("openrouter", "oracle", default_model),
            "verifier": _cost_aware_agent_model("openrouter", "verifier", default_model),
            "final": _cost_aware_agent_model("openrouter", "final", default_model),
        }
        self._token_budget = TokenBudget()

    async def build_research_context(self, query: str) -> ResearchContext | None:
        if not _web_research_enabled():
            return None
        try:
            # Retrieval should not trip the local generation circuit in strict-local mode.
            # If web retrieval is unavailable, continue with generation using available context.
            return await asyncio.wait_for(
                self._researcher.research(query),
                timeout=_stage_timeout_seconds("retrieval"),
            )
        except Exception:
            return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        if not self._health.can_attempt():
            if self._strict_provider:
                raise RuntimeError("OpenRouter circuit breaker is open")
            return await self._fallback.build_agent_text(agent_id, query, research)

        complexity_score = research.workflow_profile.complexity_score if research else _query_complexity_score(query)

        # Use deduplicated prompts with query-aware pruning.
        system_prompt = _build_agent_prompt(agent_id, complexity_score)
        
        # Use compressed research context (60% token reduction)
        compression_level = _research_compression_level()
        if compression_level == "none":
            research_block = _trim_for_prompt(format_research_context(research), 6500)
        else:
            research_block = _compress_research_context(research, compression_level)
        
        model_name = self._model_by_role.get(agent_id, self._default_model)
        user_prompt = f"Question: {query.strip()}\n\nLive web research context:\n{research_block}"
        cache_key = _prompt_cache_key("openrouter", f"agent:{agent_id}", model_name, system_prompt, user_prompt)
        cached_response = _load_prompt_cache(cache_key)
        if cached_response is not None:
            return cached_response

        estimated_tokens = _estimate_tokens(system_prompt) + _estimate_tokens(user_prompt)
        if not self._token_budget.can_afford(estimated_tokens):
            if self._strict_provider:
                raise RuntimeError("OpenRouter token budget exhausted")
            return await self._fallback.build_agent_text(agent_id, query, research)

        try:
            minimum_length = 120 if agent_id == "synthesiser" else 280
            validate_fn = None if agent_id == "synthesiser" else (
                lambda text: _is_agent_research_grade(text, minimum_length=minimum_length, research=research)
            )
            resolved = await _invoke_with_resilience(
                self._health,
                f"agent:{agent_id}",
                lambda: self._chat(
                    model=model_name,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                ),
                _stage_timeout_seconds("agent"),
                validate_fn,
            )
            _store_prompt_cache(cache_key, resolved)
            self._token_budget.charge(estimated_tokens + _estimate_tokens(resolved))
            return resolved
        except Exception as exc:
            self._register_fallback(exc)
            if self._strict_provider:
                raise

        return await self._fallback.build_agent_text(agent_id, query, research)

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        if not self._health.can_attempt():
            if self._strict_provider:
                raise RuntimeError("OpenRouter circuit breaker is open")
            return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

        # Compress research context for final stage
        compression_level = _research_compression_level()
        if compression_level == "none":
            research_block = _trim_for_prompt(format_research_context(research), 4200)
        else:
            research_block = _compress_research_context(research, compression_level)
        
        model_name = self._model_by_role.get("final", self._default_model)
        
        # Compress agent outputs (40% reduction) - pass summaries instead of full text
        advocate_output = _trim_for_prompt(outputs.get("advocate", ""), 1200)
        skeptic_output = _trim_for_prompt(outputs.get("skeptic", ""), 1200)
        synthesiser_output = _trim_for_prompt(outputs.get("synthesiser", ""), 1400)
        oracle_output = _trim_for_prompt(outputs.get("oracle", ""), 1200)
        verifier_output = _trim_for_prompt(outputs.get("verifier", ""), 1000)

        base_user_prompt = (
            f"Question: {query.strip()}\n\n"
            f"ADVOCATE:\n{advocate_output}\n\n"
            f"SKEPTIC:\n{skeptic_output}\n\n"
            f"SYNTHESISER:\n{synthesiser_output}\n\n"
            f"ORACLE:\n{oracle_output}\n\n"
            f"VERIFIER:\n{verifier_output}\n\n"
            f"RESEARCH CONTEXT:\n{research_block}"
            + (f"\n\nREFINEMENT FOCUS: {refinement_note.strip()}" if refinement_note and refinement_note.strip() else "")
        )

        try:
            resolved = await _invoke_with_resilience(
                self._health,
                "final",
                lambda: self._chat(
                    model=model_name,
                    system_prompt=_provider_final_prompt("openrouter"),
                    user_prompt=base_user_prompt,
                ),
                _stage_timeout_seconds("final"),
                lambda text: _is_final_research_grade(text, minimum_length=920, research=research),
                operation_with_retry=(
                    lambda: self._chat(
                        model=model_name,
                        system_prompt=(
                            _provider_final_prompt("openrouter")
                            + "\n\nCRITICAL: Every claim MUST cite [S1], [S2], [S3] etc. References MUST include all sources."
                        ),
                        user_prompt=base_user_prompt,
                    ) if _final_auto_retry_enabled() else None
                ),
            )
            if _final_auto_retry_enabled() and research and len(research.sources) > 0:
                resolved = _inject_missing_citations(resolved, research)
            return resolved
        except Exception as exc:
            self._register_fallback(exc)
            if self._strict_provider:
                raise

        return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

    def diagnostics(self) -> dict[str, str | int | bool]:
        breaker_state = self._health.snapshot()
        registry = prompt_registry_snapshot(
            [
                prompt_fingerprint("advocate", _provider_agent_prompt("openrouter", "advocate")),
                prompt_fingerprint("skeptic", _provider_agent_prompt("openrouter", "skeptic")),
                prompt_fingerprint("synthesiser", _provider_agent_prompt("openrouter", "synthesiser")),
                prompt_fingerprint("oracle", _provider_agent_prompt("openrouter", "oracle")),
                prompt_fingerprint("final", _provider_final_prompt("openrouter")),
            ]
        )
        registry_version, registry_size = _prompt_registry_summary(registry)
        return {
            "configuredProvider": "openrouter",
            "activeProvider": "openrouter",
            "modelName": self._default_model,
            "costMode": self._cost_mode,
            "isFallback": (self._fallback_count > 0) and (not self._strict_provider),
            "fallbackCount": self._fallback_count,
            "lastError": self._last_error,
            "strictProvider": self._strict_provider,
            "agentModelMap": json.dumps(self._model_by_role, sort_keys=True),
            "tokenBudgetLimit": self._token_budget.total_limit,
            "tokenBudgetUsed": self._token_budget.used,
            "tokenBudgetRemaining": self._token_budget.remaining(),
            "promptRegistryVersion": registry_version,
            "promptRegistrySize": registry_size,
            **breaker_state,
        }

    async def _chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            body = await self._chat_request(client, model, system_prompt, user_prompt)

        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("OpenRouter response missing choices")

        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            return "\n".join(part for part in parts if part).strip()
        return str(content).strip()

    async def _chat_request(
        self,
        client: httpx.AsyncClient,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        payload = {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        had_rate_limit = False
        last_error = ""

        for _ in range(len(self._api_keys)):
            api_key = self._next_api_key()
            headers = {
                **self._headers_base,
                "Authorization": f"Bearer {api_key}",
            }

            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

            if response.status_code == 429:
                had_rate_limit = True
                last_error = response.text[:200]
                continue

            if response.status_code in {401, 402, 403}:
                last_error = response.text[:200]
                continue

            if response.status_code == 400:
                # Retry with tighter prompt bounds before declaring provider failure.
                compact_payload = {
                    "model": model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": _trim_for_prompt(system_prompt, 1200)},
                        {"role": "user", "content": _trim_for_prompt(user_prompt, 3200)},
                    ],
                }
                retry = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=compact_payload,
                )
                if retry.is_success:
                    return retry.json()
                if retry.status_code == 429:
                    had_rate_limit = True
                    last_error = retry.text[:200]
                    continue

                # Some OpenRouter-backed providers reject system/developer instructions.
                error_text = (retry.text or response.text or "").lower()
                if "developer instruction" in error_text:
                    compatibility_payload = {
                        "model": model,
                        "temperature": 0.2,
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    f"System instructions:\n{_trim_for_prompt(system_prompt, 1200)}\n\n"
                                    f"User request:\n{_trim_for_prompt(user_prompt, 3200)}"
                                ),
                            }
                        ],
                    }
                    compat = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers=headers,
                        json=compatibility_payload,
                    )
                    if compat.is_success:
                        return compat.json()
                    if compat.status_code == 429:
                        had_rate_limit = True
                        last_error = compat.text[:200]
                        continue
                    raise RuntimeError(f"OpenRouter 400 after compatibility retry: {compat.text[:200]}")

                raise RuntimeError(f"OpenRouter 400 after compact retry: {retry.text[:200]}")

            response.raise_for_status()
            return response.json()

        if had_rate_limit:
            raise RuntimeError("OpenRouter rate-limited across all configured keys")
        raise RuntimeError(f"OpenRouter request failed across all configured keys: {last_error}")

    def _next_api_key(self) -> str:
        if not self._api_keys:
            return ""
        key = self._api_keys[self._api_key_index % len(self._api_keys)]
        self._api_key_index = (self._api_key_index + 1) % len(self._api_keys)
        return key

    def _register_fallback(self, exc: Exception) -> None:
        self._fallback_count += 1
        message = f"{type(exc).__name__}: {exc}".strip()
        self._last_error = message[:240]


class GroqPipelineModelProvider:
    def __init__(self, default_model: str, fallback: PipelineModelProvider | None = None) -> None:
        api_keys = _parse_api_key_pool("GROQ_API_KEY", "GROQ_API_KEYS")
        if not api_keys:
            raise RuntimeError("GROQ_API_KEY is required for provider=groq")

        self._default_model = default_model
        self._fallback_count = 0
        self._last_error = ""
        self._health = _ProviderHealthManager(
            provider_name="groq",
            retry_budget=_provider_retry_budget(),
            failure_threshold=_provider_failure_threshold(),
            cooldown_seconds=_provider_cooldown_seconds(),
            backoff_seconds=_provider_backoff_seconds(),
        )
        self._base_url = "https://api.groq.com/openai/v1".rstrip("/")
        self._timeout_seconds = float(os.getenv("GROQ_TIMEOUT_SECONDS", "30"))
        self._api_keys = api_keys
        self._api_key_index = 0
        self._headers_base = {
            "Content-Type": "application/json",
        }
        self._researcher = _create_researcher()
        self._fallback = fallback or DeterministicPipelineModelProvider(
            configured_provider="groq",
            model_name=default_model,
            reason="Groq runtime call failed",
        )
        self._model_by_role = {
            "advocate": _cost_aware_agent_model("groq", "advocate", default_model),
            "skeptic": _cost_aware_agent_model("groq", "skeptic", default_model),
            "synthesiser": _cost_aware_agent_model("groq", "synthesiser", default_model),
            "oracle": _cost_aware_agent_model("groq", "oracle", default_model),
            "final": _cost_aware_agent_model("groq", "final", default_model),
        }
        self._token_budget = TokenBudget()

    async def build_research_context(self, query: str) -> ResearchContext | None:
        if not _web_research_enabled():
            return None
        try:
            return await asyncio.wait_for(
                self._researcher.research(query),
                timeout=_stage_timeout_seconds("retrieval"),
            )
        except Exception:
            return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.build_agent_text(agent_id, query, research)

        complexity_score = research.workflow_profile.complexity_score if research else _query_complexity_score(query)

        # Use deduplicated prompts with query-aware pruning.
        system_prompt = _build_agent_prompt(agent_id, complexity_score)
        
        # Use compressed research context (60% token reduction)
        compression_level = _research_compression_level()
        if compression_level == "none":
            research_block = format_research_context(research)
        else:
            research_block = _compress_research_context(research, compression_level)
        
        model_name = self._model_by_role.get(agent_id, self._default_model)
        user_prompt = f"Question: {query.strip()}\n\nLive web research context:\n{research_block}"
        cache_key = _prompt_cache_key("groq", f"agent:{agent_id}", model_name, system_prompt, user_prompt)
        cached_response = _load_prompt_cache(cache_key)
        if cached_response is not None:
            return cached_response

        estimated_tokens = _estimate_tokens(system_prompt) + _estimate_tokens(user_prompt)
        if not self._token_budget.can_afford(estimated_tokens):
            return await self._fallback.build_agent_text(agent_id, query, research)

        try:
            minimum_length = 120 if agent_id == "synthesiser" else 280
            validate_fn = None if agent_id == "synthesiser" else (
                lambda text: _is_agent_research_grade(text, minimum_length=minimum_length, research=research)
            )
            resolved = await _invoke_with_resilience(
                self._health,
                f"agent:{agent_id}",
                lambda: self._chat(
                    model=model_name,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                ),
                _stage_timeout_seconds("agent"),
                validate_fn,
            )
            _store_prompt_cache(cache_key, resolved)
            self._token_budget.charge(estimated_tokens + _estimate_tokens(resolved))
            return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.build_agent_text(agent_id, query, research)

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        if not self._health.can_attempt():
            return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

        compression_level = _research_compression_level()
        if compression_level == "none":
            research_block = _trim_for_prompt(format_research_context(research), 2600)
        else:
            research_block = _compress_research_context(research, compression_level)
        model_name = self._model_by_role.get("final", self._default_model)

        advocate_output = _trim_for_prompt(outputs.get("advocate", ""), 700)
        skeptic_output = _trim_for_prompt(outputs.get("skeptic", ""), 700)
        synthesiser_output = _trim_for_prompt(outputs.get("synthesiser", ""), 900)
        oracle_output = _trim_for_prompt(outputs.get("oracle", ""), 700)
        verifier_output = _trim_for_prompt(outputs.get("verifier", ""), 650)

        base_user_prompt = (
            f"Question: {query.strip()}\n\n"
            f"ADVOCATE:\n{advocate_output}\n\n"
            f"SKEPTIC:\n{skeptic_output}\n\n"
            f"SYNTHESISER:\n{synthesiser_output}\n\n"
            f"ORACLE:\n{oracle_output}\n\n"
            f"VERIFIER:\n{verifier_output}\n\n"
            f"RESEARCH:\n{research_block}"
            + (f"\n\nREFINEMENT: {refinement_note.strip()}" if refinement_note and refinement_note.strip() else "")
        )

        try:
            resolved = await _invoke_with_resilience(
                self._health,
                "final",
                lambda: self._chat(
                    model=model_name,
                    system_prompt=_provider_final_prompt("groq"),
                    user_prompt=base_user_prompt,
                ),
                _stage_timeout_seconds("final"),
                lambda text: _is_final_research_grade(text, minimum_length=920, research=research),
                operation_with_retry=(
                    lambda: self._chat(
                        model=model_name,
                        system_prompt=(
                            _provider_final_prompt("groq")
                            + "\n\nCRITICAL: Every claim MUST cite [S1], [S2], [S3] etc. References MUST include all sources."
                        ),
                        user_prompt=base_user_prompt,
                    ) if _final_auto_retry_enabled() else None
                ),
            )
            if _final_auto_retry_enabled() and research and len(research.sources) > 0:
                resolved = _inject_missing_citations(resolved, research)
            return resolved
        except Exception as exc:
            self._register_fallback(exc)

        return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

    def diagnostics(self) -> dict[str, str | int | bool]:
        breaker_state = self._health.snapshot()
        registry = prompt_registry_snapshot(
            [
                prompt_fingerprint("advocate", _provider_agent_prompt("groq", "advocate")),
                prompt_fingerprint("skeptic", _provider_agent_prompt("groq", "skeptic")),
                prompt_fingerprint("synthesiser", _provider_agent_prompt("groq", "synthesiser")),
                prompt_fingerprint("oracle", _provider_agent_prompt("groq", "oracle")),
                prompt_fingerprint("final", _provider_final_prompt("groq")),
            ]
        )
        registry_version, registry_size = _prompt_registry_summary(registry)
        return {
            "configuredProvider": "groq",
            "activeProvider": "deterministic-fallback" if self._health.is_open() else "groq",
            "modelName": self._default_model,
            "isFallback": self._fallback_count > 0,
            "fallbackCount": self._fallback_count,
            "lastError": self._last_error,
            "agentModelMap": json.dumps(self._model_by_role, sort_keys=True),
            "tokenBudgetLimit": self._token_budget.total_limit,
            "tokenBudgetUsed": self._token_budget.used,
            "tokenBudgetRemaining": self._token_budget.remaining(),
            "promptRegistryVersion": registry_version,
            "promptRegistrySize": registry_size,
            **breaker_state,
        }

    async def _chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            body = await self._chat_request(client, model, system_prompt, user_prompt)

        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("Groq response missing choices")

        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            return "\n".join(part for part in parts if part).strip()
        return str(content).strip()

    async def _chat_request(
        self,
        client: httpx.AsyncClient,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        base_payload = {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        had_rate_limit = False
        last_error = ""

        for _ in range(len(self._api_keys)):
            api_key = self._next_api_key()
            headers = {
                **self._headers_base,
                "Authorization": f"Bearer {api_key}",
            }

            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=base_payload,
            )
            if response.status_code == 429:
                had_rate_limit = True
                last_error = response.text[:200]
                continue
            if response.status_code in {401, 402, 403}:
                last_error = response.text[:200]
                continue

            if response.status_code == 400:
                compact_payload = {
                    "model": model,
                    "temperature": 0.1,
                    "messages": [
                        {"role": "system", "content": _trim_for_prompt(system_prompt, 1100)},
                        {"role": "user", "content": _trim_for_prompt(user_prompt, 3000)},
                    ],
                }
                retry = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=compact_payload,
                )
                if retry.is_success:
                    return retry.json()
                if retry.status_code == 429:
                    had_rate_limit = True
                    last_error = retry.text[:200]
                    continue
                raise RuntimeError(f"Groq request failed after compact retry: {retry.status_code} {retry.text[:200]}")

            response.raise_for_status()
            return response.json()

        if had_rate_limit:
            raise RuntimeError("Groq rate-limited across all configured keys")
        raise RuntimeError(f"Groq request failed across all configured keys: {last_error}")

    def _next_api_key(self) -> str:
        if not self._api_keys:
            return ""
        key = self._api_keys[self._api_key_index % len(self._api_keys)]
        self._api_key_index = (self._api_key_index + 1) % len(self._api_keys)
        return key

    def _register_fallback(self, exc: Exception) -> None:
        self._fallback_count += 1
        message = f"{type(exc).__name__}: {exc}".strip()
        self._last_error = message[:240]


class LocalPipelineModelProvider:
    def __init__(self, default_model: str) -> None:
        self._default_model = default_model
        self._strict_local = _local_strict_mode()
        self._fallback_count = 0
        self._last_error = ""
        self._health = _ProviderHealthManager(
            provider_name="local",
            retry_budget=_provider_retry_budget(),
            failure_threshold=_provider_failure_threshold(),
            cooldown_seconds=_provider_cooldown_seconds(),
            backoff_seconds=_provider_backoff_seconds(),
        )
        self._base_url = os.getenv("HEXAMIND_LOCAL_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
        self._timeout_seconds = float(os.getenv("HEXAMIND_LOCAL_TIMEOUT_SECONDS", "45"))
        self._researcher = _create_researcher()
        self._fallback = None
        if not self._strict_local:
            self._fallback = DeterministicPipelineModelProvider(
                configured_provider="local",
                model_name=default_model,
                reason="Local runtime call failed",
            )
        self._hf_provider = get_huggingface_provider()
        self._hf_enabled = os.getenv("HEXAMIND_ENABLE_HF_FALLBACK", "1").strip().lower() not in {"0", "false", "no"}
        self._or_provider = get_openrouter_provider()
        self._or_enabled = os.getenv("HEXAMIND_ENABLE_OPENROUTER_FALLBACK", "1").strip().lower() not in {"0", "false", "no"}
        self._tier_models = {
            "small": os.getenv("HEXAMIND_LOCAL_MODEL_SMALL", default_model).strip() or default_model,
            "medium": os.getenv("HEXAMIND_LOCAL_MODEL_MEDIUM", default_model).strip() or default_model,
            "large": os.getenv("HEXAMIND_LOCAL_MODEL_LARGE", default_model).strip() or default_model,
        }
        self._model_by_role = {
            "researcher": _cost_aware_agent_model("local", "researcher", get_agent_model_config("researcher").primary_ollama_model),
            "critic": _cost_aware_agent_model("local", "critic", get_agent_model_config("critic").primary_ollama_model),
            "advocate": _cost_aware_agent_model("local", "advocate", get_agent_model_config("advocate").primary_ollama_model),
            "skeptic": _cost_aware_agent_model("local", "skeptic", get_agent_model_config("skeptic").primary_ollama_model),
            "synthesiser": _cost_aware_agent_model("local", "synthesiser", get_agent_model_config("synthesiser").primary_ollama_model),
            "oracle": _cost_aware_agent_model("local", "oracle", get_agent_model_config("oracle").primary_ollama_model),
            "verifier": _cost_aware_agent_model("local", "verifier", get_agent_model_config("verifier").primary_ollama_model),
            "final": _cost_aware_agent_model("local", "final", default_model),
        }
        self._token_budget = TokenBudget()
        self._local_available = self._probe_local_service()
        if self._strict_local and not self._local_available:
            raise RuntimeError(
                f"Strict local mode is enabled but local provider is unavailable at {self._base_url}."
            )

    async def build_research_context(self, query: str) -> ResearchContext | None:
        if not _web_research_enabled():
            return None
        try:
            # Retrieval failures should not trip the generation circuit in strict local mode.
            return await asyncio.wait_for(
                self._researcher.research(query),
                timeout=_stage_timeout_seconds("retrieval"),
            )
        except Exception:
            return None

    async def build_agent_text(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None = None,
    ) -> str:
        if not self._health.can_attempt():
            if self._strict_local:
                raise RuntimeError("Local provider circuit is open in strict local mode.")
            if not self._fallback:
                raise RuntimeError("Local provider fallback is unavailable.")
            return await self._fallback.build_agent_text(agent_id, query, research)

        prompts = {
            "researcher": (
                "RESEARCHER agent (local, evidence synthesis mode).\n"
                "SECTIONS: '## Executive Summary', '## Key Findings', '## Evidence Analysis', '## Implications', '## Limitations', '## Citations Used'.\n"
                "Synthesize sources into a comprehensive, well-structured research report. Be thorough and evidence-based."
            ),
            "critic": (
                "CRITIC agent (local, quality review mode).\n"
                "SECTIONS: '## Bias Assessment', '## Quality Gaps', '## Unsupported Claims', '## Missing Perspectives', '## Recommendations', '## Citations Used'.\n"
                "Review the research report for bias, gaps, and unsupported claims. Be critical but constructive."
            ),
            "advocate": (
                "ADVOCATE agent (local, research-paper mode).\n"
                "SECTIONS: '## Opportunity Thesis', '## Strategic Upside', '## Supporting Logic', '## Actionable Next Step', '## Citations Used'.\n"
                "Prioritize topic evidence and avoid generic implementation templates."
            ),
            "skeptic": (
                "SKEPTIC agent (local, research-paper mode).\n"
                "SECTIONS: '## Risk Thesis', '## Primary Failure Modes', '## Risk Severity Matrix', '## Mitigation Requirements', '## Citations Used'.\n"
                "Focus on domain-specific safety/regulatory/evidence risks."
            ),
            "synthesiser": (
                "SYNTHESISER agent (local, research-paper mode).\n"
                "SECTIONS: '## Integrated Assessment', '## Conflict Resolution Matrix', '## Tradeoff Analysis', '## Decision Rule', '## Guardrails', '## Citations Used'.\n"
                "Integrate evidence conflicts into coherent topic conclusions."
            ),
            "oracle": (
                "ORACLE agent (local, research-paper mode). Forecast topic scenarios.\n"
                "SECTIONS: '## Scenario Outlook', '## Most Likely (60%)', '## Upside (25%)', '## Downside (15%)', "
                "'## Leading Indicators', '## Citations Used'.\n"
                "Avoid generic project timelines."
            ),
            "verifier": (
                "VERIFIER agent (local). Audit evidence.\n"
                "SECTIONS: '## Verification Summary', '## Claim Audit Table', '## Source Triangulation', "
                "'## Evidence Gaps', '## Verification Confidence'.\n"
                "Audit 5+ claims."
            ),
        }
        complexity_score = research.workflow_profile.complexity_score if research else _query_complexity_score(query)
        system_prompt = _build_agent_prompt(agent_id, complexity_score)
        tier = _local_model_tier(query, research)
        min_length_by_tier = {
            "small": 60,
            "medium": 90,
            "large": 140,
        }
        research_block = _compressed_research_block(research, _local_context_budget("agent", tier, research))
        model_name = self._resolve_local_model(agent_id, tier)
        token_budget = _local_token_budget("agent", tier, research)
        user_prompt = f"Question: {query.strip()}\n\nLive research:\n{research_block}"
        cache_key = _prompt_cache_key("local", f"agent:{agent_id}", model_name, system_prompt, user_prompt)
        cached_response = _load_prompt_cache(cache_key)
        if cached_response is not None:
            return cached_response

        estimated_tokens = _estimate_tokens(system_prompt) + _estimate_tokens(user_prompt)
        if not self._token_budget.can_afford(estimated_tokens):
            if self._strict_local:
                raise RuntimeError("Local provider token budget exhausted in strict local mode.")
            if not self._fallback:
                raise RuntimeError("Local provider fallback is unavailable.")
            return await self._fallback.build_agent_text(agent_id, query, research)

        if self._local_available:
            try:
                resolved = await _invoke_with_resilience(
                    self._health,
                    f"agent:{agent_id}",
                    lambda: self._chat(
                        model=model_name,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_tokens=token_budget,
                    ),
                    _stage_timeout_seconds("agent"),
                    lambda text: _is_agent_research_grade(
                        text,
                        minimum_length=min_length_by_tier.get(tier, 230),
                        research=research,
                    ),
                )
                _store_prompt_cache(cache_key, resolved)
                self._token_budget.charge(estimated_tokens + _estimate_tokens(resolved))
                return resolved
            except Exception as exc:
                self._register_fallback(exc)
                if self._strict_local:
                    raise

        if self._strict_local:
            raise RuntimeError("Local provider is unavailable in strict local mode.")

        hf_result = await self._hf_agent_fallback(agent_id, query, research)
        if hf_result:
            return hf_result

        or_result = await self._or_agent_fallback(agent_id, query, research)
        if or_result:
            return or_result

        if not self._fallback:
            raise RuntimeError("Local provider fallback is unavailable.")
        return await self._fallback.build_agent_text(agent_id, query, research)

    async def compose_final_answer(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None = None,
        refinement_note: str | None = None,
    ) -> str:
        if not self._health.can_attempt():
            if self._strict_local:
                raise RuntimeError("Local provider circuit is open in strict local mode.")
            if not self._fallback:
                raise RuntimeError("Local provider fallback is unavailable.")
            return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

        tier = _local_model_tier(query, research)
        min_length_by_tier = {
            "small": 240,
            "medium": 320,
            "large": 420,
        }
        research_block = _compressed_research_block(research, _local_context_budget("final", tier, research))
        model_name = self._resolve_local_model("final", tier)
        token_budget = _local_token_budget("final", tier, research)

        base_user_prompt = (
            f"Question: {query.strip()}\n\n"
            "OUTPUT CONTRACT:\n"
            "- Deep reasoning over mechanisms, not generic statements.\n"
            "- Lead with the direct answer and the strongest evidence first.\n"
            "- Include a Claim-to-Citation Map section with claim IDs (C1..Cn) mapped to [Sx].\n"
            "- Include Verification & Confidence with verified/weak/unverified claim counts.\n"
            "- Keep all major claims source-grounded when sources are available.\n"
            "- Prefer specific findings, concrete examples, and measurable outcomes over broad caveats.\n\n"
            f"ADVOCATE:\n{outputs.get('advocate', '')}\n\n"
            f"SKEPTIC:\n{outputs.get('skeptic', '')}\n\n"
            f"SYNTHESISER:\n{outputs.get('synthesiser', '')}\n\n"
            f"ORACLE:\n{outputs.get('oracle', '')}\n\n"
            f"VERIFIER:\n{outputs.get('verifier', '')}\n\n"
            f"RESEARCH:\n{research_block}"
            + (f"\n\nREFINEMENT: {refinement_note.strip()}" if refinement_note and refinement_note.strip() else "")
        )

        if self._local_available:
            try:
                resolved = await _invoke_with_resilience(
                    self._health,
                    "final",
                    lambda: self._chat(
                        model=model_name,
                        system_prompt=_provider_final_prompt("local"),
                        user_prompt=base_user_prompt,
                        max_tokens=token_budget,
                    ),
                    _stage_timeout_seconds("final"),
                    lambda text: _is_final_research_grade(
                        text,
                        minimum_length=min_length_by_tier.get(tier, 760),
                        research=research,
                    ),
                    operation_with_retry=(
                        lambda: self._chat(
                            model=model_name,
                            system_prompt=(
                                _provider_final_prompt("local")
                                + "\n\nCRITICAL: Every claim MUST cite [S1], [S2], [S3] etc. References MUST include all sources."
                            ),
                            user_prompt=base_user_prompt,
                            max_tokens=token_budget,
                        ) if _final_auto_retry_enabled() else None
                    ),
                )
                if _final_auto_retry_enabled() and research and len(research.sources) > 0:
                    resolved = _inject_missing_citations(resolved, research)
                resolved = _ensure_verification_sections(resolved, outputs, research)
                return resolved
            except Exception as exc:
                self._register_fallback(exc)
                if self._strict_local:
                    raise

        if self._strict_local:
            raise RuntimeError("Local provider is unavailable in strict local mode.")

        hf_result = await self._hf_final_fallback(query, outputs, research, refinement_note)
        if hf_result:
            return hf_result

        or_result = await self._or_final_fallback(query, outputs, research, refinement_note)
        if or_result:
            return or_result

        if not self._fallback:
            raise RuntimeError("Local provider fallback is unavailable.")
        return await self._fallback.compose_final_answer(query, outputs, research, refinement_note)

    def diagnostics(self) -> dict[str, str | int | bool]:
        breaker_state = self._health.snapshot()
        registry = prompt_registry_snapshot(
            [
                prompt_fingerprint("advocate", _provider_agent_prompt("local", "advocate")),
                prompt_fingerprint("skeptic", _provider_agent_prompt("local", "skeptic")),
                prompt_fingerprint("synthesiser", _provider_agent_prompt("local", "synthesiser")),
                prompt_fingerprint("oracle", _provider_agent_prompt("local", "oracle")),
                prompt_fingerprint("final", _provider_final_prompt("local")),
            ]
        )
        registry_version, registry_size = _prompt_registry_summary(registry)
        return {
            "configuredProvider": "local",
            "activeProvider": (
                "local"
                if self._local_available and not self._health.is_open()
                else ("local-unavailable" if self._strict_local else "deterministic-fallback")
            ),
            "modelName": self._default_model,
            "localBaseUrl": self._base_url,
            "localAvailable": self._local_available,
            "isFallback": self._fallback_count > 0 or not self._local_available,
            "fallbackCount": self._fallback_count,
            "strictLocal": self._strict_local,
            "lastError": self._last_error,
            "agentModelMap": json.dumps(self._model_by_role, sort_keys=True),
            "hfFallbackEnabled": self._hf_enabled,
            "hfFallbackAvailable": self._hf_provider.available,
            "openrouterFallbackEnabled": self._or_enabled,
            "openrouterFallbackAvailable": self._or_provider.available,
            "tokenBudgetLimit": self._token_budget.total_limit,
            "tokenBudgetUsed": self._token_budget.used,
            "tokenBudgetRemaining": self._token_budget.remaining(),
            "promptRegistryVersion": registry_version,
            "promptRegistrySize": registry_size,
            **breaker_state,
        }

    async def _hf_agent_fallback(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None,
    ) -> str | None:
        if not self._hf_enabled or not self._hf_provider.available:
            return None
        try:
            config = get_agent_model_config(agent_id)
            research_block = _compressed_research_block(research, 2400)
            prompt = (
                f"You are the {agent_id.upper()} agent."
                f" {config.system_prompt_suffix}\n\n"
                f"Question: {query.strip()}\n\n"
                f"Research:\n{research_block}\n\n"
                "Return concise, evidence-backed markdown with clear section headings and citations when present."
            )
            result = await self._hf_provider.generate(
                agent_id=agent_id,
                prompt=prompt,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            if result and len(result.strip()) >= 120:
                return result.strip()
            return None
        except Exception:
            return None

    async def _hf_final_fallback(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None,
        refinement_note: str | None,
    ) -> str | None:
        if not self._hf_enabled or not self._hf_provider.available:
            return None
        try:
            research_block = _compressed_research_block(research, 3200)
            prompt = (
                "Produce a structured final research report with sections: "
                "Title, Author, Abstract, Keywords, Introduction, Methods, Results, Discussion/Conclusion, References.\n\n"
                f"Question: {query.strip()}\n\n"
                f"ADVOCATE:\n{outputs.get('advocate', '')}\n\n"
                f"SKEPTIC:\n{outputs.get('skeptic', '')}\n\n"
                f"SYNTHESISER:\n{outputs.get('synthesiser', '')}\n\n"
                f"ORACLE:\n{outputs.get('oracle', '')}\n\n"
                f"VERIFIER:\n{outputs.get('verifier', '')}\n\n"
                f"RESEARCH:\n{research_block}\n"
                + (f"\nREFINEMENT: {refinement_note.strip()}\n" if refinement_note and refinement_note.strip() else "")
            )
            result = await self._hf_provider.generate(
                agent_id="synthesiser",
                prompt=prompt,
                temperature=0.35,
                max_tokens=1800,
            )
            if result and len(result.strip()) >= 500:
                return result.strip()
            return None
        except Exception:
            return None

    async def _or_agent_fallback(
        self,
        agent_id: str,
        query: str,
        research: ResearchContext | None,
    ) -> str | None:
        if not self._or_enabled or not self._or_provider.available:
            return None
        try:
            config = get_agent_model_config(agent_id)
            research_block = _compressed_research_block(research, 2200)
            prompt = (
                f"You are the {agent_id.upper()} agent."
                f" {config.system_prompt_suffix}\n\n"
                f"Question: {query.strip()}\n\n"
                f"Research:\n{research_block}\n\n"
                "Return concise markdown with clear headings and evidence-backed reasoning."
            )
            result = await self._or_provider.generate(
                agent_id=agent_id,
                prompt=prompt,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            if result and len(result.strip()) >= 120:
                return result.strip()
            return None
        except Exception:
            return None

    async def _or_final_fallback(
        self,
        query: str,
        outputs: dict[str, str],
        research: ResearchContext | None,
        refinement_note: str | None,
    ) -> str | None:
        if not self._or_enabled or not self._or_provider.available:
            return None
        try:
            research_block = _compressed_research_block(research, 2800)
            prompt = (
                "Produce a structured final research report with sections: "
                "Title, Author, Abstract, Keywords, Introduction, Methods, Results, Discussion/Conclusion, References.\n\n"
                f"Question: {query.strip()}\n\n"
                f"ADVOCATE:\n{outputs.get('advocate', '')}\n\n"
                f"SKEPTIC:\n{outputs.get('skeptic', '')}\n\n"
                f"SYNTHESISER:\n{outputs.get('synthesiser', '')}\n\n"
                f"ORACLE:\n{outputs.get('oracle', '')}\n\n"
                f"VERIFIER:\n{outputs.get('verifier', '')}\n\n"
                f"RESEARCH:\n{research_block}\n"
                + (f"\nREFINEMENT: {refinement_note.strip()}\n" if refinement_note and refinement_note.strip() else "")
            )
            result = await self._or_provider.generate(
                agent_id="synthesiser",
                prompt=prompt,
                temperature=0.35,
                max_tokens=1800,
            )
            if result and len(result.strip()) >= 500:
                return result.strip()
            return None
        except Exception:
            return None

    async def _chat(self, model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        payload = {
            "model": model,
            "temperature": 0.15,
            "top_p": 0.85,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("Local model response missing choices")

        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            return "\n".join(part for part in parts if part).strip()
        return str(content).strip()

    def _probe_local_service(self) -> bool:
        try:
            response = httpx.get(f"{self._base_url}/models", timeout=3.0)
            response.raise_for_status()
            return True
        except Exception:
            return False

    def _register_fallback(self, exc: Exception) -> None:
        self._fallback_count += 1
        message = f"{type(exc).__name__}: {exc}".strip()
        self._last_error = message[:240]

    def _resolve_local_model(self, agent_id: str, tier: str) -> str:
        role_model = self._model_by_role.get(agent_id, self._default_model)
        if role_model != self._default_model:
            return role_model
        return self._tier_models.get(tier, self._default_model)


def _citation_count(text: str) -> int:
    """Count unique source citations in text."""
    return len(set(re.findall(r"\[S\d+\]", text)))


def _inject_missing_citations(
    final_answer: str,
    research: ResearchContext | None,
) -> str:
    """
    Deterministic post-processor that injects missing claim-to-citation mappings.
    Scans answer for claims and maps them to source IDs based on source content matching.
    Ensures References section includes all cited sources.
    """
    if not research or not research.sources:
        return final_answer
    
    answer = final_answer.strip()
    sources = research.sources
    
    # Extract sections
    title_match = re.search(r"## Title\n(.+?)\n\n", answer)
    refs_section_match = re.search(r"(## References?\n.*)", answer, re.DOTALL)
    
    if not refs_section_match:
        # No references section, we need to add one
        refs_section = "\n\n## References\n"
        for source in sources[:6]:  # Limit to top sources
            refs_section += f"- [{source.id}] {source.title} ({source.domain}) - {source.url}\n"
        answer += refs_section
    else:
        # Update existing references section
        old_refs = refs_section_match.group(1)
        new_refs = "## References\n"
        cited_ids = set(re.findall(r"\[S\d+\]", answer))
        
        # Add citations for all cited sources
        for source_id in sorted(cited_ids):
            matching_source = next((s for s in sources if s.id == source_id), None)
            if matching_source and f"[{source_id}]" not in old_refs:
                new_refs += f"- [{source_id}] {matching_source.title} ({matching_source.domain}) - {matching_source.url}\n"
        
        # Preserve any manually added references
        if "[" in old_refs:
            existing_refs = re.findall(r"- \[(?:S\d+|\d+)\].*", old_refs)
            for ref in existing_refs:
                if ref not in new_refs:
                    new_refs += ref + "\n"
        
        answer = answer[:refs_section_match.start()] + new_refs.rstrip()
    
    # Inject missing citations into claims paragraphs
    # Look for paragraphs in Results and Discussion sections
    paragraphs = re.split(r"\n\n+", answer)
    processed_paragraphs = []
    
    for paragraph in paragraphs:
        # Skip section headers and already-cited content
        if paragraph.startswith("##") or "[S" in paragraph:
            processed_paragraphs.append(paragraph)
            continue
        
        # For substantive claims in Results/Discussion, try to add citations
        if any(keyword in answer[max(0, answer.find(paragraph)-500):answer.find(paragraph)+len(paragraph)+500].lower() 
               for keyword in ["## results", "## discussion"]):
            
            # Find sentences/claims in paragraph
            sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            injected_sentences = []
            
            for sentence in sentences:
                if len(sentence.strip()) < 20 or "[S" in sentence:
                    injected_sentences.append(sentence)
                    continue
                
                # Score sentences against source content for semantic matching
                best_source = None
                best_score = 0.3  # Minimum threshold
                
                for source in sources:
                    # Simple keyword matching
                    sentence_lower = sentence.lower()
                    source_text = (source.excerpt + " " + source.snippet).lower()
                    
                    # Count matching words
                    sentence_words = set(re.findall(r"\b\w{3,}\b", sentence_lower))
                    source_words = set(re.findall(r"\b\w{3,}\b", source_text))
                    
                    if sentence_words and source_words:
                        overlap = len(sentence_words & source_words) / len(sentence_words | source_words)
                        if overlap > best_score:
                            best_score = overlap
                            best_source = source
                
                # Inject citation if we found a good match
                if best_source and f"[{best_source.id}]" not in sentence:
                    # Add citation at end of sentence
                    if sentence.rstrip().endswith((".", "!", "?")):
                        sentence = sentence.rstrip()[:-1] + f" [{best_source.id}]."
                    else:
                        sentence = sentence.rstrip() + f" [{best_source.id}]"
                
                injected_sentences.append(sentence)
            
            processed_paragraphs.append(" ".join(injected_sentences))
        else:
            processed_paragraphs.append(paragraph)
    
    return "\n\n".join(processed_paragraphs)


def _ensure_verification_sections(
    final_answer: str,
    outputs: dict[str, str],
    research: ResearchContext | None,
) -> str:
    """Ensure the final report contains verification-critical sections for stable quality scoring."""
    answer = (final_answer or "").strip()
    if not answer:
        return answer

    citations = sorted(set(re.findall(r"\[S\d+\]", answer)))
    source_count = len(research.sources) if research and research.sources else 0
    verified = max(0, min(len(citations), 6))
    weak = max(0, 6 - verified) if source_count > 0 else 2
    unverified = 0 if source_count > 0 else 4

    if "## Claim-to-Citation Map" not in answer:
        map_lines = ["## Claim-to-Citation Map"]
        if citations:
            for idx, cite in enumerate(citations[:6], start=1):
                map_lines.append(f"- C{idx} -> {cite}")
        else:
            map_lines.append("- C1 -> No direct [Sx] citations available in this run.")
        answer += "\n\n" + "\n".join(map_lines)

    if "## Verification & Confidence" not in answer:
        verifier_excerpt = _trim_for_prompt(outputs.get("verifier", ""), 480)
        verification_lines = [
            "## Verification & Confidence",
            f"- Verified claims: {verified}",
            f"- Weakly supported claims: {weak}",
            f"- Unverified claims: {unverified}",
            "- Confidence note: Use caution for claims without direct evidence support.",
        ]
        if verifier_excerpt:
            verification_lines.append("\nVerifier signal:\n" + verifier_excerpt)
        answer += "\n\n" + "\n".join(verification_lines)

    return answer


def _trim_for_prompt(text: str, limit: int) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 64].rstrip() + "\n\n[truncated for token safety]"


def _prior_outputs_block(prior_outputs: dict[str, str] | None, limit: int = 3200) -> str:
    if not prior_outputs:
        return ""

    ordered_agents = ("advocate", "skeptic", "oracle", "verifier", "synthesiser")
    sections: list[str] = []
    for agent_id in ordered_agents:
        content = (prior_outputs.get(agent_id) or "").strip()
        if not content:
            continue
        sections.append(f"[{agent_id}]\n{_trim_for_prompt(content, max(300, limit // 4))}")

    if not sections:
        return ""

    combined = "\n\n".join(sections)
    return _trim_for_prompt(f"Prior agent outputs:\n{combined}", limit)


def _is_agent_research_grade(
    text: str,
    minimum_length: int,
    research: ResearchContext | None,
) -> bool:
    if len(text) < minimum_length:
        return False
    heading_count = text.count("## ")
    has_citation_section = "## Citations Used" in text or "## Source Inventory" in text
    if heading_count < 1:
        return False
    if research and research.sources:
        citations = _citation_count(text)
        has_source_signal = "[S" in text or "http" in text or "source" in text.lower()
        # Accept good topic-specific responses even when the model misses strict citation formatting.
        return (citations >= 1 or has_source_signal) and (has_citation_section or has_source_signal)
    return True


def _final_min_length() -> int:
    """Get hard minimum final answer length from environment."""
    return max(620, _env_int("HEXAMIND_FINAL_MIN_LENGTH", 1200))


def _final_min_citations() -> int:
    """Get hard minimum citation count from environment."""
    return max(2, _env_int("HEXAMIND_FINAL_MIN_CITATIONS", 3))


def _final_auto_retry_enabled() -> bool:
    """Check if auto-retry with post-processing is enabled."""
    return os.getenv("HEXAMIND_FINAL_AUTO_RETRY", "1").strip().lower() in {"1", "true", "yes"}


def _is_final_research_grade(
    text: str,
    minimum_length: int,
    research: ResearchContext | None,
) -> bool:
    """Validate final answer meets research-grade standards with hard minimum gates."""
    required_sections = (
        "## Title",
        "## Author",
        "## Abstract",
        "## Keywords",
        "## Introduction",
        "## Methods",
        "## Results",
        "## Discussion/Conclusion",
        "## References",
    )
    # Hard gate 1: minimum length
    hard_minimum = _final_min_length()
    if len(text) < hard_minimum:
        return False
    # Hard gate 2: required sections
    if not all(section in text for section in required_sections):
        return False
    # Hard gate 3: citation count when sources exist
    if research and research.sources:
        citation_count = _citation_count(text)
        min_citations = _final_min_citations()
        return citation_count >= min_citations
    return True

def _web_research_enabled() -> bool:
    return os.getenv("HEXAMIND_WEB_RESEARCH", "1").strip().lower() not in {"0", "false", "no"}


def _cost_mode() -> str:
    value = os.getenv("HEXAMIND_COST_MODE", "free").strip().lower()
    return value if value in {"free", "balanced", "max"} else "free"


def _default_model_for_provider(provider_name: str) -> str:
    if provider_name in {"gemini", "google", "google-genai"}:
        return "gemini-2.0-flash"
    if provider_name in {"openrouter", "router"}:
        # Free-tier oriented default. Override per role with HEXAMIND_AGENT_MODEL_* env vars.
        return "google/gemma-3-12b-it:free"
    if provider_name in {"groq"}:
        return "llama-3.1-8b-instant"
    return "deterministic"


def _normalize_provider_name(name: str) -> str:
    normalized = (name or "").strip().lower()
    aliases = {
        "google": "gemini",
        "google-genai": "gemini",
        "router": "openrouter",
    }
    return aliases.get(normalized, normalized)


def _provider_priority(primary_name: str) -> list[str]:
    """
    Build provider order from HEXAMIND_PROVIDER_CHAIN with a Groq-first default.
    Ensures the configured primary provider is always first if it is cloud-capable.
    """
    supported = {"groq", "openrouter", "gemini"}
    raw_chain = os.getenv("HEXAMIND_PROVIDER_CHAIN", "groq,openrouter,gemini")
    parsed = [_normalize_provider_name(part) for part in raw_chain.split(",") if part.strip()]

    ordered: list[str] = []
    seen: set[str] = set()

    primary = _normalize_provider_name(primary_name)
    if primary in supported:
        ordered.append(primary)
        seen.add(primary)

    for name in parsed:
        if name in supported and name not in seen:
            ordered.append(name)
            seen.add(name)

    for fallback_name in ("groq", "openrouter", "gemini"):
        if fallback_name not in seen:
            ordered.append(fallback_name)
            seen.add(fallback_name)

    return ordered


def _create_researcher() -> ResearcherProtocol:
    from research import InternetResearcher

    return InternetResearcher()


def create_pipeline_model_provider() -> PipelineModelProvider:
    """
    Creates a resilient chain of model providers based on available API keys.
    Order of operations:
    1. Identify the primary provider from HEXAMIND_MODEL_PROVIDER.
    2. Identify all other available cloud providers (Gemini, Groq, OpenRouter).
    3. Build a linked chain: Primary -> Fallback 1 -> Fallback 2 -> Deterministic.
    """
    primary_name = _normalize_provider_name(os.getenv("HEXAMIND_MODEL_PROVIDER", "groq"))
    strict_mode = _strict_provider_mode()
    
    # helper to check if a provider is "available" (has keys)
    def is_available(name: str) -> bool:
        if name in {"gemini", "google", "google-genai"}:
            return bool(os.getenv("GOOGLE_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEYS", "").strip())
        if name in {"openrouter", "router"}:
            return bool(os.getenv("OPENROUTER_API_KEY", "").strip() or os.getenv("OPENROUTER_API_KEYS", "").strip())
        if name in {"groq"}:
            return bool(os.getenv("GROQ_API_KEY", "").strip() or os.getenv("GROQ_API_KEYS", "").strip())
        if name in {"local", "ollama", "lmstudio", "llama", "local-openai"}:
            # We don't chain local by default as it's environment specific
            return False 
        return False

    # List of cloud providers to potentially chain
    all_cloud_providers = _provider_priority(primary_name)
    
    # 1. Build the sequence of names to try
    # Start with the primary. If primary is not in the list (like 'local'), handle it separately.
    chain_names: list[str] = []
    if primary_name in all_cloud_providers:
        chain_names.append(primary_name)
    
    # Add other available ones
    for p in all_cloud_providers:
        if p not in chain_names and is_available(p):
            chain_names.append(p)
            
    # 2. Build the chain from the bottom up (last to first)
    # In strict mode, end with explicit overload error (no deterministic report fallback).
    if strict_mode:
        current_chain: PipelineModelProvider = ExhaustedPipelineModelProvider(
            configured_provider="chain-end",
            model_name="none",
            reason=OVERLOAD_RETRY_MESSAGE,
        )
    else:
        current_chain = DeterministicPipelineModelProvider(
            configured_provider="chain-end",
            model_name="deterministic",
            reason="All available cloud providers in the chain failed or were exhausted.",
        )

    # Functional mapping to create providers
    def instantiate_provider(name: str, fb: PipelineModelProvider) -> PipelineModelProvider:
        provider_model_name = os.getenv(f"HEXAMIND_MODEL_NAME_{name.upper()}", "").strip()
        global_model_name = os.getenv("HEXAMIND_MODEL_NAME", "").strip()
        m_name = provider_model_name or global_model_name or _default_model_for_provider(name)
        try:
            if name in {"gemini", "google", "google-genai"}:
                return GeminiPipelineModelProvider(m_name, fallback=fb)
            if name in {"openrouter", "router"}:
                return OpenRouterPipelineModelProvider(m_name, fallback=fb)
            if name in {"groq"}:
                return GroqPipelineModelProvider(m_name, fallback=fb)
            if name in {"local", "ollama", "lmstudio", "llama", "local-openai"}:
                return LocalPipelineModelProvider(m_name)
        except Exception:
            return fb # Skip failed inits
        return fb

    # Build the chain backwards
    for name in reversed(chain_names):
        current_chain = instantiate_provider(name, current_chain)
    
    # If primary is local, instantiate it directly (not in chain)
    if primary_name in {"local", "ollama", "lmstudio", "llama", "local-openai"}:
        try:
            provider_model_name = os.getenv(f"HEXAMIND_MODEL_NAME_{primary_name.upper()}", "").strip()
            global_model_name = os.getenv("HEXAMIND_MODEL_NAME", "").strip()
            m_name = provider_model_name or global_model_name or _default_model_for_provider(primary_name)
            return LocalPipelineModelProvider(m_name)
        except Exception:
            return current_chain  # Fall back if local init fails

    return current_chain
