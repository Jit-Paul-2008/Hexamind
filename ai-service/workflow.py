from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchWorkflowProfile:
    audience: str
    complexity_score: float
    depth_label: str
    max_terms: int
    max_sources: int
    max_hits_per_term: int
    fetch_concurrency: int
    min_relevance: float
    required_source_mix: int
    requires_primary_sources: bool
    requires_contradiction_check: bool
    token_mode: str
    context_source_cap: int
    evidence_excerpt_limit: int
    subquestions: tuple[str, ...]
    search_intents: tuple[str, ...]


@dataclass(frozen=True)
class TopicAnalysis:
    complexity_score: float
    abstraction_score: float
    domain_risk_score: float
    novelty_score: float
    audience_hint: str


def build_workflow_profile(query: str) -> ResearchWorkflowProfile:
    normalized = _clean_query(query)
    analysis = analyze_topic(normalized)
    audience = _select_audience(normalized, analysis)
    depth_label = _depth_label(analysis.complexity_score, audience)

    token_mode = _token_mode()
    max_terms, max_sources, max_hits_per_term, fetch_concurrency, min_relevance = _depth_settings(
        depth_label=depth_label,
        audience=audience,
        analysis=analysis,
        token_mode=token_mode,
    )
    context_source_cap, evidence_excerpt_limit = _token_context_settings(depth_label, token_mode)

    search_intents = _build_search_intents(normalized, analysis, audience)
    subquestions = _build_subquestions(normalized, analysis, audience)

    required_source_mix = 3 if audience in {"phd", "professor"} or analysis.complexity_score >= 0.72 else 2
    requires_primary_sources = analysis.domain_risk_score >= 0.4 or audience in {"phd", "professor"}
    requires_contradiction_check = analysis.complexity_score >= 0.38 or audience in {"phd", "professor"}

    return ResearchWorkflowProfile(
        audience=audience,
        complexity_score=round(analysis.complexity_score, 3),
        depth_label=depth_label,
        max_terms=max_terms,
        max_sources=max_sources,
        max_hits_per_term=max_hits_per_term,
        fetch_concurrency=fetch_concurrency,
        min_relevance=min_relevance,
        required_source_mix=required_source_mix,
        requires_primary_sources=requires_primary_sources,
        requires_contradiction_check=requires_contradiction_check,
        token_mode=token_mode,
        context_source_cap=context_source_cap,
        evidence_excerpt_limit=evidence_excerpt_limit,
        subquestions=tuple(subquestions),
        search_intents=tuple(search_intents),
    )


def analyze_topic(query: str) -> TopicAnalysis:
    words = re.findall(r"[a-zA-Z0-9]{3,}", query.lower())
    unique_words = {word for word in words}
    length_score = min(1.0, len(words) / 26.0)
    unique_score = min(1.0, len(unique_words) / 18.0)
    abstraction_score = _keyword_score(query, _ABSTRACTION_TERMS)
    domain_risk_score = _keyword_score(query, _HIGH_RISK_TERMS)
    novelty_score = _keyword_score(query, _NOVELTY_TERMS)

    complexity_score = (
        (length_score * 0.24)
        + (unique_score * 0.18)
        + (abstraction_score * 0.26)
        + (domain_risk_score * 0.16)
        + (novelty_score * 0.16)
    )

    if _has_comparison_pattern(query):
        complexity_score += 0.06
    if _has_theory_pattern(query):
        complexity_score += 0.08
    if _has_methodology_pattern(query):
        complexity_score += 0.05

    complexity_score = max(0.0, min(1.0, complexity_score))
    audience_hint = "professor" if complexity_score >= 0.78 else "phd" if complexity_score >= 0.58 else "grad"

    return TopicAnalysis(
        complexity_score=complexity_score,
        abstraction_score=abstraction_score,
        domain_risk_score=domain_risk_score,
        novelty_score=novelty_score,
        audience_hint=audience_hint,
    )


def _select_audience(query: str, analysis: TopicAnalysis) -> str:
    configured = os.getenv("HEXAMIND_RESEARCH_AUDIENCE", "auto").strip().lower()
    if configured in {"grad", "phd", "professor"}:
        return configured

    if _has_teaching_pattern(query) and analysis.complexity_score < 0.45:
        return "grad"
    if analysis.complexity_score >= 0.8 or analysis.domain_risk_score >= 0.5:
        return "professor"
    if analysis.complexity_score >= 0.58:
        return "phd"
    return "grad"


def _depth_label(complexity_score: float, audience: str) -> str:
    if audience == "professor" or complexity_score >= 0.82:
        return "maximal"
    if audience == "phd" or complexity_score >= 0.62:
        return "deep"
    if complexity_score >= 0.36:
        return "balanced"
    return "focused"


def _depth_settings(
    *,
    depth_label: str,
    audience: str,
    analysis: TopicAnalysis,
    token_mode: str,
) -> tuple[int, int, int, int, float]:
    if depth_label == "maximal":
        settings = [14, 12, 10, 6, 0.18]
    elif depth_label == "deep":
        settings = [12, 10, 8, 5, 0.22]
    elif depth_label == "balanced":
        settings = [10, 8, 7, 4, 0.24]
    else:
        settings = [8, 6, 5, 3, 0.28]

    if token_mode == "lean":
        settings[0] = max(6, settings[0] - 2)
        settings[1] = max(5, settings[1] - 2)
        settings[2] = max(4, settings[2] - 2)
        settings[4] = min(0.35, settings[4] + 0.04)
    elif token_mode == "max-quality":
        settings[0] += 2
        settings[1] += 2
        settings[2] += 1
        settings[4] = max(0.14, settings[4] - 0.03)

    return int(settings[0]), int(settings[1]), int(settings[2]), int(settings[3]), float(settings[4])


def _token_context_settings(depth_label: str, token_mode: str) -> tuple[int, int]:
    if depth_label == "maximal":
        source_cap = 10
        excerpt_limit = 900
    elif depth_label == "deep":
        source_cap = 8
        excerpt_limit = 760
    elif depth_label == "balanced":
        source_cap = 6
        excerpt_limit = 620
    else:
        source_cap = 5
        excerpt_limit = 520

    if token_mode == "lean":
        source_cap = max(4, source_cap - 2)
        excerpt_limit = max(380, excerpt_limit - 200)
    elif token_mode == "max-quality":
        source_cap += 1
        excerpt_limit += 120

    return source_cap, excerpt_limit


def _token_mode() -> str:
    value = os.getenv("HEXAMIND_TOKEN_MODE", "smart").strip().lower()
    if value in {"lean", "smart", "max-quality"}:
        return value
    return "smart"


def _build_search_intents(query: str, analysis: TopicAnalysis, audience: str) -> list[str]:
    base = _clean_query(query)
    terms = _top_query_terms(base, 6)
    core = " ".join(terms) if terms else base

    intents = [
        base,
        f"{base} latest evidence",
        f"{base} official documentation",
        f"{base} implementation guide",
        f"{base} limitations failures",
        f"{base} benchmark evaluation",
        f"{base} methodology",
        f"{base} peer reviewed",
        f"{base} systematic review",
        f"{core} case study",
        f"{core} scholarly article",
        f"{base} site:.gov",
        f"{base} site:.edu",
        f"{base} site:arxiv.org",
    ]
    if audience in {"phd", "professor"} or analysis.complexity_score >= 0.7:
        intents.extend(
            [
                f"{base} theoretical background",
                f"{base} comparative analysis",
                f"{base} recent review paper",
                f"{base} conflicting evidence",
                f"{base} formal definition",
                f"{base} replication study",
            ]
        )
    return _dedupe_preserve_order(intents)


def _build_subquestions(query: str, analysis: TopicAnalysis, audience: str) -> list[str]:
    base = _clean_query(query)
    subquestions = [
        f"What is the precise definition and scope of {base}?",
        f"What are the strongest current sources of evidence on {base}?",
        f"Where do experts disagree about {base}?",
        f"What are the main limitations, caveats, or failure modes for {base}?",
    ]
    if audience in {"phd", "professor"} or analysis.domain_risk_score >= 0.35:
        subquestions.extend(
            [
                f"Which primary sources or official references are most authoritative for {base}?",
                f"What assumptions would break the leading claims about {base}?",
                f"How does the evidence for {base} compare across methods, datasets, or contexts?",
            ]
        )
    if analysis.novelty_score >= 0.28:
        subquestions.append(f"What recent developments may have changed the evidence base for {base}?")
    return _dedupe_preserve_order(subquestions)


def _keyword_score(query: str, keywords: tuple[str, ...]) -> float:
    normalized = query.lower()
    matches = sum(1 for keyword in keywords if keyword in normalized)
    return min(1.0, matches / max(1, len(keywords) / 3.0))


def _has_comparison_pattern(query: str) -> bool:
    return bool(re.search(r"\b(vs|versus|compare|comparison|trade[- ]?off|between)\b", query.lower()))


def _has_theory_pattern(query: str) -> bool:
    return bool(re.search(r"\b(theory|mechanism|framework|model|proof|derivation|formal)\b", query.lower()))


def _has_methodology_pattern(query: str) -> bool:
    return bool(re.search(r"\b(method|methodology|protocol|experiment|evaluation|benchmark|dataset|study)\b", query.lower()))


def _has_teaching_pattern(query: str) -> bool:
    return bool(re.search(r"\b(explain|teach|learn|intro|introduction|guide|basics)\b", query.lower()))


_ABSTRACTION_TERMS: tuple[str, ...] = (
    "theory",
    "framework",
    "mechanism",
    "proof",
    "derivation",
    "formal",
    "axiom",
    "methodology",
    "epistemology",
    "causal",
    "comparative",
    "synthesis",
)

_HIGH_RISK_TERMS: tuple[str, ...] = (
    "medicine",
    "clinical",
    "security",
    "biomedical",
    "law",
    "regulation",
    "finance",
    "infrastructure",
    "safety",
    "policy",
    "education",
    "machine learning",
)

_NOVELTY_TERMS: tuple[str, ...] = (
    "latest",
    "recent",
    "state of the art",
    "2025",
    "2026",
    "emerging",
    "new",
    "current",
)


def _top_query_terms(query: str, max_terms: int) -> list[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "into",
        "about",
        "how",
        "what",
        "when",
        "where",
        "which",
        "are",
        "was",
        "were",
        "will",
        "would",
        "could",
        "should",
        "can",
        "your",
        "their",
        "our",
    }
    words = re.findall(r"[a-zA-Z0-9]{3,}", query.lower())
    filtered = [word for word in words if word not in stop]
    seen: set[str] = set()
    unique: list[str] = []
    for word in filtered:
        if word in seen:
            continue
        seen.add(word)
        unique.append(word)
        if len(unique) >= max_terms:
            break
    return unique


def _clean_query(query: str) -> str:
    return re.sub(r"\s+", " ", query).strip()


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        key = item.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output
