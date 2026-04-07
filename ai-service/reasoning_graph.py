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
        print(f"🛰️  Orchestrator starting for query: {self.query}", flush=True)
        
        # Initialize with a basic plan in case of catastrophic failure
        self.task_tree = [
            HierarchicalNode(id="researcher_1", topic=f"General research on {self.query}", role="researcher")
        ]
        
        success = await self._plan_phase()
        print(f"🛰️  Orchestrator finished. Success: {success}, Tasks: {len(self.task_tree)}", flush=True)
        
        if not success or not self.task_tree:
            yield self._event(PipelineEventType.PIPELINE_ERROR, "orchestrator", "Failed to generate research plan.")
            return
        yield self._event(PipelineEventType.AGENT_DONE, "orchestrator", f"Decomposed into {len(self.task_tree)} specialized tasks.")

        # 2. HIERARCHICAL EXECUTION (Workers)
        semaphore = asyncio.Semaphore(1) # Limit to 1 for maximum stability on CPU
        
        async def run_worker_task(node: HierarchicalNode):
            async with semaphore:
                print(f"🔧 Starting worker task: {node.id} ({node.role}) - Topic: {node.topic}", flush=True)
                heartbeat_task = asyncio.create_task(self._emit_heartbeat(node.id))
                
                try:
                    yield self._event(PipelineEventType.AGENT_START, node.id)
                    worker = ResearchWorker(node.role, self.provider)
                    result = await worker.run(node.topic, context=self.query)
                    node.analysis = result["analysis"]
                    node.sources = result["sources"]
                    node.status = NodeStatus.COMPLETED
                    yield self._event(PipelineEventType.AGENT_DONE, node.id, node.analysis)
                except Exception as e:
                    print(f"❌ Worker {node.id} failed: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    node.status = NodeStatus.FAILED
                finally:
                    heartbeat_task.cancel()
                    print(f"✅ Worker task {node.id} finished.", flush=True)

        # Execute all nodes in the tree
        for node in self.task_tree:
            async for event_item in run_worker_task(node):
                yield event_item




        # 3. FINAL SYNTHESIS
        yield self._event(PipelineEventType.AGENT_START, "synthesizer")
        final_report = await self._finalize_phase()
        yield self._event(PipelineEventType.AGENT_DONE, "synthesizer", final_report)
        
        yield self._event(PipelineEventType.PIPELINE_DONE, "output", final_report)

    async def _emit_heartbeat(self, agent_id: str):
        """Sends a periodic 'Thinking' signal to prevent SSE timeouts."""
        while True:
            await asyncio.sleep(15)
            logger.debug(f"Heartbeat: {agent_id} is still thinking...")

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
        """Orchestrator: Bypasses model call and uses Diamond Experts (v6.0)."""
        # DIAMOND EXPERT ARCHITECTURE (v6.0)
        # We bypass the model-driven planning to save the 20-minute CPU timeout.
        # This manually authors the 4 specialist experts that ensure a high-fidelity report.
        self.task_tree = [
            HierarchicalNode(id="historian", topic=f"The historical evolution and pedagogy of {self.query}", role="historian"),
            HierarchicalNode(id="researcher", topic=f"Current evidence and case studies on {self.query}", role="researcher"),
            HierarchicalNode(id="auditor", topic=f"Critical assessment, gaps, and educator challenges for {self.query}", role="auditor"),
            HierarchicalNode(id="analyst", topic=f"Implementation strategies and practical outcomes for {self.query}", role="analyst")
        ]
        
        logger.info(f"Diamond Experts initialized. Bypassing planner.")
        return True






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
            "4. Add a References section with all unique URLs.\n\n"
            "CRITICAL: Be concise. Direct synthesis only. No conversational filler."
        )

        return await self.provider.generate_text(
            prompt,
            system_prompt="You are a High-Precision Synthesis Agent. Your output must be the gold standard of integrated research."
        )




