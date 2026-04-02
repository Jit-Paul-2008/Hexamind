from __future__ import annotations

import re
import time
from dataclasses import dataclass
from itertools import combinations
from urllib.parse import urlparse

import httpx

from research import ResearchContext


@dataclass(frozen=True)
class ContradictionFinding:
    sourceA: str
    sourceB: str
    reason: str
    contradiction_type: str = "stance_polarity"  # stance_polarity, numerical, temporal, scope
    severity: str = "moderate"  # low, moderate, high


@dataclass(frozen=True)
class ClaimVerification:
    claim: str
    status: str  # verified, weakly-supported, contested, unverified
    evidence: tuple[str, ...]
    rationale: str
    confidence: str = "moderate"  # high, moderate, low, uncertain
    supporting_count: int = 0
    opposing_count: int = 0


@dataclass(frozen=True)
class CitationIntegrityFinding:
    sourceId: str
    reachable: bool
    excerptOverlap: float
    freshnessScore: float
    status: str
    rationale: str


@dataclass(frozen=True)
class QualityGateResult:
    """Result from a single quality gate check."""
    gate_name: str
    passed: bool
    score: float
    max_score: float
    issues: tuple[str, ...]
    recommendations: tuple[str, ...]


@dataclass(frozen=True)
class TrustScoreBreakdown:
    """Detailed breakdown of trust score components."""
    verification_score: float  # 35% weight
    integrity_score: float  # 25% weight
    freshness_score: float  # 10% weight
    coverage_score: float  # 12% weight
    structure_score: float  # 8% weight
    transparency_score: float  # 10% weight
    total_penalties: float
    final_score: float
    grade: str  # A, B, C, D, F


def analyze_pipeline_quality(
    query: str,
    assembled: dict[str, str],
    final_answer: str,
    research: ResearchContext | None,
) -> dict[str, object]:
    combined = "\n".join(list(assembled.values()) + [final_answer])
    citation_count = _citation_count(combined)
    source_count = len(research.sources) if research else 0
    unique_domains = len({source.domain for source in research.sources}) if research else 0
    average_credibility = _average_credibility(research)
    has_claim_map = "claim-to-citation map" in final_answer.lower() or "claim graph" in final_answer.lower()
    has_uncertainty = any(marker in final_answer.lower() for marker in ("uncertainty", "open questions", "limitations", "confidence", "caveats"))
    has_contradiction_section = any(marker in final_answer.lower() for marker in ("contradiction", "conflicting", "disputed", "contested"))
    has_report_plan = "report plan" in final_answer.lower()
    generic_template_hits = _generic_template_hit_count(final_answer)
    citation_integrity_findings = _audit_citations(final_answer, research)

    # Beast workflow: Enhanced claim verification with confidence levels
    claim_verifications = _verify_claims_v2(final_answer, research)
    verified_count = sum(1 for item in claim_verifications if item.status == "verified")
    weakly_supported_count = sum(1 for item in claim_verifications if item.status == "weakly-supported")
    contested_count = sum(1 for item in claim_verifications if item.status == "contested")
    unverified_count = sum(1 for item in claim_verifications if item.status == "unverified")
    high_confidence_count = sum(1 for item in claim_verifications if item.confidence == "high")
    claim_verification_rate = (
        ((verified_count + weakly_supported_count * 0.5) / len(claim_verifications)) if claim_verifications else 0.0
    )

    # Beast workflow: Enhanced contradiction detection with types
    contradictions = _detect_contradictions_v2(query, research)
    contradiction_count = len(contradictions)
    high_severity_contradictions = sum(1 for c in contradictions if c.severity == "high")
    contradiction_covered = contradiction_count == 0 or has_contradiction_section

    # Beast workflow: Multi-tier quality gates
    gate_results = _run_quality_gates(
        citation_count=citation_count,
        source_count=source_count,
        unique_domains=unique_domains,
        average_credibility=average_credibility,
        has_claim_map=has_claim_map,
        has_uncertainty=has_uncertainty,
        has_contradiction_section=has_contradiction_section,
        generic_template_hits=generic_template_hits,
        claim_verification_rate=claim_verification_rate,
        contradiction_count=contradiction_count,
        contradiction_covered=contradiction_covered,
        final_answer=final_answer,
        research=research,
    )

    # Calculate component scores
    citation_score = min(1.0, citation_count / 6.0) * 25.0  # Raised bar: 6 citations for full score
    source_score = min(1.0, source_count / 8.0) * 15.0
    diversity_score = 0.0
    if source_count:
        diversity_score = min(1.0, unique_domains / max(1, source_count)) * 12.0
    credibility_score = average_credibility * 15.0
    structure_score = 8.0 if has_claim_map else 0.0
    structure_score += 5.0 if has_uncertainty else 0.0
    transparency_score = 10.0 if contradiction_covered and has_uncertainty else 5.0 if contradiction_covered else 0.0
    verification_component = claim_verification_rate * 15.0
    template_penalty = min(10.0, generic_template_hits * 2.0)  # Harsher penalty
    integrity_score = _average_citation_integrity(citation_integrity_findings)
    freshness_score = _average_source_freshness(research)
    
    # Beast workflow: Trust Score v2 Framework
    trust_breakdown = _calculate_trust_score_v2(
        claim_verification_rate=claim_verification_rate,
        integrity_score=integrity_score,
        freshness_score=freshness_score,
        source_count=source_count,
        unique_domains=unique_domains,
        has_claim_map=has_claim_map,
        has_uncertainty=has_uncertainty,
        contradiction_covered=contradiction_covered,
        contested_count=contested_count,
        unverified_count=unverified_count,
        generic_template_hits=generic_template_hits,
        high_severity_contradictions=high_severity_contradictions,
    )
    trust_score = trust_breakdown.final_score

    overall_score = round(
        citation_score
        + source_score
        + diversity_score
        + credibility_score
        + structure_score
        + transparency_score
        + verification_component,
        2,
    )
    overall_score = round(max(0.0, overall_score - template_penalty), 2)

    # Beast workflow: Stricter passing criteria
    all_gates_passed = all(gate.passed for gate in gate_results)
    passing = (
        overall_score >= 72  # Raised threshold
        and citation_count >= (5 if source_count > 0 else 0)  # Raised bar
        and (source_count == 0 or unique_domains >= min(3, source_count))
        and contradiction_covered
        and (not claim_verifications or claim_verification_rate >= 0.60)  # Raised bar
        and trust_score >= 55  # Trust score gate
        and high_severity_contradictions == 0  # No high-severity unaddressed contradictions
    )
    if has_report_plan and generic_template_hits >= 5:  # Stricter
        passing = False
    if trust_score < 50.0 and source_count > 0:
        passing = False

    return {
        "query": query,
        "overallScore": overall_score,
        "trustScore": trust_score,
        "trustGrade": trust_breakdown.grade,
        "passing": passing,
        "allGatesPassed": all_gates_passed,
        "metrics": {
            "citationCount": citation_count,
            "sourceCount": source_count,
            "uniqueDomains": unique_domains,
            "averageCredibility": round(average_credibility, 3),
            "contradictionCount": contradiction_count,
            "highSeverityContradictions": high_severity_contradictions,
            "hasClaimToCitationMap": has_claim_map,
            "hasUncertaintyDisclosure": has_uncertainty,
            "hasContradictionSection": has_contradiction_section,
            "hasReportPlan": has_report_plan,
            "genericTemplateHitCount": generic_template_hits,
            "verifiedClaimCount": verified_count,
            "weaklySupportedClaimCount": weakly_supported_count,
            "contestedClaimCount": contested_count,
            "unverifiedClaimCount": unverified_count,
            "highConfidenceClaimCount": high_confidence_count,
            "claimVerificationRate": round(claim_verification_rate, 3),
            "citationIntegrityScore": round(integrity_score, 3),
            "sourceFreshnessScore": round(freshness_score, 3),
        },
        "qualityGates": [
            {
                "name": gate.gate_name,
                "passed": gate.passed,
                "score": round(gate.score, 2),
                "maxScore": round(gate.max_score, 2),
                "issues": list(gate.issues),
                "recommendations": list(gate.recommendations),
            }
            for gate in gate_results
        ],
        "claimVerifications": [
            {
                "claim": item.claim,
                "status": item.status,
                "confidence": item.confidence,
                "evidence": list(item.evidence),
                "rationale": item.rationale,
                "supportingCount": item.supporting_count,
                "opposingCount": item.opposing_count,
            }
            for item in claim_verifications
        ],
        "contradictionFindings": [
            {
                "sourceA": finding.sourceA,
                "sourceB": finding.sourceB,
                "reason": finding.reason,
                "type": finding.contradiction_type,
                "severity": finding.severity,
            }
            for finding in contradictions
        ],
        "citationIntegrityFindings": [
            {
                "sourceId": finding.sourceId,
                "reachable": finding.reachable,
                "excerptOverlap": finding.excerptOverlap,
                "freshnessScore": finding.freshnessScore,
                "status": finding.status,
                "rationale": finding.rationale,
            }
            for finding in citation_integrity_findings
        ],
        "trustScoreComponents": {
            "verification": round(claim_verification_rate * 35.0, 2),
            "integrity": round(integrity_score * 25.0, 2),
            "freshness": round(freshness_score * 10.0, 2),
            "coverage": round(source_score * 0.6 + diversity_score * 0.5, 2),
            "structure": round(structure_score * 0.4, 2),
            "transparency": round(transparency_score * 0.5, 2),
            "penalties": round((contested_count * 2.0) + (unverified_count * 1.0) + template_penalty, 2),
        },
        "notes": _quality_notes(
            passing=passing,
            citation_count=citation_count,
            source_count=source_count,
            unique_domains=unique_domains,
            contradiction_count=contradiction_count,
            has_claim_map=has_claim_map,
            claim_verification_rate=claim_verification_rate,
            generic_template_hits=generic_template_hits,
            trust_score=trust_score,
        ),
    }


def _verify_claims(final_answer: str, research: ResearchContext | None) -> list[ClaimVerification]:
    claims = _extract_claim_lines(final_answer)
    if not claims:
        return []

    if not research or not research.sources:
        return [
            ClaimVerification(
                claim=claim,
                status="unverified",
                evidence=(),
                rationale="No research sources available for verification.",
            )
            for claim in claims
        ]

    verifications: list[ClaimVerification] = []
    for claim in claims:
        citations = tuple(sorted(set(re.findall(r"\[S\d+\]", claim))))
        claim_text = re.sub(r"\[S\d+\]", "", claim).strip(" -")
        claim_terms = _claim_terms(claim_text)

        supporting: list[str] = []
        opposing: list[str] = []
        for source in research.sources:
            excerpt = source.excerpt.lower()
            overlap = sum(1 for term in claim_terms if term in excerpt)
            if overlap >= max(2, len(claim_terms) // 3):
                if _stance_score(claim_text) * _stance_score(source.excerpt) < 0:
                    opposing.append(source.id)
                else:
                    supporting.append(source.id)

        if supporting and not opposing:
            status = "verified" if len(supporting) >= 2 or citations else "weakly-supported"
            verifications.append(
                ClaimVerification(
                    claim=claim,
                    status=status,
                    evidence=tuple(sorted(set(citations + tuple(supporting))))[:4],
                    rationale="Claim terms align with supporting source excerpts." if status == "verified" else "Claim has partial support but needs stronger corroboration.",
                )
            )
            continue

        if supporting and opposing:
            verifications.append(
                ClaimVerification(
                    claim=claim,
                    status="contested",
                    evidence=tuple(sorted(set(citations + tuple(supporting) + tuple(opposing))))[:5],
                    rationale="Sources show mixed evidence for this claim.",
                )
            )
            continue

        if citations:
            verifications.append(
                ClaimVerification(
                    claim=claim,
                    status="weakly-supported",
                    evidence=citations,
                    rationale="Claim cites sources but excerpt support is weak or indirect.",
                )
            )
            continue

        verifications.append(
            ClaimVerification(
                claim=claim,
                status="unverified",
                evidence=(),
                rationale="No source support found and no citation provided.",
            )
        )

    return verifications[:10]


def _extract_claim_lines(text: str) -> list[str]:
    claims: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("-") or re.match(r"^\d+\.", stripped):
            cleaned = stripped.lstrip("- ").strip()
            if len(cleaned) >= 45 and any(ch.isalpha() for ch in cleaned):
                claims.append(cleaned)
    return claims


def _claim_terms(claim: str) -> list[str]:
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
        "are",
        "was",
        "were",
        "can",
        "should",
        "would",
        "could",
        "will",
    }
    words = re.findall(r"[a-zA-Z0-9]{4,}", claim.lower())
    deduped: list[str] = []
    seen: set[str] = set()
    for word in words:
        if word in stop or word in seen:
            continue
        seen.add(word)
        deduped.append(word)
        if len(deduped) >= 12:
            break
    return deduped


def _citation_count(text: str) -> int:
    return len(set(re.findall(r"\[S\d+\]", text)))


def _average_credibility(research: ResearchContext | None) -> float:
    if not research or not research.sources:
        return 0.0
    total = sum(source.credibility_score for source in research.sources)
    return total / len(research.sources)


def _detect_contradictions(
    query: str,
    research: ResearchContext | None,
) -> list[ContradictionFinding]:
    if not research:
        return []

    precomputed = getattr(research, "contradictions", ())
    if precomputed:
        findings: list[ContradictionFinding] = []
        for item in precomputed[:5]:
            if isinstance(item, tuple) and len(item) == 3:
                findings.append(
                    ContradictionFinding(
                        sourceA=str(item[0]),
                        sourceB=str(item[1]),
                        reason=str(item[2]),
                    )
                )
        if findings:
            return findings

    if len(research.sources) < 2:
        return []

    findings: list[ContradictionFinding] = []
    for source_a, source_b in combinations(research.sources, 2):
        score_a = _stance_score(source_a.excerpt)
        score_b = _stance_score(source_b.excerpt)

        if score_a == 0 and score_b == 0:
            continue

        if score_a * score_b < 0 and abs(score_a - score_b) >= 2:
            findings.append(
                ContradictionFinding(
                    sourceA=f"{source_a.id} ({source_a.domain})",
                    sourceB=f"{source_b.id} ({source_b.domain})",
                    reason=f"Evidence polarity differs for query '{query}'.",
                )
            )

    return findings[:5]


def _stance_score(text: str) -> int:
    normalized = text.lower()
    positive_cues = [
        "improve",
        "improved",
        "effective",
        "success",
        "increase",
        "benefit",
        "outperform",
        "recommended",
    ]
    negative_cues = [
        "fail",
        "failed",
        "risk",
        "limitation",
        "uncertain",
        "not effective",
        "decline",
        "worse",
        "harm",
    ]
    positive = sum(1 for cue in positive_cues if cue in normalized)
    negative = sum(1 for cue in negative_cues if cue in normalized)
    return positive - negative


def _quality_notes(
    *,
    passing: bool,
    citation_count: int,
    source_count: int,
    unique_domains: int,
    contradiction_count: int,
    has_claim_map: bool,
    claim_verification_rate: float,
    generic_template_hits: int,
    trust_score: float,
) -> list[str]:
    notes: list[str] = []
    if passing:
        notes.append("Quality gate passed for deep-research output.")
    else:
        notes.append("Quality gate failed. Regeneration with stronger grounding is recommended.")

    if citation_count < 4 and source_count > 0:
        notes.append("Increase citation density to at least 4 unique source IDs.")
    if source_count > 0 and unique_domains < min(3, source_count):
        notes.append("Increase domain diversity to reduce source concentration risk.")
    if contradiction_count > 0:
        notes.append("Contradictions detected across sources. Ensure they are explicitly discussed.")
    if not has_claim_map:
        notes.append("Add a claim-to-citation map section in final synthesis.")
    if claim_verification_rate < 0.5:
        notes.append("Increase direct evidence support for key claims to improve verification rate.")
    if generic_template_hits > 0:
        notes.append("Reduce generic template phrasing and make the report planner more query-specific.")
    if trust_score < 50.0:
        notes.append("Improve citation integrity, freshness, and corroboration to raise trust score.")

    return notes


def _generic_template_hit_count(text: str) -> int:
    phrases = (
        "in conclusion",
        "overall,",
        "the best approach",
        "it is important to note",
        "in summary",
        "next steps",
        "consider the following",
        "confidence: moderate",
    )
    normalized = text.lower()
    return sum(1 for phrase in phrases if phrase in normalized)


def _audit_citations(final_answer: str, research: ResearchContext | None) -> list[CitationIntegrityFinding]:
    if not research or not research.sources:
        return []

    citations = sorted(set(re.findall(r"\[S\d+\]", final_answer)))
    if not citations:
        return [
            CitationIntegrityFinding(
                sourceId=source.id,
                reachable=_url_reachable(source.url),
                excerptOverlap=0.0,
                freshnessScore=round(source.recency_score if hasattr(source, "recency_score") else 0.0, 3),
                status="missing-citations",
                rationale="No source IDs were cited in the final answer.",
            )
            for source in research.sources[:6]
        ]

    findings: list[CitationIntegrityFinding] = []
    for source in research.sources[:6]:
        cited = source.id and f"[{source.id}]" in final_answer
        overlap = _citation_overlap_score(final_answer, source.excerpt)
        reachable = _url_reachable(source.url)
        freshness = round(getattr(source, "recency_score", 0.0), 3)
        if not reachable:
            status = "unreachable"
            rationale = "Citation URL did not respond to a reachability probe."
        elif cited and overlap >= 0.3:
            status = "verified"
            rationale = "Citation is reachable and overlaps with the cited excerpt."
        elif cited or overlap >= 0.15:
            status = "weakly-supported"
            rationale = "Citation is reachable but the excerpt overlap is partial."
        else:
            status = "unsupported"
            rationale = "Citation appears in the source inventory but is not grounded in the final answer."
        findings.append(
            CitationIntegrityFinding(
                sourceId=source.id,
                reachable=reachable,
                excerptOverlap=round(overlap, 3),
                freshnessScore=freshness,
                status=status,
                rationale=rationale,
            )
        )

    return findings


def _average_citation_integrity(findings: list[CitationIntegrityFinding]) -> float:
    if not findings:
        return 0.0
    total = 0.0
    for finding in findings:
        base = 0.0
        if finding.status == "verified":
            base = 1.0
        elif finding.status == "weakly-supported":
            base = 0.6
        elif finding.status == "unsupported":
            base = 0.3
        else:
            base = 0.1
        total += (base * 0.6) + (finding.excerptOverlap * 0.25) + (finding.freshnessScore * 0.15)
    return total / len(findings)


def _average_source_freshness(research: ResearchContext | None) -> float:
    if not research or not research.sources:
        return 0.0
    total = sum(getattr(source, "recency_score", 0.0) for source in research.sources)
    return min(1.0, total / len(research.sources))


def _citation_overlap_score(final_answer: str, excerpt: str) -> float:
    answer_terms = set(re.findall(r"[a-zA-Z0-9]{4,}", final_answer.lower()))
    excerpt_terms = set(re.findall(r"[a-zA-Z0-9]{4,}", excerpt.lower()))
    if not answer_terms or not excerpt_terms:
        return 0.0
    union = answer_terms | excerpt_terms
    if not union:
        return 0.0
    return len(answer_terms & excerpt_terms) / len(union)


def _url_reachable(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    if not domain:
        return False
    if any(token in domain for token in ("example.com", "example.org", "example.net", "example.gov", "localhost", "127.0.0.1")):
        return True
    try:
        response = httpx.head(url, timeout=2.5, follow_redirects=True)
        if response.status_code < 400:
            return True
        response = httpx.get(url, timeout=2.5, follow_redirects=True)
        return response.status_code < 400
    except Exception:
        return False


# =============================================================================
# BEAST WORKFLOW: Enhanced Claim Verification v2
# =============================================================================

def _verify_claims_v2(final_answer: str, research: ResearchContext | None) -> list[ClaimVerification]:
    """Enhanced claim verification with confidence levels and source counting."""
    claims = _extract_claim_lines(final_answer)
    if not claims:
        return []

    if not research or not research.sources:
        return [
            ClaimVerification(
                claim=claim,
                status="unverified",
                evidence=(),
                rationale="No research sources available for verification.",
                confidence="uncertain",
                supporting_count=0,
                opposing_count=0,
            )
            for claim in claims
        ]

    verifications: list[ClaimVerification] = []
    for claim in claims:
        citations = tuple(sorted(set(re.findall(r"\[S\d+\]", claim))))
        claim_text = re.sub(r"\[S\d+\]", "", claim).strip(" -")
        claim_terms = _claim_terms(claim_text)

        supporting: list[str] = []
        opposing: list[str] = []
        source_tiers: list[str] = []
        
        for source in research.sources:
            excerpt = source.excerpt.lower()
            overlap = sum(1 for term in claim_terms if term in excerpt)
            
            if overlap >= max(2, len(claim_terms) // 3):
                # Calculate stance alignment
                claim_stance = _stance_score(claim_text)
                source_stance = _stance_score(source.excerpt)
                
                # Track source tier for confidence calculation
                tier = _get_source_tier(source.domain, source.authority)
                source_tiers.append(tier)
                
                if claim_stance * source_stance < 0:
                    opposing.append(source.id)
                else:
                    supporting.append(source.id)

        has_primary = any(t == "tier1_primary" for t in source_tiers)
        
        # Determine status and confidence
        if supporting and not opposing:
            if len(supporting) >= 2 or citations:
                status = "verified"
                confidence = "high" if len(supporting) >= 3 and has_primary else "moderate"
                rationale = f"Claim supported by {len(supporting)} source(s) with no contradicting evidence."
            else:
                status = "weakly-supported"
                confidence = "moderate" if has_primary else "low"
                rationale = "Claim has partial support but needs stronger corroboration."
        elif supporting and opposing:
            status = "contested"
            confidence = "low"
            rationale = f"Sources show mixed evidence: {len(supporting)} supporting, {len(opposing)} opposing."
        elif citations:
            status = "weakly-supported"
            confidence = "low"
            rationale = "Claim cites sources but excerpt support is weak or indirect."
        else:
            status = "unverified"
            confidence = "uncertain"
            rationale = "No source support found and no citation provided."

        verifications.append(
            ClaimVerification(
                claim=claim,
                status=status,
                evidence=tuple(sorted(set(citations + tuple(supporting) + tuple(opposing))))[:6],
                rationale=rationale,
                confidence=confidence,
                supporting_count=len(supporting),
                opposing_count=len(opposing),
            )
        )

    return verifications[:12]  # Increased from 10


def _get_source_tier(domain: str, authority: str) -> str:
    """Map source to authority tier."""
    lowered = domain.lower()
    if lowered.endswith((".gov", ".edu")) or authority == "primary":
        return "tier1_primary"
    if authority == "high" or any(t in lowered for t in ("docs", "developer", "research")):
        return "tier2_high"
    if any(t in lowered for t in ("reddit", "forum", "community")):
        return "tier4_contextual"
    return "tier3_secondary"


# =============================================================================
# BEAST WORKFLOW: Enhanced Contradiction Detection v2
# =============================================================================

def _detect_contradictions_v2(
    query: str,
    research: ResearchContext | None,
) -> list[ContradictionFinding]:
    """Enhanced contradiction detection with types and severity levels."""
    if not research:
        return []

    # Check for precomputed contradictions first
    precomputed = getattr(research, "contradictions", ())
    if precomputed:
        findings: list[ContradictionFinding] = []
        for item in precomputed[:6]:
            if isinstance(item, tuple) and len(item) == 3:
                findings.append(
                    ContradictionFinding(
                        sourceA=str(item[0]),
                        sourceB=str(item[1]),
                        reason=str(item[2]),
                        contradiction_type="stance_polarity",
                        severity="moderate",
                    )
                )
        if findings:
            return findings

    if len(research.sources) < 2:
        return []

    findings: list[ContradictionFinding] = []
    for source_a, source_b in combinations(research.sources, 2):
        # Stance polarity check
        score_a = _stance_score(source_a.excerpt)
        score_b = _stance_score(source_b.excerpt)

        if score_a != 0 or score_b != 0:
            stance_diff = abs(score_a - score_b)
            if score_a * score_b < 0 and stance_diff >= 2:
                severity = "high" if stance_diff >= 4 else "moderate"
                findings.append(
                    ContradictionFinding(
                        sourceA=f"{source_a.id} ({source_a.domain})",
                        sourceB=f"{source_b.id} ({source_b.domain})",
                        reason=f"Evidence polarity differs: {source_a.domain} (stance: {score_a:+d}) vs {source_b.domain} (stance: {score_b:+d})",
                        contradiction_type="stance_polarity",
                        severity=severity,
                    )
                )
                continue

        # Numerical contradiction check
        if _has_numerical_contradiction(source_a.excerpt, source_b.excerpt):
            findings.append(
                ContradictionFinding(
                    sourceA=f"{source_a.id} ({source_a.domain})",
                    sourceB=f"{source_b.id} ({source_b.domain})",
                    reason="Sources report significantly different numerical values",
                    contradiction_type="numerical",
                    severity="moderate",
                )
            )
            continue

        # Temporal contradiction check  
        if _has_temporal_contradiction(source_a, source_b):
            findings.append(
                ContradictionFinding(
                    sourceA=f"{source_a.id} ({source_a.domain})",
                    sourceB=f"{source_b.id} ({source_b.domain})",
                    reason="Sources from different time periods may have outdated vs current findings",
                    contradiction_type="temporal",
                    severity="low",
                )
            )

    return findings[:6]


def _has_numerical_contradiction(excerpt_a: str, excerpt_b: str) -> bool:
    """Check for contradictory numerical claims."""
    pct_pattern = r"(\d+(?:\.\d+)?)\s*%"
    pcts_a = [float(m) for m in re.findall(pct_pattern, excerpt_a)]
    pcts_b = [float(m) for m in re.findall(pct_pattern, excerpt_b)]
    
    for p_a in pcts_a:
        for p_b in pcts_b:
            if abs(p_a - p_b) > 25:  # More than 25 percentage points difference
                return True
    return False


def _has_temporal_contradiction(source_a, source_b) -> bool:
    """Check for temporal conflicts based on recency scores."""
    recency_a = getattr(source_a, "recency_score", 0.5)
    recency_b = getattr(source_b, "recency_score", 0.5)
    return abs(recency_a - recency_b) >= 0.5  # Significant recency gap


# =============================================================================
# BEAST WORKFLOW: Multi-Tier Quality Gates
# =============================================================================

def _run_quality_gates(
    citation_count: int,
    source_count: int,
    unique_domains: int,
    average_credibility: float,
    has_claim_map: bool,
    has_uncertainty: bool,
    has_contradiction_section: bool,
    generic_template_hits: int,
    claim_verification_rate: float,
    contradiction_count: int,
    contradiction_covered: bool,
    final_answer: str,
    research: ResearchContext | None,
) -> list[QualityGateResult]:
    """Run all quality gates and return results."""
    gates: list[QualityGateResult] = []
    
    # Gate 1: Structural Requirements
    structural_issues: list[str] = []
    structural_recs: list[str] = []
    structural_score = 0.0
    structural_max = 25.0
    
    if has_claim_map:
        structural_score += 10.0
    else:
        structural_issues.append("Missing claim-to-citation map")
        structural_recs.append("Add a claim-to-citation map section showing which sources support each claim")
    
    if has_uncertainty:
        structural_score += 8.0
    else:
        structural_issues.append("Missing uncertainty/limitations disclosure")
        structural_recs.append("Add section discussing limitations, caveats, and open questions")
    
    if generic_template_hits < 3:
        structural_score += 7.0
    else:
        structural_issues.append(f"Too many generic template phrases ({generic_template_hits})")
        structural_recs.append("Replace generic language with query-specific analysis")
    
    gates.append(QualityGateResult(
        gate_name="structural",
        passed=structural_score >= 18.0,
        score=structural_score,
        max_score=structural_max,
        issues=tuple(structural_issues),
        recommendations=tuple(structural_recs),
    ))
    
    # Gate 2: Evidence Requirements
    evidence_issues: list[str] = []
    evidence_recs: list[str] = []
    evidence_score = 0.0
    evidence_max = 30.0
    
    if source_count > 0:
        if citation_count >= 5:
            evidence_score += 12.0
        elif citation_count >= 3:
            evidence_score += 6.0
            evidence_issues.append(f"Citation count ({citation_count}) below target (5+)")
            evidence_recs.append("Increase citation density with more source references")
        else:
            evidence_issues.append(f"Low citation count ({citation_count})")
            evidence_recs.append("Add more citations to support claims")
        
        if unique_domains >= 4:
            evidence_score += 10.0
        elif unique_domains >= 3:
            evidence_score += 6.0
        else:
            evidence_issues.append(f"Low domain diversity ({unique_domains} domains)")
            evidence_recs.append("Add sources from more diverse domains")
        
        if average_credibility >= 0.7:
            evidence_score += 8.0
        elif average_credibility >= 0.5:
            evidence_score += 4.0
            evidence_issues.append(f"Moderate source credibility ({average_credibility:.2f})")
            evidence_recs.append("Prioritize higher-authority sources")
        else:
            evidence_issues.append(f"Low source credibility ({average_credibility:.2f})")
            evidence_recs.append("Replace low-credibility sources with authoritative ones")
    else:
        evidence_score = 15.0  # No sources expected
    
    gates.append(QualityGateResult(
        gate_name="evidence",
        passed=evidence_score >= 20.0 or source_count == 0,
        score=evidence_score,
        max_score=evidence_max,
        issues=tuple(evidence_issues),
        recommendations=tuple(evidence_recs),
    ))
    
    # Gate 3: Verification Requirements
    verification_issues: list[str] = []
    verification_recs: list[str] = []
    verification_score = 0.0
    verification_max = 25.0
    
    if claim_verification_rate >= 0.75:
        verification_score += 15.0
    elif claim_verification_rate >= 0.5:
        verification_score += 8.0
        verification_issues.append(f"Verification rate ({claim_verification_rate:.0%}) below target (75%)")
        verification_recs.append("Strengthen evidence support for unverified claims")
    else:
        verification_issues.append(f"Low verification rate ({claim_verification_rate:.0%})")
        verification_recs.append("Add direct source support for major claims")
    
    if contradiction_covered:
        verification_score += 10.0
    else:
        verification_issues.append("Contradictions not addressed in output")
        verification_recs.append("Add section explicitly discussing contradicting evidence")
    
    gates.append(QualityGateResult(
        gate_name="verification",
        passed=verification_score >= 18.0,
        score=verification_score,
        max_score=verification_max,
        issues=tuple(verification_issues),
        recommendations=tuple(verification_recs),
    ))
    
    # Gate 4: Non-Generic Output
    nongeneric_issues: list[str] = []
    nongeneric_recs: list[str] = []
    nongeneric_score = 0.0
    nongeneric_max = 20.0
    
    word_count = len(final_answer.split())
    if word_count >= 400:
        nongeneric_score += 8.0
    elif word_count >= 200:
        nongeneric_score += 4.0
    else:
        nongeneric_issues.append(f"Output too brief ({word_count} words)")
        nongeneric_recs.append("Expand analysis with more detail and evidence")
    
    # Check for query-specific content
    if research and research.query:
        query_terms = set(re.findall(r"[a-zA-Z0-9]{4,}", research.query.lower()))
        answer_lower = final_answer.lower()
        term_hits = sum(1 for term in query_terms if term in answer_lower)
        if term_hits >= len(query_terms) * 0.6:
            nongeneric_score += 8.0
        else:
            nongeneric_issues.append("Output may not sufficiently address the specific query")
            nongeneric_recs.append("Ensure key query concepts are addressed directly")
    else:
        nongeneric_score += 4.0
    
    if generic_template_hits < 2:
        nongeneric_score += 4.0
    elif generic_template_hits < 4:
        nongeneric_score += 2.0
    
    gates.append(QualityGateResult(
        gate_name="non_generic",
        passed=nongeneric_score >= 14.0,
        score=nongeneric_score,
        max_score=nongeneric_max,
        issues=tuple(nongeneric_issues),
        recommendations=tuple(nongeneric_recs),
    ))
    
    return gates


# =============================================================================
# BEAST WORKFLOW: Trust Score v2 Framework
# =============================================================================

def _calculate_trust_score_v2(
    claim_verification_rate: float,
    integrity_score: float,
    freshness_score: float,
    source_count: int,
    unique_domains: int,
    has_claim_map: bool,
    has_uncertainty: bool,
    contradiction_covered: bool,
    contested_count: int,
    unverified_count: int,
    generic_template_hits: int,
    high_severity_contradictions: int,
) -> TrustScoreBreakdown:
    """Calculate comprehensive trust score with component breakdown."""
    
    # Component 1: Verification (35% weight)
    verification_component = claim_verification_rate * 35.0
    
    # Component 2: Integrity (25% weight)
    integrity_component = integrity_score * 25.0
    
    # Component 3: Freshness (10% weight)
    freshness_component = freshness_score * 10.0
    
    # Component 4: Coverage (12% weight)
    source_factor = min(1.0, source_count / 8.0)
    diversity_factor = min(1.0, unique_domains / 5.0) if source_count > 0 else 0.5
    coverage_component = ((source_factor * 0.5) + (diversity_factor * 0.5)) * 12.0
    
    # Component 5: Structure (8% weight)
    structure_component = 0.0
    if has_claim_map:
        structure_component += 5.0
    if has_uncertainty:
        structure_component += 3.0
    
    # Component 6: Transparency (10% weight)
    transparency_component = 0.0
    if contradiction_covered:
        transparency_component += 6.0
    if has_uncertainty:
        transparency_component += 4.0
    
    # Calculate penalties
    penalties = 0.0
    penalties += contested_count * 3.0  # Stricter penalty
    penalties += unverified_count * 1.5  # Stricter penalty
    penalties += generic_template_hits * 2.0
    penalties += high_severity_contradictions * 5.0  # New: high-severity contradiction penalty
    
    # Calculate final score
    raw_score = (
        verification_component
        + integrity_component
        + freshness_component
        + coverage_component
        + structure_component
        + transparency_component
    )
    final_score = max(0.0, min(100.0, raw_score - penalties))
    
    # Assign grade
    if final_score >= 85:
        grade = "A"
    elif final_score >= 75:
        grade = "B"
    elif final_score >= 60:
        grade = "C"
    elif final_score >= 45:
        grade = "D"
    else:
        grade = "F"
    
    return TrustScoreBreakdown(
        verification_score=round(verification_component, 2),
        integrity_score=round(integrity_component, 2),
        freshness_score=round(freshness_component, 2),
        coverage_score=round(coverage_component, 2),
        structure_score=round(structure_component, 2),
        transparency_score=round(transparency_component, 2),
        total_penalties=round(penalties, 2),
        final_score=round(final_score, 2),
        grade=grade,
    )


# =============================================================================
# BEAST WORKFLOW: Enhanced Generic Template Detection
# =============================================================================

def _generic_template_hit_count(text: str) -> int:
    """Enhanced detection of generic template language."""
    phrases = (
        # Common filler phrases
        "in conclusion",
        "overall,",
        "the best approach",
        "it is important to note",
        "in summary",
        "next steps",
        "consider the following",
        "confidence: moderate",
        # AI assistant patterns
        "as an ai",
        "i cannot provide",
        "please note that",
        "it's worth noting",
        "it's important to understand",
        "there are several",
        "there are many",
        "one thing to consider",
        # Low-value hedging
        "generally speaking",
        "in general",
        "for the most part",
        "it depends on",
        "various factors",
        # Placeholder language
        "further research is needed",
        "consult a professional",
        "seek expert advice",
    )
    normalized = text.lower()
    return sum(1 for phrase in phrases if phrase in normalized)
