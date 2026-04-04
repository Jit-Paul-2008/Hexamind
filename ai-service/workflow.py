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
    search_passes: tuple[str, ...]
    # Beast workflow additions
    query_type: str  # factual, comparison, decision, forecast, technical, exploratory
    adversarial_queries: tuple[str, ...]  # anti-thesis and edge-case queries
    stakeholder_perspectives: tuple[str, ...]  # different viewpoints to consider
    requires_verification: bool  # whether claims need cross-checking
    report_mode: str  # brief, technical, decision, synthesis
    min_verification_rate: float  # minimum claim verification threshold
    contradiction_sensitivity: str  # low, medium, high


@dataclass(frozen=True)
class TopicAnalysis:
    complexity_score: float
    abstraction_score: float
    domain_risk_score: float
    novelty_score: float
    audience_hint: str
    query_type: str  # factual, comparison, decision, forecast, technical, exploratory
    has_controversy: bool  # topic likely has conflicting views
    requires_recency: bool  # topic has fast-moving developments


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
    search_passes = _build_search_passes(normalized, analysis, audience)
    
    # Beast workflow: adversarial query expansion
    adversarial_queries = _build_adversarial_queries(normalized, analysis)
    stakeholder_perspectives = _build_stakeholder_perspectives(normalized, analysis)
    report_mode = _select_report_mode(analysis, audience, depth_label)
    min_verification_rate = _select_min_verification_rate(analysis, audience)
    contradiction_sensitivity = _select_contradiction_sensitivity(analysis, audience)

    required_source_mix = 3 if audience in {"phd", "professor"} or analysis.complexity_score >= 0.72 else 2
    requires_primary_sources = analysis.domain_risk_score >= 0.4 or audience in {"phd", "professor"}
    requires_contradiction_check = analysis.complexity_score >= 0.38 or audience in {"phd", "professor"} or analysis.has_controversy
    requires_verification = analysis.domain_risk_score >= 0.3 or analysis.complexity_score >= 0.5 or audience in {"phd", "professor"}

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
        search_passes=tuple(search_passes),
        # Beast workflow additions
        query_type=analysis.query_type,
        adversarial_queries=tuple(adversarial_queries),
        stakeholder_perspectives=tuple(stakeholder_perspectives),
        requires_verification=requires_verification,
        report_mode=report_mode,
        min_verification_rate=min_verification_rate,
        contradiction_sensitivity=contradiction_sensitivity,
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
    
    # Beast workflow: classify query type
    query_type = _classify_query_type(query)
    has_controversy = _detect_controversy_potential(query)
    requires_recency = novelty_score >= 0.3 or any(token in query.lower() for token in ("latest", "current", "recent", "2025", "2026", "new"))

    return TopicAnalysis(
        complexity_score=complexity_score,
        abstraction_score=abstraction_score,
        domain_risk_score=domain_risk_score,
        novelty_score=novelty_score,
        audience_hint=audience_hint,
        query_type=query_type,
        has_controversy=has_controversy,
        requires_recency=requires_recency,
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
    value = os.getenv("HEXAMIND_TOKEN_MODE", "lean").strip().lower()
    if value in {"lean", "smart", "max-quality"}:
        return value
    return "lean"


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


def _build_search_passes(query: str, analysis: TopicAnalysis, audience: str) -> list[str]:
    normalized = query.lower()
    passes = ["official", "recent", "evidence", "failure_modes"]

    if _has_comparison_pattern(query) or analysis.complexity_score >= 0.45:
        passes.append("comparison")
    if _has_methodology_pattern(query) or audience in {"phd", "professor"}:
        passes.append("methodology")
    if any(token in normalized for token in ("benchmark", "evaluation", "measure", "validate")):
        passes.append("benchmark")
    if any(token in normalized for token in ("policy", "law", "regulation", "security", "clinical", "medicine")):
        passes.append("primary_sources")

    return _dedupe_preserve_order(passes)


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


# =============================================================================
# BEAST WORKFLOW: Query Intelligence and Adversarial Expansion
# =============================================================================

def _classify_query_type(query: str) -> str:
    """Classify query into type for specialized handling."""
    lowered = query.lower()
    
    # Comparison queries
    if _has_comparison_pattern(query):
        return "comparison"
    
    # Decision/recommendation queries
    if any(token in lowered for token in ("should", "recommend", "choose", "decide", "best", "prefer", "advise")):
        return "decision"
    
    # Forecasting queries
    if any(token in lowered for token in ("predict", "forecast", "future", "will", "expect", "outlook", "trend")):
        return "forecast"
    
    # Technical/implementation queries
    if any(token in lowered for token in ("implement", "build", "code", "configure", "setup", "deploy", "install", "architecture")):
        return "technical"
    
    # Exploratory/definitional queries
    if any(token in lowered for token in ("what is", "define", "explain", "how does", "why does", "overview")):
        return "exploratory"
    
    # Default to factual
    return "factual"


def _detect_controversy_potential(query: str) -> bool:
    """Detect if topic likely has conflicting views or evidence."""
    lowered = query.lower()
    controversy_indicators = (
        "debate", "controversial", "disagree", "dispute", "argument",
        "vs", "versus", "conflict", "competing", "alternative",
        "critics", "criticism", "skeptic", "doubt", "question",
        "politics", "policy", "ethics", "moral", "religion",
        "climate", "vaccine", "ai safety", "regulation",
    )
    return any(token in lowered for token in controversy_indicators)


def _build_adversarial_queries(query: str, analysis: TopicAnalysis) -> list[str]:
    """Generate adversarial queries to find counter-evidence and edge cases."""
    base = _clean_query(query)
    terms = _top_query_terms(base, 5)
    core = " ".join(terms) if terms else base
    
    adversarial = []
    
    # Anti-thesis queries (what evidence would disprove this?)
    adversarial.extend([
        f"{core} criticism limitations",
        f"{core} failures problems",
        f"{core} does not work when",
        f"{core} risks dangers",
        f"{core} counterargument rebuttal",
    ])
    
    # Edge case queries (under what conditions does this fail?)
    adversarial.extend([
        f"{core} edge cases exceptions",
        f"{core} when fails",
        f"{core} not recommended when",
        f"{core} prerequisites requirements",
    ])
    
    # Assumption-challenging queries
    adversarial.extend([
        f"{core} assumptions wrong",
        f"{core} alternative approaches",
        f"{core} conflicting evidence",
        f"{core} outdated obsolete",
    ])
    
    # High-complexity or high-risk topics get deeper adversarial coverage
    if analysis.complexity_score >= 0.6 or analysis.domain_risk_score >= 0.4:
        adversarial.extend([
            f"{core} systematic review negative",
            f"{core} meta-analysis limitations",
            f"{core} replication failure",
            f"{core} bias confounding",
        ])
    
    return _dedupe_preserve_order(adversarial)


def _build_stakeholder_perspectives(query: str, analysis: TopicAnalysis) -> list[str]:
    """Identify stakeholder perspectives to consider."""
    lowered = query.lower()
    perspectives = []
    
    # Policy/regulatory topics
    if any(token in lowered for token in ("policy", "regulation", "law", "government", "compliance")):
        perspectives.extend(["regulator", "practitioner", "affected_party", "advocate", "critic"])
    
    # Engineering/technical topics
    elif any(token in lowered for token in ("engineer", "build", "implement", "architecture", "system", "software")):
        perspectives.extend(["builder", "operator", "security_auditor", "end_user", "maintainer"])
    
    # Medical/health topics
    elif any(token in lowered for token in ("medical", "health", "clinical", "patient", "treatment", "therapy")):
        perspectives.extend(["clinician", "patient", "researcher", "regulator", "caregiver"])
    
    # Business/strategy topics
    elif any(token in lowered for token in ("business", "strategy", "market", "invest", "company", "startup")):
        perspectives.extend(["executive", "investor", "employee", "customer", "competitor"])
    
    # Education/learning topics
    elif any(token in lowered for token in ("learn", "education", "teach", "student", "course", "training")):
        perspectives.extend(["learner", "instructor", "employer", "institution", "researcher"])
    
    # Default perspectives
    else:
        perspectives.extend(["proponent", "skeptic", "practitioner", "theorist"])
    
    return perspectives[:5]


def _select_report_mode(analysis: TopicAnalysis, audience: str, depth_label: str) -> str:
    """Select appropriate report structure based on query characteristics."""
    
    # Quick brief for simple factual questions
    if analysis.complexity_score < 0.35 and analysis.query_type in ("factual", "exploratory"):
        return "brief"
    
    # Technical report for implementation questions
    if analysis.query_type == "technical":
        return "technical"
    
    # Decision memo for recommendation questions
    if analysis.query_type == "decision":
        return "decision"
    
    # Research synthesis for complex academic questions
    if audience in ("phd", "professor") or depth_label == "maximal":
        return "synthesis"
    
    # Comparison for vs-type questions
    if analysis.query_type == "comparison":
        return "comparison"
    
    # Forecast for prediction questions
    if analysis.query_type == "forecast":
        return "forecast"
    
    # Default to balanced report
    return "standard"


def _select_min_verification_rate(analysis: TopicAnalysis, audience: str) -> float:
    """Select minimum claim verification threshold."""
    # High-risk domains require higher verification
    if analysis.domain_risk_score >= 0.5:
        return 0.85
    
    # Academic audiences expect higher verification
    if audience in ("phd", "professor"):
        return 0.80
    
    # Complex topics need stronger verification
    if analysis.complexity_score >= 0.7:
        return 0.75
    
    # Controversial topics need verification
    if analysis.has_controversy:
        return 0.75
    
    # Default threshold
    return 0.65


def _select_contradiction_sensitivity(analysis: TopicAnalysis, audience: str) -> str:
    """Select contradiction detection sensitivity level."""
    # High sensitivity for controversial or high-risk topics
    if analysis.has_controversy or analysis.domain_risk_score >= 0.5:
        return "high"
    
    # High sensitivity for academic audiences
    if audience in ("phd", "professor"):
        return "high"
    
    # Medium sensitivity for complex topics
    if analysis.complexity_score >= 0.5:
        return "medium"
    
    return "low"


# =============================================================================
# BEAST WORKFLOW: Source Authority Tiers
# =============================================================================

SOURCE_AUTHORITY_TIERS = {
    # Tier 1 - Primary: Highest trust, official and peer-reviewed
    "tier1_primary": {
        "patterns": (".gov", ".edu", "arxiv.org", "nature.com", "science.org", "ieee.org", "acm.org"),
        "keywords": ("official", "peer-reviewed", "journal", "proceedings"),
        "weight": 1.0,
        "min_credibility": 0.85,
    },
    # Tier 2 - High: Established media, recognized experts, standards bodies
    "tier2_high": {
        "patterns": ("docs.", "developer.", "research.", "standards.", "rfc-editor.org"),
        "keywords": ("documentation", "specification", "standard", "whitepaper"),
        "weight": 0.85,
        "min_credibility": 0.70,
    },
    # Tier 3 - Secondary: Quality blogs, industry reports, verified sources
    "tier3_secondary": {
        "patterns": ("github.com", "stackoverflow.com", "medium.com"),
        "keywords": ("guide", "tutorial", "report", "analysis"),
        "weight": 0.65,
        "min_credibility": 0.50,
    },
    # Tier 4 - Contextual: Forums, discussions (sentiment and edge cases only)
    "tier4_contextual": {
        "patterns": ("reddit.com", "forum", "community", "discuss"),
        "keywords": ("discussion", "opinion", "experience"),
        "weight": 0.40,
        "min_credibility": 0.30,
    },
}


def classify_source_tier(url: str, domain: str) -> str:
    """Classify source into authority tier."""
    lowered_url = url.lower()
    lowered_domain = domain.lower()
    
    # Check Tier 1 - Primary
    tier1 = SOURCE_AUTHORITY_TIERS["tier1_primary"]
    if any(pattern in lowered_domain for pattern in tier1["patterns"]):
        return "tier1_primary"
    
    # Check Tier 2 - High
    tier2 = SOURCE_AUTHORITY_TIERS["tier2_high"]
    if any(pattern in lowered_domain or pattern in lowered_url for pattern in tier2["patterns"]):
        return "tier2_high"
    
    # Check Tier 4 - Contextual (check before Tier 3 to catch forums)
    tier4 = SOURCE_AUTHORITY_TIERS["tier4_contextual"]
    if any(pattern in lowered_domain for pattern in tier4["patterns"]):
        return "tier4_contextual"
    
    # Default to Tier 3 - Secondary
    return "tier3_secondary"


def get_tier_weight(tier: str) -> float:
    """Get retrieval weight for source tier."""
    return SOURCE_AUTHORITY_TIERS.get(tier, SOURCE_AUTHORITY_TIERS["tier3_secondary"])["weight"]


def get_tier_min_credibility(tier: str) -> float:
    """Get minimum credibility threshold for source tier."""
    return SOURCE_AUTHORITY_TIERS.get(tier, SOURCE_AUTHORITY_TIERS["tier3_secondary"])["min_credibility"]


# =============================================================================
# BEAST WORKFLOW: Anti-Spam and Quality Filtering
# =============================================================================

SEO_SPAM_PATTERNS = (
    # Content farm indicators
    "top 10", "top 5", "best of", "you won't believe",
    "click here", "subscribe now", "limited time", "act now",
    "affiliate", "sponsored", "advertisement", "promoted",
    # Low-quality content indicators
    "generated by ai", "written by chatgpt", "this article was",
    "as an ai language model", "i cannot", "i don't have access",
    # Clickbait patterns
    "shocking", "amazing", "unbelievable", "jaw-dropping",
    "secret", "hack", "trick", "revealed",
)

CONTENT_FARM_DOMAINS = (
    "buzzfeed.com", "listicle", "clickbait",
    "contentfarm", "articlespinner",
)


def detect_seo_spam(title: str, snippet: str, excerpt: str) -> bool:
    """Detect SEO spam and low-quality content."""
    text = f"{title} {snippet} {excerpt}".lower()
    
    # Check for spam patterns
    spam_hits = sum(1 for pattern in SEO_SPAM_PATTERNS if pattern in text)
    if spam_hits >= 2:
        return True
    
    # Check for excessive promotional language
    promo_words = ("buy", "sale", "discount", "offer", "deal", "free", "win", "prize")
    promo_hits = sum(1 for word in promo_words if word in text)
    if promo_hits >= 3:
        return True
    
    return False


def detect_ai_generated_low_quality(excerpt: str) -> bool:
    """Detect AI-generated low-quality content."""
    lowered = excerpt.lower()
    
    ai_indicators = (
        "as an ai", "i'm an ai", "as a language model",
        "i cannot provide", "i don't have real-time",
        "please consult", "it's important to note that",
        "in conclusion,", "to summarize,", "in summary,",
    )
    
    indicator_hits = sum(1 for indicator in ai_indicators if indicator in lowered)
    return indicator_hits >= 2


def calculate_content_quality_score(title: str, snippet: str, excerpt: str, domain: str) -> float:
    """Calculate overall content quality score."""
    score = 1.0
    
    # Penalize spam
    if detect_seo_spam(title, snippet, excerpt):
        score -= 0.4
    
    # Penalize AI-generated low-quality
    if detect_ai_generated_low_quality(excerpt):
        score -= 0.3
    
    # Penalize content farm domains
    if any(farm in domain.lower() for farm in CONTENT_FARM_DOMAINS):
        score -= 0.35
    
    # Reward substantive content
    word_count = len(excerpt.split())
    if word_count >= 100:
        score += 0.1
    elif word_count < 30:
        score -= 0.15
    
    return max(0.0, min(1.0, score))


# =============================================================================
# BEAST WORKFLOW: Enhanced Contradiction Detection
# =============================================================================

POSITIVE_STANCE_MARKERS = (
    "effective", "successful", "recommended", "proven", "works",
    "beneficial", "improves", "increases", "positive", "advantage",
    "outperforms", "superior", "better", "optimal", "significant",
    "strong evidence", "confirmed", "validated", "supported",
)

NEGATIVE_STANCE_MARKERS = (
    "ineffective", "failed", "not recommended", "disproven", "doesn't work",
    "harmful", "worsens", "decreases", "negative", "disadvantage",
    "underperforms", "inferior", "worse", "suboptimal", "insignificant",
    "weak evidence", "refuted", "invalidated", "unsupported", "flawed",
)

UNCERTAINTY_MARKERS = (
    "uncertain", "unclear", "unknown", "debated", "controversial",
    "mixed results", "conflicting", "inconsistent", "preliminary",
    "limited evidence", "needs more research", "insufficient data",
)


def calculate_stance_score(text: str) -> tuple[int, int, int]:
    """Calculate positive, negative, and uncertainty stance scores."""
    lowered = text.lower()
    
    positive = sum(1 for marker in POSITIVE_STANCE_MARKERS if marker in lowered)
    negative = sum(1 for marker in NEGATIVE_STANCE_MARKERS if marker in lowered)
    uncertain = sum(1 for marker in UNCERTAINTY_MARKERS if marker in lowered)
    
    return positive, negative, uncertain


def detect_numerical_contradiction(excerpt_a: str, excerpt_b: str) -> bool:
    """Detect if two excerpts contain contradictory numerical claims."""
    # Extract percentages
    pct_pattern = r"(\d+(?:\.\d+)?)\s*%"
    pcts_a = [float(m) for m in re.findall(pct_pattern, excerpt_a)]
    pcts_b = [float(m) for m in re.findall(pct_pattern, excerpt_b)]
    
    # Check if any percentages differ by more than 20 points
    for p_a in pcts_a:
        for p_b in pcts_b:
            if abs(p_a - p_b) > 20:
                return True
    
    return False


def detect_temporal_contradiction(excerpt_a: str, excerpt_b: str) -> bool:
    """Detect temporal conflicts (old data contradicting new data)."""
    year_pattern = r"\b(20\d{2})\b"
    years_a = [int(y) for y in re.findall(year_pattern, excerpt_a)]
    years_b = [int(y) for y in re.findall(year_pattern, excerpt_b)]
    
    if not years_a or not years_b:
        return False
    
    # If sources are 3+ years apart, might have temporal conflict
    min_a, max_a = min(years_a), max(years_a)
    min_b, max_b = min(years_b), max(years_b)
    
    year_gap = abs(max(max_a, max_b) - min(min_a, min_b))
    return year_gap >= 3


def classify_contradiction_type(excerpt_a: str, excerpt_b: str, domain_a: str, domain_b: str) -> tuple[str, str]:
    """Classify the type of contradiction and provide explanation."""
    pos_a, neg_a, unc_a = calculate_stance_score(excerpt_a)
    pos_b, neg_b, unc_b = calculate_stance_score(excerpt_b)
    
    # Stance polarity contradiction
    stance_diff = (pos_a - neg_a) - (pos_b - neg_b)
    if abs(stance_diff) >= 2:
        return "stance_polarity", f"Sources show opposing positions: {domain_a} (stance: {pos_a - neg_a:+d}) vs {domain_b} (stance: {pos_b - neg_b:+d})"
    
    # Numerical contradiction
    if detect_numerical_contradiction(excerpt_a, excerpt_b):
        return "numerical", f"Sources report different numbers: {domain_a} vs {domain_b}"
    
    # Temporal contradiction
    if detect_temporal_contradiction(excerpt_a, excerpt_b):
        return "temporal", f"Sources from different time periods may have outdated vs current findings"
    
    # Scope contradiction (general vs specific)
    if _has_scope_conflict(excerpt_a, excerpt_b):
        return "scope", f"Sources differ in scope: general claim vs specific exception"
    
    return "none", ""


def _has_scope_conflict(excerpt_a: str, excerpt_b: str) -> bool:
    """Detect scope conflicts (general claims vs specific exceptions)."""
    general_markers = ("always", "never", "all", "none", "every", "universal")
    specific_markers = ("except", "unless", "but", "however", "in some cases", "sometimes")
    
    a_lower = excerpt_a.lower()
    b_lower = excerpt_b.lower()
    
    a_general = any(m in a_lower for m in general_markers)
    a_specific = any(m in a_lower for m in specific_markers)
    b_general = any(m in b_lower for m in general_markers)
    b_specific = any(m in b_lower for m in specific_markers)
    
    return (a_general and b_specific) or (b_general and a_specific)


# =============================================================================
# BEAST WORKFLOW: Confidence Calibration
# =============================================================================

def calculate_claim_confidence(
    supporting_sources: int,
    opposing_sources: int,
    source_tiers: list[str],
    has_primary_source: bool,
    verification_rate: float,
) -> tuple[str, str]:
    """Calculate confidence level for a claim with rationale."""
    
    # High confidence: 3+ agreeing Tier 1 sources, no contradictions
    tier1_count = sum(1 for t in source_tiers if t == "tier1_primary")
    if tier1_count >= 3 and opposing_sources == 0 and verification_rate >= 0.8:
        return "high", "3+ primary sources agree with no contradictions"
    
    if supporting_sources >= 3 and opposing_sources == 0 and has_primary_source:
        return "high", "Multiple sources including primary agree with no contradictions"
    
    # Moderate confidence: 2+ agreeing sources, minor contradictions resolved
    if supporting_sources >= 2 and opposing_sources <= 1:
        if has_primary_source:
            return "moderate", "2+ sources agree with primary support, minor contradictions"
        return "moderate", "2+ sources agree, contradictions are minor"
    
    # Low confidence: single source or unresolved contradictions
    if supporting_sources == 1 or opposing_sources >= supporting_sources:
        return "low", "Single source support or significant contradictions"
    
    # Uncertain: insufficient evidence
    if supporting_sources == 0:
        return "uncertain", "No direct source support found"
    
    return "moderate", "Evidence supports claim with some limitations"
