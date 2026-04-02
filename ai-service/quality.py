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


@dataclass(frozen=True)
class ClaimVerification:
    claim: str
    status: str
    evidence: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class CitationIntegrityFinding:
    sourceId: str
    reachable: bool
    excerptOverlap: float
    freshnessScore: float
    status: str
    rationale: str


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
    has_claim_map = "claim-to-citation map" in final_answer.lower()
    has_uncertainty = "uncertainty" in final_answer.lower() or "open questions" in final_answer.lower()
    has_report_plan = "report plan" in final_answer.lower()
    generic_template_hits = _generic_template_hit_count(final_answer)
    citation_integrity_findings = _audit_citations(final_answer, research)

    claim_verifications = _verify_claims(final_answer, research)
    verified_count = sum(1 for item in claim_verifications if item.status == "verified")
    weakly_supported_count = sum(1 for item in claim_verifications if item.status == "weakly-supported")
    contested_count = sum(1 for item in claim_verifications if item.status == "contested")
    unverified_count = sum(1 for item in claim_verifications if item.status == "unverified")
    claim_verification_rate = (
        (verified_count / len(claim_verifications)) if claim_verifications else 0.0
    )

    contradictions = _detect_contradictions(query, research)
    contradiction_count = len(contradictions)
    contradiction_covered = contradiction_count == 0 or "contradiction" in final_answer.lower()

    citation_score = min(1.0, citation_count / 4.0) * 30.0
    source_score = min(1.0, source_count / 8.0) * 20.0
    diversity_score = 0.0
    if source_count:
        diversity_score = min(1.0, unique_domains / max(1, source_count)) * 15.0
    credibility_score = average_credibility * 15.0
    structure_score = 10.0 if has_claim_map else 0.0
    transparency_score = 10.0 if contradiction_covered and has_uncertainty else 5.0 if contradiction_covered else 0.0
    verification_score = claim_verification_rate * 10.0
    template_penalty = min(8.0, generic_template_hits * 1.5)
    integrity_score = _average_citation_integrity(citation_integrity_findings)
    freshness_score = _average_source_freshness(research)
    trust_score = round(
        max(
            0.0,
            (claim_verification_rate * 35.0)
            + (integrity_score * 25.0)
            + (freshness_score * 10.0)
            + (source_score * 0.6)
            + (diversity_score * 0.5)
            + (structure_score * 0.4)
            + (transparency_score * 0.5)
            - (contested_count * 2.0)
            - (unverified_count * 1.0),
        ),
        2,
    )

    overall_score = round(
        citation_score
        + source_score
        + diversity_score
        + credibility_score
        + structure_score
        + transparency_score
        + verification_score,
        2,
    )
    overall_score = round(max(0.0, overall_score - template_penalty), 2)

    passing = (
        overall_score >= 70
        and citation_count >= (4 if source_count > 0 else 0)
        and (source_count == 0 or unique_domains >= min(3, source_count))
        and contradiction_covered
        and (not claim_verifications or claim_verification_rate >= 0.5)
    )
    if has_report_plan and generic_template_hits >= 6:
        passing = False
    if trust_score < 50.0 and source_count > 0:
        passing = False

    return {
        "query": query,
        "overallScore": overall_score,
        "trustScore": trust_score,
        "passing": passing,
        "metrics": {
            "citationCount": citation_count,
            "sourceCount": source_count,
            "uniqueDomains": unique_domains,
            "averageCredibility": round(average_credibility, 3),
            "contradictionCount": contradiction_count,
            "hasClaimToCitationMap": has_claim_map,
            "hasUncertaintyDisclosure": has_uncertainty,
            "hasReportPlan": has_report_plan,
            "genericTemplateHitCount": generic_template_hits,
            "verifiedClaimCount": verified_count,
            "weaklySupportedClaimCount": weakly_supported_count,
            "contestedClaimCount": contested_count,
            "unverifiedClaimCount": unverified_count,
            "claimVerificationRate": round(claim_verification_rate, 3),
            "citationIntegrityScore": round(integrity_score, 3),
            "sourceFreshnessScore": round(freshness_score, 3),
        },
        "claimVerifications": [
            {
                "claim": item.claim,
                "status": item.status,
                "evidence": list(item.evidence),
                "rationale": item.rationale,
            }
            for item in claim_verifications
        ],
        "contradictionFindings": [
            {
                "sourceA": finding.sourceA,
                "sourceB": finding.sourceB,
                "reason": finding.reason,
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
