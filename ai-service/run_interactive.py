import asyncio
import sys
import os
from pathlib import Path
from typing import List

# Add current directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent))

from reasoning_graph import AuroraGraph, TaxonomyNode, NodeStatus
from schemas import PipelineEventType

def print_tree(nodes: List[TaxonomyNode], indent: str = "", flattened_map: List[TaxonomyNode] = None):
    """Recursively print the taxonomy tree with indentation."""
    for node in nodes:
        idx = len(flattened_map) + 1
        flattened_map.append(node)
        print(f"{indent}[{idx}] {node.role.upper():12} | {node.topic}")
        if node.children:
            print_tree(node.children, indent + "    ", flattened_map)

async def main():
    if len(sys.argv) < 2:
        query = input("\nEnter research query: ").strip()
    else:
        query = sys.argv[1]

    if not query:
        print("Error: Query cannot be empty.")
        return

    print("\n" + "="*50)
    print("      HEXAMIND AURORA v8.5: TAXONOMY PLANNER")
    print("="*50)
    print(f"TARGET QUERY: {query}\n")

    # Initialize Graph
    graph = AuroraGraph(query=query)

    # Stage 1: Strategic Planning
    print("📡 Orchestrator constructing Strategic Taxonomy [Ollama 7B]...")
    proposal_tree = await graph.generate_proposal()

    while True:
        print("\nPROPOSED RESEARCH TAXONOMY (Hierarchical Roadmap):")
        print("-" * 50)
        flattened_list = []
        print_tree(proposal_tree, "", flattened_list)
        print("-" * 50)

        print("\nCOMMANDS:")
        print("  - [ENTER]       : Confirm taxonomy and BEGIN Recursive Execution")
        print("  - branch [i]:[r]:[t] : Add child to index (e.g. 'branch 1:analyst:market cap')")
        print("  - remove [i]    : Remove index and its sub-tree")
        print("  - edit [i]:[t]  : Edit topic at index")
        print("  - exit          : Cancel session")
        
        cmd = input("\nAction> ").strip().lower()
        
        if not cmd:
            break
        
        if cmd == "exit":
            print("Session cancelled.")
            return

        try:
            if cmd.startswith("branch "):
                parts = cmd[7:].split(":")
                parent_idx = int(parts[0].strip()) - 1
                role = parts[1].strip()
                topic = parts[2].strip()
                
                parent_node = flattened_list[parent_idx]
                new_node = TaxonomyNode(
                    id=f"{parent_node.id}_{len(parent_node.children)+1}",
                    topic=topic,
                    role=role,
                    parent_id=parent_node.id
                )
                parent_node.children.append(new_node)
                print(f"✅ Added child branch to node {parent_idx+1}.")
            
            elif cmd.startswith("remove "):
                idx = int(cmd[7:].strip()) - 1
                node_to_remove = flattened_list[idx]
                
                if node_to_remove.parent_id:
                    # Find parent in flattened list and remove from children
                    parent = next(n for n in flattened_list if n.id == node_to_remove.parent_id)
                    parent.children.remove(node_to_remove)
                else:
                    proposal_tree.remove(node_to_remove)
                print(f"✅ Removed: {node_to_remove.topic}")
                    
            elif cmd.startswith("edit "):
                parts = cmd[5:].split(":")
                idx = int(parts[0].strip()) - 1
                new_topic = parts[1].strip()
                flattened_list[idx].topic = new_topic
                print(f"✅ Updated node {idx+1}")
            else:
                print("❌ Unknown command.")
        except Exception as e:
            print(f"❌ Command Error: {e}")

    # Stage 2: Execution
    print("\n🚀 Taxonomy Confirmed. Launching Hierarchical Reasoning Engine...")
    print("Note: Child nodes will inherit context from parents for seamless synthesis.\n")
    
    final_graph = AuroraGraph(query=query, task_tree=proposal_tree)
    
    async for event_data in final_graph.run():
        import json
        evt = json.loads(event_data["data"])
        e_type = evt["type"]
        agent_id = evt["agentId"]
        content = evt.get("fullContent", "")

        if e_type == "agent_start":
            print(f"🧠 [{agent_id.upper()}] starting...")
        elif e_type == "agent_done":
            print(f"✅ [{agent_id.upper()}] completed section.")
        elif e_type == "pipeline_error":
            print(f"❌ ERROR: {content}")
        elif e_type == "pipeline_done":
            print("\nFinal Synthesis complete.")

    print("\n" + "="*50)
    print("               RESEARCH COMPLETE")
    print("="*50)
    
    title = query.replace(" ", "_")[:20]
    print(f"\nFinal Taxonomy-First report generated.")

if __name__ == "__main__":
    asyncio.run(main())
