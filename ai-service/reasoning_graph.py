import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from inference_provider import get_provider, InferenceProvider
from research import InternetResearcher
from agent_model_config import get_agent_model_config

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
    diffs: List[Dict[str, str]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)


class AuroraGraph:
    """The central orchestration engine for Hexamind Aurora."""
    
    def __init__(self, query: str):
        self.query = query
        self.task_tree: List[HierarchicalNode] = []
        self.context: Dict[str, Any] = {"query": query}
        self.provider = get_provider()
        self.researcher = InternetResearcher()
        self.initial_draft: str = ""


    async def run(self):
        """Execute the hierarchical research graph and yield events."""
        from worker_agents import DraftingWorker
        logger.info(f"Starting Aurora v5 ADD Graph for: {self.query}")
        
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

        # 2. PARALLEL EVIDENCE GATHERING
        print("🌍 Launching parallel web searches...", flush=True)
        yield self._event(PipelineEventType.AGENT_START, "orchestrator", "Fetching evidence in parallel...")
        
        workers = {}
        fetch_tasks = []
        for node in self.task_tree:
            agent_config = get_agent_model_config(node.role)
            worker_provider = InferenceProvider(model_name=agent_config.primary_ollama_model)
            worker = ResearchWorker(node.role, worker_provider)
            workers[node.id] = worker
            fetch_tasks.append(worker.gather_evidence(node.topic))
            
        contexts = await asyncio.gather(*fetch_tasks)
        node_contexts = {node.id: context for node, context in zip(self.task_tree, contexts)}

        # 2.5 FAST DRAFTING PHASE
        print("📝 Generating initial 0.5B draft...", flush=True)
        yield self._event(PipelineEventType.AGENT_START, "drafter")
        drafter_config = get_agent_model_config("drafter")
        drafter_provider = InferenceProvider(model_name=drafter_config.primary_ollama_model)
        drafter = DraftingWorker(drafter_provider)
        self.initial_draft = await drafter.draft(self.query, list(node_contexts.values()))
        yield self._event(PipelineEventType.AGENT_DONE, "drafter", self.initial_draft)

        # 3. HIERARCHICAL EXECUTION (Workers Inference as Editors)
        semaphore = asyncio.Semaphore(1) # Limit to 1 for maximum stability on CPU
        
        async def run_worker_task(node: HierarchicalNode):
            async with semaphore:
                print(f"🔧 Starting editorial worker task: {node.id} ({node.role})", flush=True)
                heartbeat_task = asyncio.create_task(self._emit_heartbeat(node.id))
                
                try:
                    yield self._event(PipelineEventType.AGENT_START, node.id)
                    worker = workers[node.id]
                    context = node_contexts[node.id]
                    result = await worker.run_analysis(node.topic, context, self.query, self.initial_draft)
                    node.diffs = result["diffs"]
                    node.sources = result["sources"]
                    node.status = NodeStatus.COMPLETED
                    yield self._event(PipelineEventType.AGENT_DONE, node.id, f"Editorial review complete. {len(node.diffs)} corrections identified.")
                except Exception as e:
                    print(f"❌ Worker {node.id} failed: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    node.status = NodeStatus.FAILED
                finally:
                    heartbeat_task.cancel()
                    print(f"✅ Worker task {node.id} finished.", flush=True)

        # Execute all editorial nodes sequentially
        for node in self.task_tree:
            async for event_item in run_worker_task(node):
                yield event_item

        # 4. FINAL ASSEMBLY (Assembler Logic)
        print("🏗️ Assembling final report from edits...", flush=True)
        yield self._event(PipelineEventType.AGENT_START, "assembler")
        
        final_report = self.initial_draft
        total_edits = 0
        for node in self.task_tree:
            if node.status == NodeStatus.COMPLETED and node.diffs:
                for diff in node.diffs:
                    original = diff.get("original_text_snippet", "")
                    replacement = diff.get("replacement_text", "")
                    if original and replacement and original in final_report:
                        final_report = final_report.replace(original, replacement)
                        total_edits += 1
        
        print(f"✅ Assembly complete. Applied {total_edits} corrections.", flush=True)
        yield self._event(PipelineEventType.AGENT_DONE, "assembler", final_report)
        
        yield self._event(PipelineEventType.PIPELINE_DONE, "output", final_report)

    async def _emit_heartbeat(self, agent_id: str):
        """Sends a periodic signal to console to show active thinking."""
        count = 1
        while True:
            await asyncio.sleep(20)
            print(f"⏳ [THINKING] {agent_id.upper()} has been deep-reasoning for {count * 20}s... (Step {count})", flush=True)
            count += 1

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
            "CRITICAL: Produce TWO reports in this exact order and only with these top-level headings:\n"
            "1. '## Technical report': Must contain a concise executive summary, methods, evidence-backed findings, research quality stats, and source inventory.\n"
            "2. '## Report on Topic': Must be polished, human-readable, structured with clear subheadings, and focused on the user's query.\n\n"
            "Style Guide:\n"
            "- Use concrete claims and [Sx] citations.\n"
            "- No conversational filler or meta-commentary.\n"
            "- Ground every insight in the provided evidence."
        )

        synth_config = get_agent_model_config("synthesiser")
        # Use 7B model for faster synthesis on CPU
        synth_provider = InferenceProvider(model_name="qwen2.5:7b")

        return await synth_provider.generate_text(
            prompt,
            system_prompt="You are a High-Precision Synthesis Agent. Your output must be the gold standard of integrated research.",
            max_tokens=1200
        )




