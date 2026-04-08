# Blueprint: Taxonomy-First Strategic Architecture (v8.5)
**Status**: Pre-Implementation Design | **Objective**: Hierarchical Cohesion

---

## 1. What to KEEP (v8.0 Foundation)
The following "Grit & Infrastructure" components are already industrial-grade and will be retained as-is:
- **ADS Logic (Atomic Distillation Swarm)**: The foraging swarm that condenses 100+ sources into the Fact Ledger.
- **Deep Paging Infrastructure**: The `research.py` logic that saturates the evidentiary pool.
- **Inference Metrics**: Global token tracking and API cost equivalence.
- **Anchor Logic**: The grounding system that prevents hallucinations via atomic anchors.

---

## 2. What to CHANGE (The Refactor)
These components require structural shifts to accommodate hierarchical planning:

### `reasoning_graph.py` (The Orchestration Engine)
- **Node Schema**: Refactor `HierarchicalNode` to include a `children: List[HierarchicalNode]` attribute.
- **The Orchestrator**: Update the Stage 0 planning prompt to generate a **Deeper Nested Taxonomy** (JSON Tree) rather than a flat list of experts.
- **Execution Flow**: Switch from "Parallel Specialist" execution to **"Recursive Depth execution."** Research will gather data for parent nodes and then trickle down refined context to sub-topics.

### `run_interactive.py` (The User Interface)
- **Tree Visualization**: Update the CLI to show an indented, professional tree structure.
- **Recursive Edits**: Implement commands to `branch [index]` (add a sub-topic) or `prune [index]` (remove a section and its children).

### `worker_agents.py` (The Experts)
- **Inherited Context**: Experts will no longer work in isolation. They will receive a "Parent Context Summary" to ensure the sub-topic research perfectly aligns with the master topic.

---

## 3. What to CREATE (The New Layer)

### `TaxonomyArchitect` (New Component)
A specialized agent task in `reasoning_graph.py` responsible solely for ADJUDICATING the flow between sections. It ensures that Section A flows logically into Section B before Section C is written.

### `MasterSequentialSynthesiser`
A new synthesis engine that takes the entire fulfilled Taxonomy Tree and compiles it into a single, high-fidelity **"Strategic Executive Intelligence"** document, with auto-generated table of contents and logical transitions.

---

## 🚀 Execution Strategy for Tomorrow
1.  **Refactor Schemas**: Implement the nested `TaxonomyNode`.
2.  **Upgrade Orchestrator**: Pivot from "Expert List" to "Taxonomic Tree" generation.
3.  **Enhance CLI**: Build the nested review loop.
4.  **Sequential Write-Back**: Implement the final report compiler.

---
> [!IMPORTANT]
> This transition moves Hexamind from a "Swarm of Experts" to a **"Hierarchical Reasoning Machine,"** producing reports that feel curated by a human professional analyst.
