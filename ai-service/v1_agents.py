"""
V1 Simplified Agent System for Free Tier Hosting
Reduces 5-agent system to 2-agent system while preserving core value
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class V1AgentConfig:
    id: str
    codename: str
    role: str
    purpose: str
    accent_color: str
    glow_color: str
    shape: str
    processing_order: int
    combines: list[str]  # Which original agents this combines


V1_AGENTS: tuple[V1AgentConfig, ...] = (
    V1AgentConfig(
        id="analyst",
        codename="Analyst",
        role="Balanced Research Analysis",
        purpose="Provides comprehensive opportunity analysis with built-in risk assessment and evidence evaluation. Combines the upside case from Advocate with critical risk analysis from Skeptic.",
        accent_color="#818cf8",
        glow_color="rgba(99, 102, 241, 0.28)",
        shape="tetrahedron",
        processing_order=1,
        combines=["advocate", "skeptic"]
    ),
    V1AgentConfig(
        id="synthesizer", 
        codename="Synthesizer",
        role="Executive Summary & Forecasting",
        purpose="Integrates analysis into actionable recommendations with scenario forecasting and confidence assessment. Combines synthesis from Synthesiser, forecasting from Oracle, and verification from Verifier.",
        accent_color="#34d399",
        glow_color="rgba(16, 185, 129, 0.28)",
        shape="dodecahedron",
        processing_order=2,
        combines=["synthesiser", "oracle", "verifier"]
    )
)


def get_v1_agent_prompts() -> dict[str, str]:
    """V1 optimized prompts that combine multiple agent capabilities"""
    
    return {
        "analyst": (
            "You are a BALANCED RESEARCH ANALYST providing comprehensive analysis of {query}. "
            "Your role combines opportunity identification with critical risk assessment.\n\n"
            
            "REQUIRED STRUCTURE:\n"
            "## Executive Summary\n"
            "## Opportunity Analysis\n"
            "- Key opportunities and benefits\n"
            "- Evidence supporting upside potential\n"
            "- Success factors and enablers\n\n"
            "## Risk Analysis\n" 
            "- Critical risks and challenges\n"
            "- Failure modes and mitigations\n"
            "- Evidence gaps and uncertainties\n\n"
            "## Evidence Assessment\n"
            "- Source quality and credibility\n"
            "- Contradictions and tensions\n"
            "- Confidence level in key claims\n\n"
            
            "ANALYSIS PRINCIPLES:\n"
            "- Balance optimism with skepticism\n"
            "- Cite evidence for all major claims\n"
            "- Flag assumptions and uncertainties\n"
            "- Use [Sx] citations for sources\n"
            "- Maintain professional, evidence-based tone\n\n"
            
            "Focus on actionable insights that decision-makers can use immediately."
        ),
        
        "synthesizer": (
            "You are an EXECUTIVE SYNTHESIZER transforming research analysis into decision-ready recommendations for {query}. "
            "Your role combines strategic synthesis, scenario forecasting, and confidence assessment.\n\n"
            
            "REQUIRED STRUCTURE:\n"
            "## Strategic Recommendation\n"
            "Clear, actionable recommendation with rationale\n\n"
            "## Implementation Roadmap\n"
            "- Immediate actions (0-3 months)\n"
            "- Short-term initiatives (3-12 months)\n"
            "- Long-term considerations (1+ years)\n\n"
            "## Scenario Outlook\n"
            "- Most Likely Outcome (60% probability)\n"
            "- Upside Scenario (25% probability)\n" 
            "- Downside Scenario (15% probability)\n"
            "- Key triggers and indicators\n\n"
            "## Risk Mitigation Plan\n"
            "- Critical risks and specific mitigations\n"
            "- Early warning signals\n"
            "- Contingency options\n\n"
            "## Confidence Assessment\n"
            "- Overall confidence level (High/Medium/Low)\n"
            "- Key assumptions and their validity\n"
            "- Evidence quality and gaps\n"
            "- Recommended validation steps\n\n"
            
            "SYNTHESIS PRINCIPLES:\n"
            "- Translate analysis into clear actions\n"
            "- Provide realistic timelines and resources\n"
            "- Balance ambition with practicality\n"
            "- Include specific next steps\n"
            "- Maintain professional executive tone\n\n"
            
            "Focus on what executives need to know to make informed decisions."
        )
    }


def get_v1_pipeline_config() -> dict:
    """V1 pipeline configuration optimized for free tier"""
    
    return {
        "agent_count": 2,
        "estimated_api_calls_per_query": 6,
        "estimated_cost_per_query": 0.18,  # USD
        "estimated_queries_per_month_free": 555,
        "processing_time_estimate": "30-60 seconds",
        
        "free_tier_optimizations": {
            "aggressive_caching": True,
            "prompt_compression": True,
            "batch_processing": False,  # V1 doesn't need batching
            "fallback_models": True,
            "token_optimization": True
        },
        
        "model_strategy": {
            "primary": "groq/llama3-70b-8192",  # Free tier, fast
            "fallback": "huggingface/mistral-7b-instruct",  # Free tier backup
            "local_fallback": "ollama/llama3.2:8b",  # If available
            "cost_mode": "free"
        },
        
        "quality_preservation": {
            "maintains_reasoning_transparency": True,
            "maintains_adversarial_analysis": True, 
            "maintains_structured_output": True,
            "maintains_confidence_scoring": True,
            "reduces_complexity": "60% fewer agents"
        }
    }
