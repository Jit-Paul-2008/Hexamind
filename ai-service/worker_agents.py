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

    async def gather_evidence(self, topic: str) -> Any:
        """Prefetch research context over the network (run in parallel)."""
        search_query = await self._generate_search_query(topic)
        return await self.researcher.research(search_query)

    async def run_analysis(self, topic: str, research_context: Any, context: Optional[str] = None) -> Dict[str, Any]:
        """Execute the worker's inference and Mini-Critique sequentially."""
        logger.info(f"Worker [{self.role}] starting inference on topic: {topic}")
        
        # 2. Specialized Analysis (with pruned context)
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
            "Task: List 2 missing details or logical flaws. If the analysis is perfect, output 'Satisfied'. "
            "CRITICAL CONSTRAINTS: Be extremely concise. Max 3 sentences. Limit <think> tags to a maximum of 2 sentences. Do NOT overthink."
        )
        return await self.provider.generate_text(
            prompt,
            system_prompt="You are a skeptical Peer Reviewer. Your goal is to ensure scientific rigor. DO NOT OVERTHINK.",
            max_tokens=400
        )

    async def _refine(self, topic: str, initial_analysis: str, critique: str) -> str:
        """Refines the analysis based on the mini-critique."""
        prompt = (
            f"Improve this {self.role} analysis of {topic} based on these notes:\n{critique}\n\n"
            f"Original Analysis:\n{initial_analysis}\n\n"
            "CRITICAL CONSTRAINTS: Fix the issues directly. Limit <think> tags to a maximum of 2 sentences. Do NOT output a long thought process."
        )
        return await self.provider.generate_text(
            prompt,
            system_prompt=f"You are a professional {self.role.capitalize()}. Refine the report. BE BRIEF.",
            max_tokens=600
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
        """Perform specialized synthesis with Neuro-Symbolic Context Pruning."""
        role_keywords = {
            WorkerRole.HISTORIAN: ["history", "timeline", "past", "evolution", "century", "early", "origin", "pedagogy", "traditional"],
            WorkerRole.AUDITOR: ["fail", "risk", "gap", "lack", "issue", "problem", "challenge", "criticism", "limitation"],
            WorkerRole.ANALYST: ["how", "mechanism", "structure", "system", "outcome", "framework", "practical", "implement"],
            WorkerRole.RESEARCHER: ["study", "data", "percent", "evidence", "research", "case", "report", "finding"]
        }.get(self.role, [])

        pruned_sources = []
        for s in sources:
            snippet_text = s.snippet.lower() if s.snippet else ""
            if any(kw in snippet_text for kw in role_keywords):
                pruned_sources.append(s)
        
        # Soft-fallback: If pruning removes EVERYTHING, just use the top 3 generally.
        if not pruned_sources:
            pruned_sources = sources[:3]

        source_text = "\n".join([f"- {s.title}: {s.snippet}" for s in pruned_sources[:5]])
        
        system_prompts = {
            WorkerRole.RESEARCHER: "You are a Fact-Checking Specialist. Report objective data.",
            WorkerRole.HISTORIAN: "You are a Historian. Focus on timelines and changes over time.",
            WorkerRole.AUDITOR: "You are a Quality Auditor. Focus on gaps and contradictions.",
            WorkerRole.ANALYST: "You are a Technical Analyst. Focus on 'How' things work."
        }
        
        prompt = (
            f"Analyze this topic using the provided evidence: {topic}\n\n"
            f"Role-Pruned Evidence:\n{source_text}\n\n"
            f"Global Context:\n{context or 'No additional context provided.'}\n\n"
            "Requirements:\n"
            "1. Be specific to your role.\n"
            "2. Cite your sources.\n"
            "3. BE EXTREMELY BRIEF (Max 3 paragraphs).\n"
            "4. CRITICAL THINKING BUDGET: Limit your <think> tags to a maximum of 3 sentences. DO NOT spiral into infinite reasoning loops.\n"
        )
        
        return await self.provider.generate_text(
            prompt,
            system_prompt=system_prompts.get(self.role, "You are a Research Assistant. DO NOT OVERTHINK."),
            max_tokens=800
        )
