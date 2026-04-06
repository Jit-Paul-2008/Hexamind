import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from inference_provider import get_provider
from research import InternetResearcher

from schemas import PipelineEvent, PipelineEventType

logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ResearchNode:
    id: str
    task: str
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)

class AuroraGraph:
    """The central orchestration engine for Hexamind Aurora."""
    
    def __init__(self, query: str):
        self.query = query
        self.nodes: Dict[str, ResearchNode] = {}
        self.context: Dict[str, Any] = {"query": query, "sources": [], "sub_answers": {}}
        self.provider = get_provider()
        self.researcher = InternetResearcher()

    async def run(self):
        """Execute the research graph and yield events."""
        logger.info(f"Starting Aurora Graph for query: {self.query}")
        
        # 1. PLAN
        yield self._event(PipelineEventType.AGENT_START, "planner")
        success = await self._plan_phase()
        if not success:
            yield self._event(PipelineEventType.PIPELINE_ERROR, "planner", self.context.get("plan", "Unknown Error during Planning"))
            logger.error("Pipeline halted: Planning failed.")
            return # HALT the graph
            
        yield self._event(PipelineEventType.AGENT_DONE, "planner", self.context["plan"])

        
        # 2. SEARCH
        yield self._event(PipelineEventType.AGENT_START, "researcher")
        await self._search_phase()
        yield self._event(PipelineEventType.AGENT_DONE, "researcher", f"Found {len(self.context['sources'])} sources.")
        
        # 3. ANALYZE
        yield self._event(PipelineEventType.AGENT_START, "analyst")
        await self._analyze_phase()
        yield self._event(PipelineEventType.AGENT_DONE, "analyst", self.context["draft"])
        
        # 4. CRITIQUE
        yield self._event(PipelineEventType.AGENT_START, "critic")
        await self._critique_phase()
        yield self._event(PipelineEventType.AGENT_DONE, "critic", self.context["critique"])
        
        # 5. FINALIZE
        yield self._event(PipelineEventType.AGENT_START, "synthesizer")
        final_report = await self._finalize_phase()
        yield self._event(PipelineEventType.AGENT_DONE, "synthesizer", final_report)
        
        yield self._event(PipelineEventType.PIPELINE_DONE, "output", final_report)

    def _event(self, type: PipelineEventType, agent_id: str, content: str = "") -> dict:
        """Helper to create a serialized PipelineEvent."""
        event = PipelineEvent(
            type=type,
            agentId=agent_id,
            fullContent=content,
            chunk=content if type == PipelineEventType.AGENT_CHUNK else None
        )
        return {
            "event": event.type.value,
            "data": event.model_dump_json()
        }

    async def _plan_phase(self) -> bool:
        """Planner Agent: Decomposes the query into sub-tasks."""
        prompt = f"Decompose this research query into 3 specific sub-questions: {self.query}"
        plan_text = await self.provider.generate_text(
            prompt, 
            system_prompt="You are the Lead Strategist for Hexamind Aurora. Break complex queries into clear, searchable sub-goals. Output only the questions, one per line."
        )
        
        # Validation
        if "Inference Error" in plan_text or not plan_text.strip():
            self.context["plan"] = plan_text
            return False
            
        self.context["plan"] = plan_text
        logger.info(f"Plan generated: {plan_text}")
        return True


    async def _search_phase(self):
        """Researcher Agent: Fetches data for each sub-goal."""
        logger.info("Starting Research Phase...")
        plan_lines = [line.strip() for line in self.context["plan"].split("\n") if "?" in line or line.startswith("-")]
        
        search_tasks = []
        for line in plan_lines[:3]: # Limit to top 3 sub-questions
            sub_query = line.strip("- ").strip()
            if sub_query:
                search_tasks.append(self._run_sub_research(sub_query))
        
        results = await asyncio.gather(*search_tasks)
        for sub_query, context in results:
            self.context["sources"].extend(context.sources)
            self.context["sub_answers"][sub_query] = [s.snippet for s in context.sources[:3]]
            
        logger.info(f"Research complete. Found {len(self.context['sources'])} total sources.")

    async def _run_sub_research(self, sub_query: str):
        """Helper to run research for a specific sub-query."""
        logger.info(f"Searching for: {sub_query}")
        context = await self.researcher.research(sub_query)
        return sub_query, context

    async def _analyze_phase(self):
        """Analyst Agent: Synthesizes research into a draft."""
        context_str = json.dumps(self.context["sub_answers"], indent=2)
        prompt = (
            f"Synthesize this research into a professional draft for: {self.query}\n\n"
            f"Evidence Context:\n{context_str}\n\n"
            "Requirements:\n"
            "1. Use direct citations from the evidence.\n"
            "2. Identify technical mechanisms and historical context.\n"
            "3. Be objective and factual."
        )
        draft = await self.provider.generate_text(
            prompt,
            system_prompt="You are a Lead Research Scientist. Ground every claim in the provided evidence. If evidence is missing, state it explicitly."
        )
        self.context["draft"] = draft
        logger.info("Draft analysis complete.")

    async def _critique_phase(self):
        """Critique Agent: Hunts for gaps and contradictions."""
        prompt = (
            f"Act as a skeptical reviewer for this research draft:\n{self.context['draft']}\n\n"
            "Compare it against the raw evidence context:\n"
            f"{json.dumps(self.context['sub_answers'], indent=2)}\n\n"
            "Tasks:\n"
            "1. List 3 specific logical gaps or missing citations.\n"
            "2. Identify any claims that go beyond the evidence.\n"
            "3. Suggest 1 additional search query if needed."
        )
        critique = await self.provider.generate_text(
            prompt,
            system_prompt="You are a Senior Peer Reviewer. Your goal is to ensure scientific rigor and eliminate hallucinations."
        )
        self.context["critique"] = critique
        logger.info("Critique phase complete.")

    async def _finalize_phase(self):
        """Synthesizer: Produces the final polished report."""
        prompt = (
            "You are the Editor-in-Chief. Synthesize the final research report for the user query.\n\n"
            f"Original Query: {self.query}\n\n"
            f"Research Draft: {self.context['draft']}\n\n"
            f"Peer Review Feedback (To Address): {self.context['critique']}\n\n"
            "Style Guide:\n"
            "1. Start with a Executive Summary.\n"
            "2. Use Markdown headings (##, ###).\n"
            "3. Include a 'Verification & Gaps' section addressing the critique.\n"
            "4. Add a References section listing the source titles and URLs."
        )
        final_report = await self.provider.generate_text(
            prompt,
            system_prompt="You are a High-Precision Synthesis Agent. Your output must be the gold standard of research reports."
        )
        return final_report
