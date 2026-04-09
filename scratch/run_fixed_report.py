import asyncio
import os
import sys
from pathlib import Path

# Add ai-service to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "ai-service"))

from reasoning_graph import AuroraGraph

async def main():
    query = "The specific architectural failures of 19th-century railway bridges"
    print(f"🚀 Rerunning Strategic Research with Aurora v8.5 [14B Tier]")
    print(f"Target Query: {query}")
    print("-" * 50)
    
    graph = AuroraGraph(query)
    
    try:
        async for event in graph.run():
            # The graph yields SSE-style JSON strings
            import json
            try:
                full_event = json.loads(event)
                evt = json.loads(full_event["data"])
                e_type = evt["type"]
                agent_id = evt["agentId"]
                
                if e_type == "agent_start":
                    print(f"🧠 [RUNNING] {agent_id.upper()} is investigating...")
                elif e_type == "agent_done":
                    print(f"✅ [COMPLETE] {agent_id.upper()} finished section.")
                elif e_type == "pipeline_done":
                    print("\n" + "="*50)
                    print("🏆 RESEARCH COMPLETE: Strategic Report Generated.")
                    print("="*50)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
