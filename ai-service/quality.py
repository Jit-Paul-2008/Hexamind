from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import combinations

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

    claim_verifications = _verify_claims(final_answer, research)
    verified_count = sum(1 for item in claim_verifications if item.status == "verified")
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

    passing = (
        overall_score >= 70
        and citation_count >= (4 if source_count > 0 else 0)
        and (source_count == 0 or unique_domains >= min(3, source_count))
        and contradiction_covered
        and (not claim_verifications or claim_verification_rate >= 0.5)
    )

    return {
        "query": query,
        "overallScore": overall_score,
        "passing": passing,
        "metrics": {
            "citationCount": citation_count,
            "sourceCount": source_count,
            "uniqueDomains": unique_domains,
            "averageCredibility": round(average_credibility, 3),
            "contradictionCount": contradiction_count,
            "hasClaimToCitationMap": has_claim_map,
            "hasUncertaintyDisclosure": has_uncertainty,
            "verifiedClaimCount": verified_count,
            "contestedClaimCount": contested_count,
            "unverifiedClaimCount": unverified_count,
            "claimVerificationRate": round(claim_verification_rate, 3),
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
        "notes": _quality_notes(
            passing=passing,
            citation_count=citation_count,
            source_count=source_count,
            unique_domains=unique_domains,
            contradiction_count=contradiction_count,
            has_claim_map=has_claim_map,
            claim_verification_rate=claim_verification_rate,
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
            verifications.append(
                ClaimVerification(
                    claim=claim,
                    status="verified",
                    evidence=tuple(sorted(set(citations + tuple(supporting))))[:4],
                    rationale="Claim terms align with supporting source excerpts.",
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
                    status="contested",
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
    if not research or len(research.sources) < 2:
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

    return notes
