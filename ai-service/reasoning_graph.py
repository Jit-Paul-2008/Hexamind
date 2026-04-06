import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from inference_provider import get_provider
from research import InternetResearcher

from worker_agents import ResearchWorker, WorkerRole
from research import InternetResearcher

from schemas import PipelineEvent, PipelineEventType

logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class HierarchicalNode:
    id: str
    topic: str
    role: str
    status: NodeStatus = NodeStatus.PENDING
    analysis: Optional[str] = None
    sources: List[str] = field(default_factory=list)


class AuroraGraph:
    """The central orchestration engine for Hexamind Aurora."""
    
    def __init__(self, query: str):
        self.query = query
        self.task_tree: List[HierarchicalNode] = []
        self.context: Dict[str, Any] = {"query": query}
        self.provider = get_provider()
        self.researcher = InternetResearcher()


    async def run(self):
        """Execute the hierarchical research graph and yield events."""
        logger.info(f"Starting Aurora v5 Hierarchical Graph for: {self.query}")
        
        # 1. PLAN (Orchestration)
        yield self._event(PipelineEventType.AGENT_START, "orchestrator")
        success = await self._plan_phase()
        if not success:
            yield self._event(PipelineEventType.PIPELINE_ERROR, "orchestrator", "Failed to generate research plan.")
            return
        yield self._event(PipelineEventType.AGENT_DONE, "orchestrator", f"Decomposed into {len(self.task_tree)} specialized tasks.")

        # 2. HIERARCHICAL EXECUTION (Workers)
        semaphore = asyncio.Semaphore(2) # Limit concurrency for CPUs
        
        async def run_worker_task(node: HierarchicalNode):
            async with semaphore:
                # Emit a periodic 'Thinking' heartbeat to keep the SSE connection alive
                # while the 14B model is processing.
                heartbeat_task = asyncio.create_task(self._emit_heartbeat(node.id))
                
                try:
                    yield self._event(PipelineEventType.AGENT_START, node.id)
                    worker = ResearchWorker(node.role, self.provider)
                    result = await worker.run(node.topic, context=self.query)
                    node.analysis = result["analysis"]
                    node.sources = result["sources"]
                    node.status = NodeStatus.COMPLETED
                    yield self._event(PipelineEventType.AGENT_DONE, node.id, node.analysis)
                finally:
                    heartbeat_task.cancel()

    async def _emit_heartbeat(self, agent_id: str):
        """Sends a periodic 'Thinking' signal to prevent SSE timeouts."""
        while True:
            await asyncio.sleep(15)
            # We don't yield here directly since this is a background task, 
            # but we can log or trigger a state update if needed.
            logger.debug(f"Heartbeat: {agent_id} is still thinking...")


        # Execute all nodes in the tree
        worker_coroutines = [run_worker_task(node) for node in self.task_tree]
        # We need to handle yielding from the worker coroutines correctly
        for coro in worker_coroutines:
            async for event_item in coro:
                yield event_item

        # 3. FINAL SYNTHESIS
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
        """Orchestrator: Decomposes the research into a JSON task tree."""
        system_prompt = (
            "You are the Lead Research Orchestrator for Hexamind Aurora. "
            "Decompose the user's query into a structured JSON research plan.\n"
            "Format: { \"tasks\": [ { \"id\": \"task1\", \"topic\": \"...\", \"role\": \"researcher|historian|auditor|analyst\" } ] }\n"
            "Generate as many specialized tasks as needed for exhaustive research. "
            "Roles: historian (past), researcher (current data), auditor (critique/gaps), analyst (technical/why)."
        )

        
        # Force a slightly more restrictive JSON format to help the model
        response = await self.provider.generate_text(
            f"Query: {self.query}\n\nDecompose this into a detailed JSON research plan with roles: historian, researcher, auditor, analyst.",
            system_prompt=system_prompt
        )
        
        try:
            # Extract JSON (handling markdown code blocks and model preamble)
            import re
            # Try to find the last markdown block first, then falling back to generic brace search
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if not json_match:
                json_match = re.search(r"(\{.*?\})", response, re.DOTALL)
            
            if not json_match:
                logger.warning(f"Plan format invalid. Model response: {response}")
                # Fallback: Generate a default 4-agent plan if the model confuses the format
                plan_data = {
                    "tasks": [
                        {"id": "t1", "topic": f"Historical background of {self.query}", "role": "historian"},
                        {"id": "t2", "topic": f"Current data on {self.query}", "role": "researcher"},
                        {"id": "t3", "topic": f"Critical assessment of {self.query}", "role": "auditor"},
                        {"id": "t4", "topic": f"Technical mechanisms of {self.query}", "role": "analyst"}
                    ]
                }
            else:
                json_str = json_match.group(1) if json_match.lastindex else json_match.group(0)
                plan_data = json.loads(json_str)
            
            tasks = plan_data.get("tasks", [])
            if not tasks:
                raise ValueError("Empty task list in plan.")

            for t in tasks:
                self.task_tree.append(HierarchicalNode(
                    id=t["id"],
                    topic=t["topic"],
                    role=t["role"]
                ))
            return True
        except Exception as e:
            logger.error(f"Planning failed: {e}. Raw Response: {response}")
            # Final safety fallback
            self.task_tree = [HierarchicalNode(id="fallback", topic=self.query, role="researcher")]
            return True # Proceed with at least one task



    async def _finalize_phase(self) -> str:
        """Synthesizer: Merges all hierarchical worker results."""
        worker_outputs = "\n\n".join([
            f"### Focus: {node.topic} ({node.role})\n{node.analysis}" 
            for node in self.task_tree if node.status == NodeStatus.COMPLETED
        ])
        
        prompt = (
            "You are the Editor-in-Chief. Synthesize the final multi-agent research report.\n\n"
            f"Original Query: {self.query}\n\n"
            f"Gathered Evidence:\n{worker_outputs}\n\n"
            "Style Guide:\n"
            "1. Start with a Executive Summary.\n"
            "2. Use Markdown headings (##).\n"
            "3. Add a unified 'Synthesis of Perspectives' section.\n"
            "4. Add a References section with all unique URLs."
        )
        return await self.provider.generate_text(
            prompt,
            system_prompt="You are a High-Precision Synthesis Agent. Your output must be the gold standard of integrated research."
        )




