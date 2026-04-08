import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent))

from reasoning_graph import AuroraGraph, HierarchicalNode, NodeStatus
from schemas import PipelineEventType

async def main():
    if len(sys.argv) < 2:
        query = input("\nEnter research query: ").strip()
    else:
        query = sys.argv[1]

    if not query:
        print("Error: Query cannot be empty.")
        return

    print("\n" + "="*50)
    print("      HEXAMIND AURORA v8.0: STRATEGIC PLANNER")
    print("="*50)
    print(f"TARGET QUERY: {query}\n")

    # Initialize Graph
    graph = AuroraGraph(query=query)

    # Stage 1: Strategic Planning
    print("📡 Orchestrator generating Roadmap Proposal [Ollama 7B]...")
    proposal = await graph.generate_proposal()

    while True:
        print("\nPROPOSED SWARM TOPOLOGY (Strategic Roadmap):")
        print("-" * 50)
        for i, node in enumerate(proposal):
            print(f"[{i+1}] {node.role.upper():12} | Topic: {node.topic}")
        print("-" * 50)

        print("\nCOMMANDS:")
        print("  - [ENTER]       : Confirm roadmap and BEGIN Layered Research")
        print("  - add [r]:[t]   : Add specialty (e.g. 'add researcher:fiscal projections')")
        print("  - remove [i]    : Remove index")
        print("  - edit [i]:[t]  : Edit topic at index")
        print("  - exit          : Cancel session")
        
        cmd = input("\nAction> ").strip().lower()
        
        if not cmd:
            break
        
        if cmd == "exit":
            print("Session cancelled.")
            return

        try:
            if cmd.startswith("add "):
                parts = cmd[4:].split(":")
                role = parts[0].strip()
                topic = parts[1].strip()
                new_id = f"custom_{len(proposal)+1}"
                proposal.append(HierarchicalNode(id=new_id, topic=topic, role=role))
                print(f"✅ Added {role} task.")
            
            elif cmd.startswith("remove "):
                idx = int(cmd[7:].strip()) - 1
                removed = proposal.pop(idx)
                print(f"✅ Removed: {removed.topic}")
                    
            elif cmd.startswith("edit "):
                parts = cmd[5:].split(":")
                idx = int(parts[0].strip()) - 1
                new_topic = parts[1].strip()
                proposal[idx].topic = new_topic
                print(f"✅ Updated task {idx+1}")
            else:
                print("❌ Unknown command.")
        except Exception as e:
            print(f"❌ Command Error: {e}")

    # Stage 2: Execution
    print("\n🚀 Roadmap Confirmed. Launching Atomic Distillation Swarm...")
    print("Note: This will perform layered searches (100+ sources) and recursive verification.\n")
    
    # Pass corrected proposal to a NEW graph instance for deep execution
    # Ensure deep_research is enabled (implicit in v8.0 ADS)
    final_graph = AuroraGraph(query=query, task_tree=proposal)
    
    async for event in final_graph.run():
        if event.type == PipelineEventType.AGENT_START:
            print(f"🧠 [{event.sender.upper()}] starting...")
        elif event.type == PipelineEventType.AGENT_DONE:
            print(f"✅ [{event.sender.upper()}] completed pass.")
        elif event.type == PipelineEventType.PIPELINE_ERROR:
            print(f"❌ ERROR: {event.content}")

    print("\n" + "="*50)
    print("               RESEARCH COMPLETE")
    print("="*50)
    
    title = query.replace(" ", "_")[:20]
    print(f"\nFinal Dual-Reports saved to data/wiki/ as:")
    print(f"- {title}_TECHNICAL.md")
    print(f"- {title}_STRATEGIC.md\n")

if __name__ == "__main__":
    asyncio.run(main())
