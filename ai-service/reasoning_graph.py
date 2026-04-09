import asyncio
import json
import logging
import re
import random
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

def update_research_status(content: str, mode: str = "a"):
    """Helper to maintain the live dashboard with fault tolerance."""
    try:
        status_path = Path(__file__).resolve().parent.parent / "research_status.md"
        with open(status_path, mode, encoding="utf-8") as f:
            f.write(content + "\n")
    except Exception as e:
        logger.warning(f"Failed to update research_status.md: {e}")

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
    max_sources: int = 20  # Strategic source allocation per node (set by _allocate_sources_per_node)


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

    def _outline_context(self) -> str:
        """Render the current report outline for use as a soft guardrail in prompts."""
        if not self.task_tree:
            return f"1. Core scope and framing for {self.query}"

        lines: list[str] = []

        def walk(nodes: List[TaxonomyNode], prefix: str = "") -> None:
            for index, node in enumerate(nodes, start=1):
                label = f"{prefix}{index}" if prefix else str(index)
                lines.append(f"{label}. {node.topic}")
                if node.children:
                    walk(node.children, f"{label}.")

        walk(self.task_tree)
        return "\n".join(lines)

    def _fallback_outline(self) -> List[TaxonomyNode]:
        topic = self.query.strip()
        return [
            TaxonomyNode(id="scope", topic=f"Scope and framing of {topic}", role="researcher"),
            TaxonomyNode(id="evidence", topic=f"Current evidence and landscape for {topic}", role="researcher"),
            TaxonomyNode(id="history", topic=f"Historical and policy context for {topic}", role="historian"),
            TaxonomyNode(id="dimensions", topic=f"Key dimensions and subtopics in {topic}", role="researcher"),
            TaxonomyNode(id="risks", topic=f"Constraints and risks in {topic}", role="auditor"),
            TaxonomyNode(id="implementation", topic=f"Implementation pathways for {topic}", role="analyst"),
        ]

    @staticmethod
    def _is_generic_outline(node: TaxonomyNode) -> bool:
        generic_topics = {
            "introduction",
            "methodology",
            "data sources",
            "analysis framework",
            "results and interpretation",
            "results",
            "conclusion",
            "research query",
            "report outline",
            "executive summary",
        }
        topic = node.topic.strip().lower()
        if topic in generic_topics:
            return True
        if len(node.children) == 0:
            return False
        child_topics = {child.topic.strip().lower() for child in node.children}
        return bool(child_topics & generic_topics)
    
    def _count_taxonomy_nodes(self, nodes: List[TaxonomyNode]) -> int:
        """Count total nodes in taxonomy tree (depth-first)."""
        count = 0
        for node in nodes:
            count += 1 + self._count_taxonomy_nodes(node.children)
        return count
    
    def _allocate_sources_per_node(self, nodes: List[TaxonomyNode], total_sources: int = 40):
        """
        Strategically allocate source budget across taxonomy nodes.
        Root nodes research broadly (full budget), children are per-category capped.
        """
        def assign_node_budget(node: TaxonomyNode, depth: int = 0):
            # Root nodes: get full budget for global baseline coverage
            if depth == 0:
                node.max_sources = total_sources
            # Child nodes: smaller budget to ensure diversity across branches
            else:
                node.max_sources = max(8, total_sources // max(1, (depth + 1)))
            
            for child in node.children:
                assign_node_budget(child, depth + 1)
        
        for root_node in nodes:
            assign_node_budget(root_node)

    def _event(self, event_type: PipelineEventType, agent_id: str, content: str = "") -> dict[str, str]:
        """Return a standard SSE message event with typed JSON payload."""
        event_obj = PipelineEvent(
            type=event_type,
            agentId=agent_id,
            fullContent=content,
        )
        return {"data": event_obj.model_dump_json()}

    async def generate_proposal(self) -> List[TaxonomyNode]:
        """Generate a proposed research plan for external review."""
        await self._plan_phase()
        return self.task_tree

    async def _plan_phase(self) -> bool:
        """Orchestrator: Generates a nested Taxonomic Tree tailored to the specific query."""
        print(f"🛰️  Orchestrator: Constructing Strategic Research Taxonomy...", flush=True)
        
        prompt = (
            f"You are the Lead Strategist. Decompose the following research query into a hierarchical report outline with 6-10 main report points, plus sub-sections where helpful.\n"
            f"Query: {self.query}\n\n"
            "Requirements:\n"
            "1. Output ONLY a JSON object representing the root of the report outline.\n"
            "2. Format: {\"id\": \"root_id\", \"topic\": \"main report frame\", \"role\": \"researcher\", \"children\": [{\"id\": \"child_id\", \"topic\": \"report point\", \"role\": \"historian\"}]}\n"
            "3. Roles are internal guidance only: researcher, historian, auditor, analyst.\n"
            "4. Prefer 6-10 top-level report points by default. Use sub-sections only when they add coverage or clarity.\n"
            "5. Keep the outline broad enough to cover all meaningful aspects of the query, but do not force irrelevant branches."
        )

        try:
            orch_config = get_agent_model_config("orchestrator")
            orch_provider = InferenceProvider(model_name=orch_config.primary_ollama_model)
            response = await orch_provider.generate_text(prompt, system_prompt="You are a High-Precision Taxonomy Architect. Output ONLY JSON.", max_tokens=orch_config.max_tokens)
            
            # More aggressive JSON extraction: find the first { and last }
            match = re.search(r'(\{.*\})', response, re.DOTALL)
            if match:
                clean_json = match.group(1)
            else:
                # Fallback to the old method if the regex fails
                clean_json = re.sub(r"```json\s*|\s*```", "", response.strip())
            
            task_data = json.loads(clean_json)
            
            def parse_recursive(node_data: Dict[str, Any], parent_id: Optional[str] = None) -> TaxonomyNode:
                # Structure Guard: Ensure minimum fields exist
                node_id = node_data.get("id", f"node_{random.randint(1000, 9999)}")
                topic = node_data.get("topic", "Target Investigation")
                role = str(node_data.get("role", "researcher")).strip().lower()
                
                # Sanitize roles to allowed set
                allowed_roles = {"researcher", "historian", "auditor", "analyst"}
                if role not in allowed_roles:
                    role = "researcher"

                node = TaxonomyNode(
                    id=node_id,
                    topic=topic,
                    role=role,
                    parent_id=parent_id
                )
                if "children" in node_data and isinstance(node_data["children"], list):
                    for child_data in node_data["children"]:
                        if isinstance(child_data, dict):
                            node.children.append(parse_recursive(child_data, node.id))
                return node

            root_node = parse_recursive(task_data)
            
            # Taxonomy Pruning: remove exact sibling duplicates and only prune ancestry duplicates
            # when both topic and role repeat (preserves multi-lens analysis quality).
            def _norm_topic(topic: str) -> str:
                return re.sub(r"\s+", " ", topic.strip().lower())

            def prune_duplicate_nodes(node: TaxonomyNode, ancestry_signatures: set[tuple[str, str]]):
                sibling_signatures: set[tuple[str, str]] = set()
                unique_children = []
                for child in node.children:
                    signature = (_norm_topic(child.topic), child.role.strip().lower())

                    # Hard dedupe exact sibling repeats.
                    if signature in sibling_signatures:
                        continue
                    sibling_signatures.add(signature)

                    # Selective ancestry dedupe: remove only if topic+role already occurred in lineage.
                    if signature in ancestry_signatures:
                        continue

                    unique_children.append(child)
                    prune_duplicate_nodes(child, ancestry_signatures | {signature})
                node.children = unique_children

            root_signature = (_norm_topic(root_node.topic), root_node.role.strip().lower())
            prune_duplicate_nodes(root_node, {root_signature})
            if self._is_generic_outline(root_node) or len(root_node.children) < 2:
                logger.warning("Planner returned a generic outline; using query-specific fallback outline.")
                self.task_tree = self._fallback_outline()
            else:
                self.task_tree = [root_node]
            logger.info("Taxonomic Architecture initialized and pruned.")
            return True
        except Exception as e:
            logger.error(f"Taxonomic planning failed: {e}. Falling back to Diamond Experts.")
            self.task_tree = self._fallback_outline()
            return True

    async def run(self):
        """Execute the hierarchical taxonomy research with Sequential Discovery."""
        from worker_agents import DistillationWorker, AnchorWorker
        logger.info(f"Starting Aurora v8.5+ Sequential Discovery for: {self.query}")
        
        # 1. PLAN
        update_research_status(f"🚀 [AURORA v8.5] Initiating Sequential Discovery...\nTarget: {self.query}\n{'-'*50}\n", mode="w")
        yield self._event(PipelineEventType.AGENT_START, "orchestrator")
        if not self.task_tree:
            await self._plan_phase()
        # Allocate source budget per node for strategic coverage (broad vs deep)
        self._allocate_sources_per_node(self.task_tree)
        update_research_status(f"✅ Taxonomy Optimized. {len(self.task_tree)} Root Chapters established.\n")
        yield self._event(PipelineEventType.AGENT_DONE, "orchestrator", "Taxonomy constructed.")

        # 2. GLOBAL BASELINE
        print("🌍 Establishing Global Baseline Anchors...", flush=True)
        update_research_status("🌍 Establishing Global Baseline Anchors...")
        baseline_worker = ResearchWorker("researcher")
        outline_context = self._outline_context()
        baseline_context = await baseline_worker.gather_evidence(self.query, outline_context=outline_context)
        distiller = DistillationWorker()
        distilled_facts = await distiller.distill("Global Overview", [s.snippet for s in baseline_context.sources[:15]])
        anchor_worker = AnchorWorker()
        global_anchors = await anchor_worker.extract(self.query, distilled_facts)
        update_research_status(f"⚓ Synthesized {len(global_anchors)} Global Context Anchors.\n")

        # 3. RECURSIVE DISCOVERY
        async def execute_node_recursive(node: TaxonomyNode, parent_analysis: str = ""):
            print(f"🔍 [DISCOVERY] Entering: {node.topic}", flush=True)
            update_research_status(f"🔍 [DISCOVERY] Investigating: {node.topic} ({node.role.upper()})...")
            yield self._event(PipelineEventType.AGENT_START, node.id)
            
            agent_config = get_agent_model_config(node.role)
            worker = ResearchWorker(node.role, InferenceProvider(model_name=agent_config.primary_ollama_model))
            
            # Context-Aware Foraging
            evidence = await worker.gather_evidence(
                node.topic,
                parent_context=parent_analysis,
                max_sources=node.max_sources,
                outline_context=outline_context,
            )
            result = await worker.run_analysis(
                node.topic,
                evidence,
                context=parent_analysis,
                anchors=global_anchors,
                outline_context=outline_context,
            )
            
            node.analysis = result.get("analysis", "")
            node.status = NodeStatus.COMPLETED
            
            update_research_status(f"✅ Node Complete: {node.topic}\n📄 Summary: {node.analysis[:200]}...\n")
            yield self._event(PipelineEventType.AGENT_DONE, node.id, f"Completed: {node.topic}")

            for child in node.children:
                async for event in execute_node_recursive(child, parent_analysis=node.analysis):
                    yield event

        for root_node in self.task_tree:
            async for event in execute_node_recursive(root_node):
                yield event

        # 4. SYNTHESIS
        print("🏗️  Master Synthesis starting...", flush=True)
        update_research_status("🏗️  Final Synthesis: Compiling Sequential Taxonomy into Strategic Report...")
        def compile_report(node: TaxonomyNode, indent_level: int = 1) -> str:
            # Clean node analysis of any existing headers that might cause level explosions
            clean_analysis = re.sub(r'^#+\s+', '', node.analysis or "", flags=re.MULTILINE).strip()
            hashes = "#" * (indent_level + 1)
            report_segment = f"{hashes} {node.topic}\n\n{clean_analysis}\n\n"
            for child in node.children:
                report_segment += compile_report(child, indent_level + 1)
            return report_segment

        body = "".join([compile_report(n) for n in self.task_tree])
        
        # Use Config-driven Synthesiser (prevents hardcoded 7B stalls on 2 cores)
        synth_config = get_agent_model_config("synthesiser")
        synth_provider = InferenceProvider(model_name=synth_config.primary_ollama_model)
        
        final_report = await synth_provider.generate_text(
            f"Synthesize the following Strategic Taxonomy for: {self.query}\n\n{body}\n\n"
            f"Report Outline to follow (soft guardrail, not rigid):\n{outline_context}\n\n"
            "Task: You are the Lead Synthesis Architect. Your goal is to create a COHERENT, NON-REPETITIVE intelligence report.\n"
            "1. Deduplicate information across all chapters.\n"
            "2. Ensure smooth logical transitions between sections.\n"
            "3. If multiple sections discuss the same thing, merge them into the most relevant heading.\n"
            "4. Maintain a formal, high-fidelity business intelligence lexicon.\n"
            "5. Output the COMPLETE polished Markdown report.",
            system_prompt="You are a High-Precision Synthesis Agent. FLAWLESS deduplication is mandatory.",
            max_tokens=2500
        )
        
        def titleize(q: str) -> str:
            q_clean = re.sub(r'^(is|what|how|why|does|do|can|will|should)\s+', '', q, flags=re.IGNORECASE)
            words = [w.capitalize() for w in re.findall(r'\w+', q_clean)]
            return "_".join(words[:5]) or "General_Research"

        # Only write to wiki if the output is not JSON (diffs array)
        def is_probably_json(text: str) -> bool:
            t = text.strip()
            return t.startswith('{') or t.startswith('[')

        wiki_dir = Path(__file__).resolve().parent.parent / "data" / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        title = titleize(self.query)
        file_path = wiki_dir / f"{title}.md"
        # Only write if not JSON
        if not is_probably_json(final_report):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_report)
            print(f"💾 Report saved to: {file_path}", flush=True)
        else:
            print(f"⚠️  Skipped writing non-Markdown output to wiki: {file_path}", flush=True)

        yield self._event(PipelineEventType.PIPELINE_DONE, "output", final_report)
