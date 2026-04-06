import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from inference_provider import InferenceProvider, get_provider
from research import InternetResearcher

logger = logging.getLogger(__name__)

class WorkerRole:
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    HISTORIAN = "historian"
    AUDITOR = "auditor"

class ResearchWorker:
    """Specialized worker that handles a specific research node."""
    
    def __init__(self, role: str, provider: Optional[InferenceProvider] = None):
        self.role = role
        self.provider = provider or get_provider()
        self.researcher = InternetResearcher()

    async def run(self, topic: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Execute the worker's specialized task with a Mini-Critique loop."""
        logger.info(f"Worker [{self.role}] starting on topic: {topic}")
        
        # 1. Specialized Search
        search_query = await self._generate_search_query(topic)
        research_context = await self.researcher.research(search_query)
        
        # 2. Specialized Analysis
        analysis = await self._analyze(topic, research_context.sources, context)
        
        # 3. Mini-Critique (Recursive verification)
        critique = await self._critique(topic, analysis, research_context.sources)
        
        # 4. Refinement
        if "Inference Error" not in critique and "Satisfied" not in critique:
            analysis = await self._refine(topic, analysis, critique)
            
        return {
            "role": self.role,
            "topic": topic,
            "analysis": analysis,
            "sources": [s.url for s in research_context.sources[:3]]
        }

    async def _critique(self, topic: str, analysis: str, sources: List[Any]) -> str:
        """Hunts for gaps in the local analysis."""
        source_text = "\n".join([f"- {s.title}: {s.snippet}" for s in sources[:3]])
        prompt = (
            f"Review this {self.role} analysis of {topic}:\n{analysis}\n\n"
            f"Evidence context:\n{source_text}\n\n"
            "Task: List 2 missing details or logical flaws. If the analysis is perfect, output 'Satisfied'."
        )
        return await self.provider.generate_text(
            prompt,
            system_prompt="You are a skeptical Peer Reviewer. Your goal is to ensure scientific rigor."
        )

    async def _refine(self, topic: str, initial_analysis: str, critique: str) -> str:
        """Refines the analysis based on the mini-critique."""
        prompt = (
            f"Improve this {self.role} analysis of {topic} based on these notes:\n{critique}\n\n"
            f"Original Analysis:\n{initial_analysis}"
        )
        return await self.provider.generate_text(
            prompt,
            system_prompt=f"You are a professional {self.role.capitalize()}. Refine the report."
        )


    async def _generate_search_query(self, topic: str) -> str:
        """Tailor the search query based on the worker's role."""
        prompts = {
            WorkerRole.RESEARCHER: f"Find current facts and data about {topic}",
            WorkerRole.HISTORIAN: f"Find historical context and evolution of {topic}",
            WorkerRole.AUDITOR: f"Find critical reviews and common failures of {topic}",
            WorkerRole.ANALYST: f"Find technical mechanisms and logical structures of {topic}"
        }
        return prompts.get(self.role, topic)

    async def _analyze(self, topic: str, sources: List[Any], context: Optional[str] = None) -> str:
        """Perform specialized synthesis."""
        source_text = "\n".join([f"- {s.title}: {s.snippet}" for s in sources[:5]])
        
        system_prompts = {
            WorkerRole.RESEARCHER: "You are a Fact-Checking Specialist. Report objective data.",
            WorkerRole.HISTORIAN: "You are a Historian. Focus on timelines and changes over time.",
            WorkerRole.AUDITOR: "You are a Quality Auditor. Focus on gaps and contradictions.",
            WorkerRole.ANALYST: "You are a Technical Analyst. Focus on 'How' things work."
        }
        
        prompt = (
            f"Analyze this topic using the provided evidence: {topic}\n\n"
            f"Evidence:\n{source_text}\n\n"
            f"Global Context:\n{context or 'No additional context provided.'}\n\n"
            "Requirements:\n"
            "1. Be specific to your role.\n"
            "2. Cite your sources.\n"
        )
        
        return await self.provider.generate_text(
            prompt,
            system_prompt=system_prompts.get(self.role, "You are a Research Assistant.")
        )
