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

    overall_score = round(
        citation_score
        + source_score
        + diversity_score
        + credibility_score
        + structure_score
        + transparency_score,
        2,
    )

    passing = (
        overall_score >= 70
        and citation_count >= (4 if source_count > 0 else 0)
        and (source_count == 0 or unique_domains >= min(3, source_count))
        and contradiction_covered
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
        },
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
        ),
    }


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

    return notes
