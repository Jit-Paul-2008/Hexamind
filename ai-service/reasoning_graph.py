import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from pathlib import Path

from inference_provider import get_provider, InferenceProvider
from research import InternetResearcher
from agent_model_config import get_agent_model_config
from worker_agents import ResearchWorker, WorkerRole
from schemas import PipelineEvent, PipelineEventType

logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TaxonomyNode:
    id: str
    topic: str
    role: str
    status: NodeStatus = NodeStatus.PENDING
    analysis: Optional[str] = None
    diffs: List[Dict[str, str]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    children: List['TaxonomyNode'] = field(default_factory=list)
    parent_id: Optional[str] = None


class AuroraGraph:
    """The central orchestration engine for Hexamind Aurora v8.5+ using Sequential Discovery."""
    
    def __init__(self, query: str, aga_mode: bool = False, math_mode: bool = False, task_tree: Optional[List[TaxonomyNode]] = None):
        self.query = query
        self.aga_mode = aga_mode
        self.math_mode = math_mode
        self.task_tree: List[TaxonomyNode] = task_tree or []
        self.context: Dict[str, Any] = {"query": query}
        self.provider = get_provider()
        self.researcher = InternetResearcher()
        self.initial_draft: str = ""

    def _event(self, event_type: PipelineEventType, agent_id: str, content: str = "") -> str:
        """Helper to format SSE events."""
        event_obj = {
            "type": event_type.value,
            "agentId": agent_id,
            "fullContent": content
        }
        return json.dumps({"data": json.dumps(event_obj)})

    async def generate_proposal(self) -> List[TaxonomyNode]:
        """Generate a proposed research plan for external review."""
        await self._plan_phase()
        return self.task_tree

    async def _plan_phase(self) -> bool:
        """Orchestrator: Generates a nested Taxonomic Tree tailored to the specific query."""
        print(f"🛰️  Orchestrator: Constructing Strategic Research Taxonomy...", flush=True)
        
        prompt = (
            f"You are the Lead Strategist. Decompose the following research query into a hierarchical Strategic Taxonomy (3-5 Chapters, with sub-sections for complex topics).\n"
            f"Query: {self.query}\n\n"
            "Requirements:\n"
            "1. Output ONLY a JSON object representing the root of the tree.\n"
            "2. Format: {\"id\": \"root_id\", \"topic\": \"topic\", \"role\": \"researcher\", \"children\": [{\"id\": \"child_id\", \"topic\": \"sub-topic\", \"role\": \"historian\"}]}\n"
            "3. Roles must be: researcher, historian, auditor, analyst.\n"
            "4. Match roles to sub-topics wisely. Keep depth to maximum 2-3 levels."
        )

        try:
            orch_config = get_agent_model_config("orchestrator")
            orch_provider = InferenceProvider(model_name=orch_config.primary_ollama_model)
            response = await orch_provider.generate_text(prompt, system_prompt="You are a High-Precision Taxonomy Architect. Output ONLY JSON.", max_tokens=1000)
            
            clean_json = re.sub(r"```json\s*|\s*```", "", response.strip())
            task_data = json.loads(clean_json)
            
            def parse_recursive(node_data: Dict[str, Any], parent_id: Optional[str] = None) -> TaxonomyNode:
                node = TaxonomyNode(
                    id=node_data["id"],
                    topic=node_data["topic"],
                    role=node_data["role"],
                    parent_id=parent_id
                )
                if "children" in node_data:
                    for child_data in node_data["children"]:
                        node.children.append(parse_recursive(child_data, node.id))
                return node

            root_node = parse_recursive(task_data)
            self.task_tree = [root_node]
            logger.info("Taxonomic Architecture initialized.")
            return True
        except Exception as e:
            logger.error(f"Taxonomic planning failed: {e}. Falling back to Diamond Experts.")
            self.task_tree = [
                TaxonomyNode(id="historian", topic=f"Historical evolution of {self.query}", role="historian"),
                TaxonomyNode(id="researcher", topic=f"Current evidence on {self.query}", role="researcher"),
                TaxonomyNode(id="auditor", topic=f"Critical risks of {self.query}", role="auditor"),
                TaxonomyNode(id="analyst", topic=f"Future outcomes of {self.query}", role="analyst")
            ]
            return True

    async def run(self):
        """Execute the hierarchical taxonomy research with Sequential Discovery."""
        from worker_agents import DistillationWorker, AnchorWorker
        logger.info(f"Starting Aurora v8.5+ Sequential Discovery for: {self.query}")
        
        # 1. PLAN
        yield self._event(PipelineEventType.AGENT_START, "orchestrator")
        if not self.task_tree:
            await self._plan_phase()
        yield self._event(PipelineEventType.AGENT_DONE, "orchestrator", "Taxonomy constructed.")

        # 2. GLOBAL BASELINE
        print("🌍 Establishing Global Baseline Anchors...", flush=True)
        baseline_worker = ResearchWorker("researcher")
        baseline_context = await baseline_worker.gather_evidence(self.query)
        distiller = DistillationWorker()
        distilled_facts = await distiller.distill("Global Overview", [s.snippet for s in baseline_context.sources[:15]])
        anchor_worker = AnchorWorker()
        global_anchors = await anchor_worker.extract(self.query, distilled_facts)

        # 3. RECURSIVE DISCOVERY
        async def execute_node_recursive(node: TaxonomyNode, parent_analysis: str = ""):
            print(f"🔍 [DISCOVERY] Entering: {node.topic}", flush=True)
            yield self._event(PipelineEventType.AGENT_START, node.id)
            
            agent_config = get_agent_model_config(node.role)
            worker = ResearchWorker(node.role, InferenceProvider(model_name=agent_config.primary_ollama_model))
            
            # Context-Aware Foraging
            evidence = await worker.gather_evidence(node.topic, parent_context=parent_analysis)
            result = await worker.run_analysis(node.topic, evidence, context=parent_analysis, anchors=global_anchors)
            
            node.analysis = result.get("analysis", "")
            node.status = NodeStatus.COMPLETED
            yield self._event(PipelineEventType.AGENT_DONE, node.id, f"Completed: {node.topic}")

            for child in node.children:
                async for event in execute_node_recursive(child, parent_analysis=node.analysis):
                    yield event

        for root_node in self.task_tree:
            async for event in execute_node_recursive(root_node):
                yield event

        # 4. SYNTHESIS
        print("🏗️  Master Synthesis starting...", flush=True)
        def compile_report(node: TaxonomyNode, indent_level: int = 1) -> str:
            hashes = "#" * (indent_level + 1)
            report_segment = f"{hashes} {node.topic}\n\n{node.analysis}\n\n"
            for child in node.children:
                report_segment += compile_report(child, indent_level + 1)
            return report_segment

        body = "".join([compile_report(n) for n in self.task_tree])
        synth_provider = InferenceProvider(model_name="qwen2.5:7b")
        final_report = await synth_provider.generate_text(
            f"Synthesize the following Strategic Taxonomy for: {self.query}\n\n{body}\n\n"
            "Task: Ensure a seamless 'discovery' flow. Output polished Markdown.",
            system_prompt="You are a High-Precision Synthesis Agent.",
            max_tokens=2000
        )
        
        def titleize(q: str) -> str:
            import re
            q = re.sub(r'^(is|what|how|why|does|do|can|will|should)\s+', '', q, flags=re.IGNORECASE)
            words = [w.capitalize() for w in re.findall(r'\w+', q)]
            return "_".join(words[:5]) or "General_Research"

        wiki_dir = Path(__file__).resolve().parent.parent / "data" / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        title = titleize(self.query)
        file_path = wiki_dir / f"{title}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_report)
        print(f"💾 Report saved to: {file_path}", flush=True)

        yield self._event(PipelineEventType.PIPELINE_DONE, "output", final_report)
