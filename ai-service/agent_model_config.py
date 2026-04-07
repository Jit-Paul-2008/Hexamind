"""
Agent Model Specialization Mapping
Configure which LLM models are best for each agent role
"""

from dataclasses import dataclass


@dataclass
class AgentModelConfig:
    """Configuration for an agent's model preferences."""
    agent_id: str
    primary_ollama_model: str  # First choice - local, fast
    fallback_hf_model: str  # Second choice - cloud, slower
    temperature: float = 0.7
    max_tokens: int = 800
    system_prompt_suffix: str = ""


# Agent-Model Specialization Matrix
# Each agent gets the best model for its role
# ALL HARMONIZED TO 14B FOR XEON POWER
AGENT_MODEL_SPECIALIZATION = {
    "advocate": AgentModelConfig(
        agent_id="advocate",
        primary_ollama_model="qwen2.5:7b",
        fallback_hf_model="mistralai/Mistral-7B-Instruct-v0.2",
        temperature=0.6,
        max_tokens=600,
        system_prompt_suffix="Focus on building the strongest evidence-based case. MAX 3 PARAGRAPHS. DO NOT OVERTHINK."
    ),
    
    "researcher": AgentModelConfig(
        agent_id="researcher",
        primary_ollama_model="qwen2.5:7b",
        fallback_hf_model="teknium/OpenHermes-2.5-Mistral-7B",
        temperature=0.6,
        max_tokens=800,
        system_prompt_suffix="Synthesize sources into a comprehensive, well-structured research report. BE BRIEF AND DIRECT."
    ),
    
    "critic": AgentModelConfig(
        agent_id="critic",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="teknium/OpenHermes-2.5-Mistral-7B",
        temperature=0.7,
        max_tokens=900,
        system_prompt_suffix="Review the research report for bias, gaps, and unsupported claims."
    ),
    
    "skeptic": AgentModelConfig(
        agent_id="skeptic",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="meta-llama/Llama-2-70b-chat-hf",
        temperature=0.7,
        max_tokens=900,
        system_prompt_suffix="Challenge assumptions and identify failure modes aggressively."
    ),
    
    "synthesiser": AgentModelConfig(
        agent_id="synthesiser",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="tiiuae/falcon-7b-instruct",
        temperature=0.75,
        max_tokens=800,
        system_prompt_suffix="Integrate competing perspectives into a coherent recommendation."
    ),
    
    "oracle": AgentModelConfig(
        agent_id="oracle",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="EleutherAI/gpt-neox-20b",
        temperature=0.8,
        max_tokens=900,
        system_prompt_suffix="Generate specific forecasts with confidence levels and triggers."
    ),
    
    "verifier": AgentModelConfig(
        agent_id="verifier",
        primary_ollama_model="qwen2.5:7b",
        fallback_hf_model="teknium/OpenHermes-2.5-Mistral-7B",
        temperature=0.5,
        max_tokens=500,
        system_prompt_suffix="Verify claims against evidence with clear verdicts. USE BULLET POINTS."
    ),

    # Aurora Diamond Expert roles (AuroraGraph / reasoning_graph.py)
    "historian": AgentModelConfig(
        agent_id="historian",
        primary_ollama_model="qwen2.5:7b",
        fallback_hf_model="teknium/OpenHermes-2.5-Mistral-7B",
        temperature=0.6,
        max_tokens=800,
        system_prompt_suffix="Focus on timelines, historical evolution, and changes over time. BE CONCISE."
    ),

    "auditor": AgentModelConfig(
        agent_id="auditor",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="teknium/OpenHermes-2.5-Mistral-7B",
        temperature=0.7,
        max_tokens=900,
        system_prompt_suffix="Focus on gaps, contradictions, and critical weaknesses. Limit <think> to 2 sentences."
    ),

    "analyst": AgentModelConfig(
        agent_id="analyst",
        primary_ollama_model="qwen2.5:7b",
        fallback_hf_model="teknium/OpenHermes-2.5-Mistral-7B",
        temperature=0.65,
        max_tokens=800,
        system_prompt_suffix="Focus on implementation strategies, mechanisms, and practical outcomes. BE DIRECT."
    ),

    "orchestrator": AgentModelConfig(
        agent_id="orchestrator",
        primary_ollama_model="qwen2.5:7b",
        fallback_hf_model="mistralai/Mistral-7B-Instruct-v0.2",
        temperature=0.5,
        max_tokens=400,
        system_prompt_suffix="Decompose the query into specialized research tasks."
    ),
}


def get_agent_model_config(agent_id: str) -> AgentModelConfig:
    """
    Get the optimal model configuration for an agent.
    
    Args:
        agent_id: The agent identifier (e.g., 'advocate', 'skeptic')
    
    Returns:
        AgentModelConfig with primary and fallback models
    """
    return AGENT_MODEL_SPECIALIZATION.get(
        agent_id,
        AGENT_MODEL_SPECIALIZATION["advocate"]  # Default fallback
    )


def list_all_models() -> dict:
    """
    Return all models used by the system.
    
    Returns:
        Dict mapping agent IDs to their model choices
    """
    models = {}
    for agent_id, config in AGENT_MODEL_SPECIALIZATION.items():
        models[agent_id] = {
            "primary": config.primary_ollama_model,
            "fallback": config.fallback_hf_model,
        }
    return models
