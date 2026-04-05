"""
Cost-Aware Routing for Hexamind
Implements smart model selection based on query complexity and cost optimization
"""

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple


class QueryComplexity(Enum):
    SIMPLE = "simple"      # Definitions, facts, basic explanations
    MODERATE = "moderate"  # Analysis, comparisons, synthesis
    COMPLEX = "complex"    # Multi-step reasoning, forecasting


@dataclass
class ModelConfig:
    name: str
    cost_per_1k_tokens: float
    quality_score: float
    speed_factor: float  # 1.0 = baseline, higher = faster
    max_context: int


class CostAwareRouter:
    """Smart routing system that optimizes cost vs quality based on query complexity"""
    
    def __init__(self):
        self.model_configs = {
            "local_light": ModelConfig(
                name="llama3.2:3b",
                cost_per_1k_tokens=0.0,
                quality_score=0.7,
                speed_factor=2.0,
                max_context=8192
            ),
            "local_balanced": ModelConfig(
                name="llama3.2:8b", 
                cost_per_1k_tokens=0.0,
                quality_score=0.85,
                speed_factor=1.0,
                max_context=8192
            ),
            "local_heavy": ModelConfig(
                name="llama3.2:70b",
                cost_per_1k_tokens=0.0,
                quality_score=0.95,
                speed_factor=0.3,
                max_context=8192
            ),
            "cloud_fast": ModelConfig(
                name="gpt-3.5-turbo",
                cost_per_1k_tokens=0.002,
                quality_score=0.8,
                speed_factor=1.5,
                max_context=16385
            ),
            "cloud_balanced": ModelConfig(
                name="gpt-4",
                cost_per_1k_tokens=0.03,
                quality_score=0.92,
                speed_factor=0.8,
                max_context=8192
            ),
            "cloud_heavy": ModelConfig(
                name="gpt-4-turbo",
                cost_per_1k_tokens=0.01,
                quality_score=0.94,
                speed_factor=1.0,
                max_context=128000
            )
        }
        
        self.cost_mode = os.getenv("HEXAMIND_COST_MODE", "balanced")  # free, balanced, max
        
    def analyze_query_complexity(self, query: str) -> QueryComplexity:
        """Analyze query to determine complexity level"""
        
        # Simple queries indicators
        simple_patterns = [
            r'\b(what|who|when|where|define|explain)\b',
            r'\b(meaning|definition|example)\b',
            r'^.{1,50}\?$'  # Short questions
        ]
        
        # Complex queries indicators  
        complex_patterns = [
            r'\b(analyze|compare|evaluate|synthesize|forecast)\b',
            r'\b(advantages?|disadvantages?|tradeoffs?|implications?)\b',
            r'\b(scenario|projection|recommendation|strategy)\b',
            r'\b(because|however|therefore|although)\b',
            r'^.{150,}'  # Long queries
        ]
        
        query_lower = query.lower()
        
        # Check for complexity indicators
        complex_matches = sum(1 for pattern in complex_patterns if re.search(pattern, query_lower))
        simple_matches = sum(1 for pattern in simple_patterns if re.search(pattern, query_lower))
        
        if complex_matches >= 2 or len(query) > 200:
            return QueryComplexity.COMPLEX
        elif simple_matches >= 1 and len(query) < 100:
            return QueryComplexity.SIMPLE
        else:
            return QueryComplexity.MODERATE
    
    def select_optimal_model(self, 
                           query: str, 
                           agent_type: str,
                           cost_mode: str = None) -> ModelConfig:
        """Select optimal model based on query complexity, agent type, and cost mode"""
        
        cost_mode = cost_mode or self.cost_mode
        complexity = self.analyze_query_complexity(query)
        
        # Agent-specific requirements
        agent_requirements = {
            "advocate": {"min_quality": 0.8, "complexity_boost": 0},
            "skeptic": {"min_quality": 0.85, "complexity_boost": 1},  # Needs more reasoning
            "synthesiser": {"min_quality": 0.9, "complexity_boost": 1},  # Complex integration
            "oracle": {"min_quality": 0.85, "complexity_boost": 0},  # Forecasting
            "verifier": {"min_quality": 0.8, "complexity_boost": 0}   # Validation
        }
        
        reqs = agent_requirements.get(agent_type, {"min_quality": 0.8, "complexity_boost": 0})
        
        # Filter models by requirements
        suitable_models = []
        for model in self.model_configs.values():
            if model.quality_score >= reqs["min_quality"]:
                suitable_models.append(model)
        
        # Adjust complexity based on agent requirements
        if complexity == QueryComplexity.SIMPLE and reqs["complexity_boost"] > 0:
            complexity = QueryComplexity.MODERATE
        elif complexity == QueryComplexity.MODERATE and reqs["complexity_boost"] > 0:
            complexity = QueryComplexity.COMPLEX
        
        # Cost-based selection
        if cost_mode == "free":
            # Only local models
            suitable_models = [m for m in suitable_models if m.cost_per_1k_tokens == 0]
            if complexity == QueryComplexity.SIMPLE:
                return self.model_configs["local_light"]
            else:
                return self.model_configs["local_balanced"]
                
        elif cost_mode == "max":
            # Best quality regardless of cost
            best_model = max(suitable_models, key=lambda m: m.quality_score)
            return best_model
            
        else:  # balanced mode
            # Optimize cost-quality tradeoff
            if complexity == QueryComplexity.SIMPLE:
                # Prefer fast, cheap models
                candidates = [m for m in suitable_models if m.speed_factor >= 1.0]
                return min(candidates, key=lambda m: m.cost_per_1k_tokens)
            elif complexity == QueryComplexity.MODERATE:
                # Balance quality and cost
                return min(suitable_models, key=lambda m: m.cost_per_1k_tokens / m.quality_score)
            else:  # COMPLEX
                # Prioritize quality for complex queries
                return max(suitable_models, key=lambda m: m.quality_score)
    
    def estimate_cost(self, query: str, agent_type: str) -> Dict[str, float]:
        """Estimate cost and performance metrics for model selection"""
        model = self.select_optimal_model(query, agent_type)
        complexity = self.analyze_query_complexity(query)
        
        # Rough token estimation
        estimated_tokens = len(query.split()) * 1.3  # ~1.3 tokens per word
        if complexity == QueryComplexity.COMPLEX:
            estimated_tokens *= 2.0  # Complex queries generate more tokens
        
        estimated_cost = (estimated_tokens / 1000) * model.cost_per_1k_tokens
        estimated_time = estimated_tokens / (1000 * model.speed_factor)  # Rough timing
        
        return {
            "model": model.name,
            "estimated_cost_usd": estimated_cost,
            "estimated_time_seconds": estimated_time,
            "quality_score": model.quality_score,
            "complexity": complexity.value,
            "tokens_estimated": estimated_tokens
        }


# Global router instance
cost_router = CostAwareRouter()


def route_query(query: str, agent_type: str, cost_mode: str = None) -> str:
    """Route query to optimal model and return model name"""
    model = cost_router.select_optimal_model(query, agent_type, cost_mode)
    return model.name


def estimate_query_cost(query: str, agent_type: str) -> Dict[str, float]:
    """Get cost estimation for query routing"""
    return cost_router.estimate_cost(query, agent_type)
