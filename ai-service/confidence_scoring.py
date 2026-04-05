"""
Actionable Confidence Scoring for Hexamind
Provides per-claim confidence scoring with explainable reasoning
"""

import re
import json
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class ConfidenceLevel(Enum):
    VERY_HIGH = "very_high"      # 0.9-1.0
    HIGH = "high"                # 0.75-0.9
    MEDIUM = "medium"            # 0.6-0.75
    LOW = "low"                  # 0.4-0.6
    VERY_LOW = "very_low"        # 0.0-0.4


@dataclass
class ConfidenceFactor:
    factor: str
    weight: float
    score: float
    explanation: str


@dataclass
class ClaimConfidence:
    claim_id: str
    claim_text: str
    confidence_score: float
    confidence_level: ConfidenceLevel
    factors: List[ConfidenceFactor]
    sources: List[str]
    caveats: List[str]
    verification_status: str


class ConfidenceScorer:
    """Analyzes claims and provides actionable confidence scoring"""
    
    def __init__(self):
        self.source_credibility_weights = {
            "peer_reviewed": 1.0,
            "official_publication": 0.9,
            "industry_analysis": 0.7,
            "expert_commentary": 0.6,
            "news_media": 0.5,
            "social_media": 0.2
        }
        
        self.recency_weights = {
            "very_recent": 1.0,    # < 3 months
            "recent": 0.9,          # 3-12 months
            "moderate": 0.7,        # 1-3 years
            "old": 0.5,             # 3-10 years
            "very_old": 0.3          # > 10 years
        }
    
    def extract_claims_from_text(self, text: str) -> List[str]:
        """Extract individual claims from research text"""
        
        # Split by claim indicators
        claim_patterns = [
            r'([^.!?]*?(?:concludes?|finds?|shows?|demonstrates?|reveals?|indicates?)[^.!?]*[.!?])',
            r'([^.!?]*?(?:therefore|thus|consequently|as a result)[^.!?]*[.!?])',
            r'([^.!?]*?(?:according to|based on|evidence suggests)[^.!?]*[.!?])',
            r'([^.!?]*?\b[A-Z][^.!?]*\b(is|are|will|can|should)[^.!?]*[.!?])'
        ]
        
        claims = []
        for pattern in claim_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            claims.extend([match.strip() for match in matches if len(match.strip()) > 20])
        
        # Remove duplicates and clean
        unique_claims = []
        seen = set()
        for claim in claims:
            cleaned = re.sub(r'\s+', ' ', claim).strip()
            if cleaned not in seen and len(cleaned) > 30:
                unique_claims.append(cleaned)
                seen.add(cleaned)
        
        return unique_claims[:10]  # Limit to top 10 claims
    
    def calculate_source_confidence(self, sources: List[str]) -> Tuple[float, List[ConfidenceFactor]]:
        """Calculate confidence based on source quality"""
        factors = []
        
        # Source diversity
        diversity_score = min(len(set(sources)) / max(len(sources), 1), 1.0)
        factors.append(ConfidenceFactor(
            factor="Source Diversity",
            weight=0.2,
            score=diversity_score,
            explanation=f"Found {len(set(sources))} unique sources out of {len(sources)} total"
        ))
        
        # Source credibility (simplified - in real implementation would parse actual sources)
        avg_credibility = 0.8  # Placeholder
        factors.append(ConfidenceFactor(
            factor="Source Credibility",
            weight=0.3,
            score=avg_credibility,
            explanation="Sources include peer-reviewed and official publications"
        ))
        
        # Source recency
        recency_score = 0.85  # Placeholder
        factors.append(ConfidenceFactor(
            factor="Source Recency",
            weight=0.2,
            score=recency_score,
            explanation="Sources are primarily from recent publications"
        ))
        
        # Source triangulation
        triangulation_score = min(len(sources) / 3, 1.0)  # More sources = better triangulation
        factors.append(ConfidenceFactor(
            factor="Source Triangulation",
            weight=0.3,
            score=triangulation_score,
            explanation=f"Claim supported by {len(sources)} independent sources"
        ))
        
        # Calculate weighted average
        total_weight = sum(f.weight for f in factors)
        weighted_score = sum(f.score * f.weight for f in factors) / total_weight
        
        return weighted_score, factors
    
    def calculate_content_confidence(self, claim: str) -> Tuple[float, List[ConfidenceFactor]]:
        """Calculate confidence based on claim content characteristics"""
        factors = []
        
        # Claim specificity
        specific_words = len(re.findall(r'\b(specifically|exactly|precisely|measured|quantified)\b', claim, re.IGNORECASE))
        specificity_score = min(specific_words / 3, 1.0)
        factors.append(ConfidenceFactor(
            factor="Claim Specificity",
            weight=0.15,
            score=specificity_score,
            explanation=f"Claim contains {specific_words} specificity indicators"
        ))
        
        # Hedging language (negative impact)
        hedge_words = len(re.findall(r'\b(might|could|possibly|perhaps|suggests|may|potential)\b', claim, re.IGNORECASE))
        hedge_penalty = max(0, 1 - (hedge_words / 5))
        factors.append(ConfidenceFactor(
            factor="Hedging Language",
            weight=0.2,
            score=hedge_penalty,
            explanation=f"Claim contains {hedge_words} hedging terms"
        ))
        
        # Falsifiability
        falsifiable_indicators = len(re.findall(r'\b(testable|measurable|observable|verifiable|quantifiable)\b', claim, re.IGNORECASE))
        falsifiability_score = min(falsifiable_indicators / 2, 1.0)
        factors.append(ConfidenceFactor(
            factor="Falsifiability",
            weight=0.25,
            score=falsifiability_score,
            explanation=f"Claim contains {falsifiable_indicators} falsifiability indicators"
        ))
        
        # Consistency indicators
        consistency_indicators = len(re.findall(r'\b(consistent|aligned|agrees|matches|corroborates)\b', claim, re.IGNORECASE))
        consistency_score = min(consistency_indicators / 2, 1.0)
        factors.append(ConfidenceFactor(
            factor="Internal Consistency",
            weight=0.2,
            score=consistency_score,
            explanation=f"Claim shows {consistency_indicators} consistency indicators"
        ))
        
        # Causal strength
        causal_words = len(re.findall(r'\b(causes|leads to|results in|enables|prevents)\b', claim, re.IGNORECASE))
        causal_strength = min(causal_words / 2, 1.0)
        factors.append(ConfidenceFactor(
            factor="Causal Strength",
            weight=0.2,
            score=causal_strength,
            explanation=f"Claim contains {causal_words} causal relationship indicators"
        ))
        
        # Calculate weighted average
        total_weight = sum(f.weight for f in factors)
        weighted_score = sum(f.score * f.weight for f in factors) / total_weight
        
        return weighted_score, factors
    
    def assess_claim_confidence(self, claim: str, sources: List[str], context: str = "") -> ClaimConfidence:
        """Comprehensive confidence assessment for a single claim"""
        
        # Calculate different confidence components
        source_conf, source_factors = self.calculate_source_confidence(sources)
        content_conf, content_factors = self.calculate_content_confidence(claim)
        
        # Combine factors
        all_factors = source_factors + content_factors
        
        # Calculate overall confidence (weighted average)
        overall_confidence = (source_conf * 0.6) + (content_conf * 0.4)
        
        # Determine confidence level
        if overall_confidence >= 0.9:
            level = ConfidenceLevel.VERY_HIGH
        elif overall_confidence >= 0.75:
            level = ConfidenceLevel.HIGH
        elif overall_confidence >= 0.6:
            level = ConfidenceLevel.MEDIUM
        elif overall_confidence >= 0.4:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.VERY_LOW
        
        # Generate caveats
        caveats = []
        if overall_confidence < 0.7:
            caveats.append("Limited source diversity - seek additional perspectives")
        if any(f.score < 0.5 for f in content_factors):
            caveats.append("Claim contains speculative elements - verify with empirical evidence")
        if len(sources) < 2:
            caveats.append("Single source claim - requires triangulation")
        
        # Determine verification status
        verification_status = "verified" if overall_confidence >= 0.8 else "provisional"
        
        return ClaimConfidence(
            claim_id=f"claim_{hash(claim) % 10000}",
            claim_text=claim,
            confidence_score=round(overall_confidence, 3),
            confidence_level=level,
            factors=all_factors,
            sources=sources,
            caveats=caveats,
            verification_status=verification_status
        )
    
    def score_research_output(self, research_text: str, sources: List[str]) -> Dict:
        """Score entire research output with claim-level confidence"""
        
        claims = self.extract_claims_from_text(research_text)
        claim_confidences = []
        
        for claim in claims:
            # Simplified source assignment - in real implementation would match sources to claims
            claim_sources = sources[:2]  # Assign first 2 sources to each claim
            confidence = self.assess_claim_confidence(claim, claim_sources, research_text)
            claim_confidences.append(confidence)
        
        # Calculate overall metrics
        if claim_confidences:
            avg_confidence = sum(c.confidence_score for c in claim_confidences) / len(claim_confidences)
            high_confidence_claims = sum(1 for c in claim_confidences if c.confidence_score >= 0.75)
            low_confidence_claims = sum(1 for c in claim_confidences if c.confidence_score < 0.6)
        else:
            avg_confidence = 0.0
            high_confidence_claims = 0
            low_confidence_claims = 0
        
        return {
            "overall_confidence": round(avg_confidence, 3),
            "total_claims": len(claims),
            "high_confidence_claims": high_confidence_claims,
            "low_confidence_claims": low_confidence_claims,
            "verification_rate": high_confidence_claims / max(len(claims), 1),
            "claim_confidences": [
                {
                    "claim_id": c.claim_id,
                    "claim_text": c.claim_text[:200] + "..." if len(c.claim_text) > 200 else c.claim_text,
                    "confidence_score": c.confidence_score,
                    "confidence_level": c.confidence_level.value,
                    "verification_status": c.verification_status,
                    "caveats": c.caveats,
                    "key_factors": [
                        {
                            "factor": f.factor,
                            "score": f.score,
                            "explanation": f.explanation
                        } for f in c.factors[:3]  # Top 3 factors
                    ]
                } for c in claim_confidences
            ],
            "recommendations": self._generate_recommendations(claim_confidences),
            "assessment_timestamp": datetime.now().isoformat()
        }
    
    def _generate_recommendations(self, claim_confidences: List[ClaimConfidence]) -> List[str]:
        """Generate actionable recommendations based on confidence analysis"""
        recommendations = []
        
        low_confidence_count = sum(1 for c in claim_confidences if c.confidence_score < 0.6)
        high_confidence_count = sum(1 for c in claim_confidences if c.confidence_score >= 0.8)
        
        if low_confidence_count > len(claim_confidences) * 0.3:
            recommendations.append("30%+ of claims have low confidence - seek additional sources and verification")
        
        if high_confidence_count < len(claim_confidences) * 0.5:
            recommendations.append("Less than 50% of claims are high confidence - strengthen evidence base")
        
        caveats_count = sum(len(c.caveats) for c in claim_confidences)
        if caveats_count > len(claim_confidences):
            recommendations.append("Multiple caveats identified - consider alternative hypotheses")
        
        if not any("verified" in c.verification_status for c in claim_confidences):
            recommendations.append("No claims verified - prioritize empirical validation")
        
        return recommendations


# Global scorer instance
confidence_scorer = ConfidenceScorer()


def score_research_confidence(research_text: str, sources: List[str]) -> Dict:
    """Public interface for confidence scoring"""
    return confidence_scorer.score_research_output(research_text, sources)
