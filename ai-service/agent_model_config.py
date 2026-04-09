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
    "researcher": AgentModelConfig(
        agent_id="researcher",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="teknium/OpenHermes-2.5-Mistral-7B",
        temperature=0.4,
        max_tokens=400,
        system_prompt_suffix="Identify factual errors or missing current statistics in the draft. Output ONLY JSON diffs."
    ),
    
    "synthesiser": AgentModelConfig(
        agent_id="synthesiser",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="tiiuae/falcon-7b-instruct",
        temperature=0.75,
        max_tokens=800,
        system_prompt_suffix="Integrate competing perspectives into a coherent recommendation."
    ),
    
    # Aurora Diamond Expert roles (AuroraGraph / reasoning_graph.py)
    "historian": AgentModelConfig(
        agent_id="historian",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="teknium/OpenHermes-2.5-Mistral-7B",
        temperature=0.4,
        max_tokens=400,
        system_prompt_suffix="Identify historical factual errors in the draft. Output ONLY JSON diffs."
    ),

    "auditor": AgentModelConfig(
        agent_id="auditor",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="teknium/OpenHermes-2.5-Mistral-7B",
        temperature=0.4,
        max_tokens=400,
        system_prompt_suffix="Identify quality issues, gaps, or contradictions in the draft. Output ONLY JSON diffs."
    ),

    "analyst": AgentModelConfig(
        agent_id="analyst",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="teknium/OpenHermes-2.5-Mistral-7B",
        temperature=0.4,
        max_tokens=400,
        system_prompt_suffix="Identify technical implementation errors or outcome gaps in the draft. Output ONLY JSON diffs."
    ),

    "drafter": AgentModelConfig(
        agent_id="drafter",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="mistralai/Mistral-7B-Instruct-v0.2",
        temperature=0.4,
        max_tokens=2000,
        system_prompt_suffix="Generate a comprehensive, encyclopedic Markdown research report in an LLM-Wiki format."
    ),

    "orchestrator": AgentModelConfig(
        agent_id="orchestrator",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="mistralai/Mistral-7B-Instruct-v0.2",
        temperature=0.5,
        max_tokens=200,
        system_prompt_suffix="Decompose the query into specialized research tasks. Do not think, just output JSON list."
    ),

    "anchor_worker": AgentModelConfig(
        agent_id="anchor_worker",
        primary_ollama_model="deepseek-r1:14b",
        fallback_hf_model="mistralai/Mistral-7B-Instruct-v0.2",
        temperature=0.1,
        max_tokens=500,
        system_prompt_suffix="Extract hard facts from text as a strict JSON list of anchors."
    ),
}


def get_agent_model_config(agent_id: str) -> AgentModelConfig:
    """
    Get the optimal model configuration for an agent.
    
    Args:
        agent_id: The agent identifier (e.g., 'researcher', 'historian')
    
    Returns:
        AgentModelConfig with primary and fallback models
    """
    return AGENT_MODEL_SPECIALIZATION.get(
        agent_id,
        AGENT_MODEL_SPECIALIZATION["orchestrator"]  # Default fallback
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
