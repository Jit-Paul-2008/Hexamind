import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from pathlib import Path

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
    
    def __init__(self, query: str, aga_mode: bool = False, math_mode: bool = False, task_tree: Optional[List[HierarchicalNode]] = None):
        self.query = query
        self.aga_mode = aga_mode
        self.math_mode = math_mode
        self.task_tree: List[HierarchicalNode] = task_tree or []
        self.context: Dict[str, Any] = {"query": query}
        self.provider = get_provider()
        self.researcher = InternetResearcher()
        self.initial_draft: str = ""


    async def generate_proposal(self) -> List[HierarchicalNode]:
        """Generate a proposed research plan for external review."""
        await self._plan_phase()
        return self.task_tree

    async def run(self):
        """Execute the hierarchical research graph and yield events."""
        from worker_agents import DraftingWorker
        logger.info(f"Starting Aurora v5 ADD Graph for: {self.query}")
        
        # 1. PLAN (Orchestration)
        yield self._event(PipelineEventType.AGENT_START, "orchestrator")
        print(f"🛰️  Orchestrator starting for query: {self.query}", flush=True)
        
        # Initialize with a basic plan if no tree was provided
        if not self.task_tree:
            self.task_tree = [
                HierarchicalNode(id="researcher_1", topic=f"General research on {self.query}", role="researcher")
            ]
            
            success = await self._plan_phase()
            print(f"🛰️  Orchestrator finished. Success: {success}, Tasks: {len(self.task_tree)}", flush=True)
        else:
            print(f"🛰️  Using injected Strategic Roadmap: {len(self.task_tree)} manual tasks.", flush=True)
            success = True
        
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

        # 2.4 MEMORY RECALL (Checking for existing knowledge)
        def titleize(q: str) -> str:
            import re
            q = re.sub(r'^(is|what|how|why|does|do|can|will|should)\s+', '', q, flags=re.IGNORECASE)
            words = [w.capitalize() for w in re.findall(r'\w+', q)]
            return "_".join(words[:5]) or "General_Research"

        wiki_dir = Path(__file__).resolve().parent.parent / "data" / "wiki"
        wiki_path = wiki_dir / f"{titleize(self.query)}.md"
        
        existing_wiki = None
        if wiki_path.exists():
            print(f"📖 [MEMORY] Existing Wiki found for '{self.query}'. Recaling knowledge...")
            try:
                with open(wiki_path, "r", encoding="utf-8") as f:
                    existing_wiki = f.read()
            except Exception as e:
                logger.error(f"Failed to read wiki memory: {e}")

        # 2.45 ATOMIC DISTILLATION SWARM (ADS) Phase
        # PILLAR 11: Distill 100+ sources into high-fidelity Fact Ledger
        print("🍯 [ADS] Launching Distillation Swarm for 100+ sources...", flush=True)
        from worker_agents import DistillationWorker, AnchorWorker
        distiller = DistillationWorker()
        
        distillation_tasks = []
        for node_id, ctx in node_contexts.items():
            # Parallelize distillation of snippets (max 20 per expert for speed)
            snippets = [s.snippet for s in ctx.sources[:20]]
            distillation_tasks.append(distiller.distill(node_id, snippets))
            
        distilled_results = await asyncio.gather(*distillation_tasks)
        fact_ledger = []
        for res in distilled_results:
            fact_ledger.extend(res)
            
        print(f"🍯 [ADS] Distilled {len(fact_ledger)} atomic facts from raw evidence pool.", flush=True)

        # 2.46 FACT-ANCHOR EXTRACTION
        anchors = None
        if self.aga_mode or True: # Always use anchors in v8.0 ADS
            print("⚓ Synthesizing Strategic Grounding Anchors...", flush=True)
            anchor_config = get_agent_model_config("anchor_worker")
            anchor_provider = InferenceProvider(model_name=anchor_config.primary_ollama_model)
            anchor_worker = AnchorWorker(anchor_provider)
            anchors = await anchor_worker.extract(self.query, fact_ledger, existing_wiki=existing_wiki)
            print(f"⚓ Extracted {len(anchors)} high-fidelity Grounding Anchors.", flush=True)

        # 2.48 MATH ENGINE SIMULATION (Optional Math Mode)
        if self.math_mode:
            print("🧮 Running Quantitative Math Engine Simulation...", flush=True)
            from simulation_engine import SimulationWorker
            sim_config = get_agent_model_config("drafter") # 7B model is best for coding math
            sim_provider = InferenceProvider(model_name=sim_config.primary_ollama_model)
            sim_worker = SimulationWorker(sim_provider)
            chart_data = await sim_worker.simulate(self.query, list(node_contexts.values()))
            if chart_data:
                print(f"🧮 Successfully simulated math logic. Emitting chart data.", flush=True)
                yield self._event(PipelineEventType.AGENT_CHUNK, "drafter", f"\n[CHART_DATA]{json.dumps(chart_data)}[/CHART_DATA]\n")
            else:
                print(f"🧮 Simulation failed to produce valid chart JSON.", flush=True)

        # 2.5 DRAFTING PHASE
        if self.aga_mode:
            print("📝 Assembling Wiki Draft via constraint logic...", flush=True)
        else:
            print("📝 Generating Wiki Draft/Update...", flush=True)
            
        yield self._event(PipelineEventType.AGENT_START, "drafter")
        drafter_config = get_agent_model_config("drafter")
        drafter_provider = InferenceProvider(model_name=drafter_config.primary_ollama_model)
        drafter = DraftingWorker(drafter_provider)
        self.initial_draft = await drafter.draft(self.query, list(node_contexts.values()), existing_wiki=existing_wiki, anchors=anchors)
        
        # PILLAR 11: Iterative Depth Scaling
        # If the draft is suspiciously short (< 300 chars) for a complex topic, perform one recursive deep-dive
        if len(self.initial_draft) < 300 and not self.math_mode:
            print("🔍 [DEPTH SCALING] Draft too thin. Spawning recursive deep-dive...", flush=True)
            yield self._event(PipelineEventType.AGENT_START, "researcher", "Re-searching for more granular evidence...")
            deep_context = await workers["researcher_1" if "researcher_1" in workers else self.task_tree[0].id].gather_evidence(f"extremely specific details and niche data on {self.query}")
            node_contexts[self.task_tree[0].id] = deep_context
            self.initial_draft = await drafter.draft(self.query, list(node_contexts.values()), existing_wiki=existing_wiki, anchors=anchors)
            print("🔍 [DEPTH SCALING] Recursive pass complete.", flush=True)

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
                    
                    # Pass the anchors to the Auditor or any worker that uses them
                    result = await worker.run_analysis(node.topic, context, self.query, self.initial_draft, anchors=anchors)
                    node.diffs = result["diffs"]
                    node.analysis = result.get("analysis", "Review complete.")
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

        # PHASE 3: CONFLICT RESOLUTION (Dynamic Swarm Adaptation)
        contradictory_nodes = [n for n in self.task_tree if n.status == NodeStatus.COMPLETED and "contradiction" in (n.analysis or "").lower()]
        if contradictory_nodes:
            print(f"⚖️  Conflict Detected. Spawning Resolver node...", flush=True)
            yield self._event(PipelineEventType.AGENT_START, "resolver", "Adjudicating contradictory expert findings...")
            
            resolver_topic = "Reconcile the following expert contradictions: " + " | ".join([f"[{n.id}] {n.analysis}" for n in contradictory_nodes])
            resolver_worker = ResearchWorker("auditor") # Use Auditor persona for adjudication
            
            # The resolver acts as an editor on the accumulated context
            result = await resolver_worker.run_analysis(resolver_topic, node_contexts[self.task_tree[0].id], self.query, self.initial_draft, anchors=anchors)
            
            # Integrate resolver findings
            resolver_node = HierarchicalNode(id="resolver", topic=resolver_topic, role="auditor", status=NodeStatus.COMPLETED, analysis=result.get("analysis", ""))
            resolver_node.diffs = result["diffs"]
            self.task_tree.append(resolver_node)
            
            yield self._event(PipelineEventType.AGENT_DONE, "resolver", "Contradictions resolved and integrated into final synthesis.")

        # 4. FINAL ASSEMBLY & DUAL SYNTHESIS
        print("🏗️ Assembling final report and integrating tradeoffs...", flush=True)
        yield self._event(PipelineEventType.AGENT_START, "synthesiser", "Synthesizing technical assessment and user-facing report...")
        
        # We first apply the diffs to ensure the synthesiser gets the most accurate technical data
        assembled_context = self.initial_draft
        for node in self.task_tree:
            if node.status == NodeStatus.COMPLETED and node.diffs:
                for diff in node.diffs:
                    original = diff.get("original_text_snippet", "")
                    replacement = diff.get("replacement_text", "")
                    if original and replacement and original in assembled_context:
                        assembled_context = assembled_context.replace(original, replacement)
        
        # update context for synthesiser
        self.initial_draft = assembled_context
        
        # Call the high-precision synthesiser for the dual output
        final_dual_report = await self._finalize_phase()
        
        print(f"✅ Synthesis complete. Emitting dual-structured report.", flush=True)
        yield self._event(PipelineEventType.AGENT_DONE, "synthesiser", "Technical and Research reports successfully synthesized.")
        
        yield self._event(PipelineEventType.PIPELINE_DONE, "output", final_dual_report)

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
        """Orchestrator: Generates a dynamic research plan tailored to the specific query."""
        print(f"🛰️  Orchestrator: Analyzing query complexity and defining expert swarm...", flush=True)
        
        prompt = (
            f"You are the Lead Strategist. Decompose the following research query into 4-6 specialized expert tasks.\n"
            f"Query: {self.query}\n\n"
            "Requirements:\n"
            "1. Output ONLY a JSON array of objects.\n"
            "2. Format: [{\"id\": \"expert_id\", \"topic\": \"specific sub-topic to research\", \"role\": \"historian|researcher|auditor|analyst\"}]\n"
            "3. Roles must be one of: historian, researcher, auditor, analyst.\n"
            "4. Match experts to the niche requirements of the query (e.g., use a 'Legal Analyst' for regulation, 'Technical Auditor' for code)."
        )

        try:
            orch_config = get_agent_model_config("orchestrator")
            orch_provider = InferenceProvider(model_name=orch_config.primary_ollama_model)
            response = await orch_provider.generate_text(prompt, system_prompt="You are a High-Precision Logic Orchestrator. Output ONLY JSON.", max_tokens=500)
            
            import re
            clean_json = re.sub(r"```json\s*|\s*```", "", response.strip())
            task_data = json.loads(clean_json)
            
            self.task_tree = [
                HierarchicalNode(id=t["id"], topic=t["topic"], role=t["role"])
                for t in task_data
            ]
            logger.info(f"Dynamic Swarm initialized with {len(self.task_tree)} specialized experts.")
            return True
        except Exception as e:
            logger.error(f"Dynamic planning failed: {e}. Falling back to Diamond Experts.")
            # FALLBACK TO DIAMOND EXPERTS (v6.0)
            self.task_tree = [
                HierarchicalNode(id="historian", topic=f"Historical evolution of {self.query}", role="historian"),
                HierarchicalNode(id="researcher", topic=f"Current evidence on {self.query}", role="researcher"),
                HierarchicalNode(id="rival_analyst", topic=f"Competitive benchmarking for {self.query}", role="analyst"),
                HierarchicalNode(id="auditor", topic=f"Critical risks of {self.query}", role="auditor"),
                HierarchicalNode(id="analyst", topic=f"Future outcomes and TEI of {self.query}", role="analyst")
            ]
            return True






    async def _finalize_phase(self) -> str:
        """Synthesizer: Merges all hierarchical worker results."""
        worker_outputs = "\n\n".join([
            f"### Focus: {node.topic} ({node.role})\n{node.analysis}" 
            for node in self.task_tree if node.status == NodeStatus.COMPLETED
        ])
        
        # PILLAR 16: Metrics Integration
        metrics_summary = (
            f"### Session Metrics (API Equivalence):\n"
            f"- **Inbound Tokens**: {InferenceProvider.TOTAL_TOKENS_IN:,}\n"
            f"- **Outbound Tokens**: {InferenceProvider.TOTAL_TOKENS_OUT:,}\n"
            f"- **Total Multi-Agent API Calls**: {InferenceProvider.API_CALL_COUNT}\n"
            f"- **Estimated Model-as-a-Service Equivalent Cost**: ${((InferenceProvider.TOTAL_TOKENS_IN/1000000)*0.15 + (InferenceProvider.TOTAL_TOKENS_OUT/1000000)*0.60):.4f}"
        )

        prompt = (
            "You are the Editor-in-Chief and Strategic Partner at a top consulting firm. Synthesize the final multi-agent research report.\n\n"
            f"Original Query: {self.query}\n\n"
            f"Gathered Evidence & Expert Insights:\n{worker_outputs}\n\n"
            "CRITICAL: Produce TWO reports in this exact order and only with these top-level headings:\n"
            "1. '## Technical report': Must contain a concise executive summary, methods, evidence-backed findings, research quality stats, and source inventory.\n"
            f"   - **MANDATORY**: Include the following session metrics in this section:\n{metrics_summary}\n"
            "2. '## Strategic Executive Summary': Must be polished, human-readable, structured with clear subheadings, and focused on the user's query.\n\n"
            "Style Guide & PILLAR 1 (Multidimensional Reasoning):\n"
            "- For every major conclusion, you MUST TRIANGULATE between:\n"
            "  - ECONOMIC IMPACT: What is the TCO, ROI, or market value cost/benefit?\n"
            "  - PSYCHOLOGICAL ANCHOR: What human desire (status, safety, fear) drives this?\n"
            "  - STRUCTURAL RISK: What regulatory or network-effect barriers exist?\n"
            "- PILLAR 8 (Paradox Resolution): You MUST explicitly address any contradictions between expert rationales. "
            "If the Auditor reports risk but the Researcher reports success, bridge the discrepancy with a 'Reconciling the Discrepancy' section.\n"
            "- PILLAR 15 (Visual Logic): You MUST emit at least one MERMAID.JS diagram (flowchart or erDiagram) "
            "representing the core ecosystem or strategic funnel of the research topic.\n"
            "- Use concrete claims and [Sx] citations.\n"
            "- No conversational filler or meta-commentary.\n"
            "- Use authoritative, McKinsey-style terminology."
        )

        synth_config = get_agent_model_config("synthesiser")
        # Use 7B model for faster synthesis on CPU
        synth_provider = InferenceProvider(model_name="qwen2.5:7b")

        return await synth_provider.generate_text(
            prompt,
            system_prompt="You are a High-Precision Synthesis Agent. Your output must be the gold standard of integrated research.",
            max_tokens=1200
        )




