import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to sys.path to import reasoning_graph
sys.path.append(str(Path(__file__).resolve().parent))

from reasoning_graph import AuroraGraph


def _resolve_query() -> str:
    value = " ".join(sys.argv[1:]).strip()
    if value:
        return value
    return "Importance of switching to project based teaching rather than traditional course based teaching"

async def run_live_trial():
    query = _resolve_query()
    print(f"🚀 Initiating Aurora v4 Deep Research...")
    print(f"Query: {query}")
    print("-" * 50)
    
    graph = AuroraGraph(query)
    final_report = ""
    
    async for event in graph.run():
        event_type = event["event"]
        data = event["data"]
        
        # Simple console feedback
        if event_type == "agent_start":
            import json
            payload = json.loads(data)
            print(f"🧠 [BRAIN] Stage: {payload['agentId'].upper()} initialized...")
        
        if event_type == "agent_done":
            import json
            payload = json.loads(data)
            print(f"✅ [BRAIN] Stage: {payload['agentId'].upper()} completed.")
            print(f"📄 [REPORT] {payload['agentId'].upper()} Findings:\n{payload['fullContent']}\n")
            print("-" * 50)
        
        if event_type == "pipeline_error":
            import json
            payload = json.loads(data)
            print("-" * 50)
            print(f"❌ [CRITICAL ERROR] Stage: {payload['agentId'].upper()} failed.")
            print(f"Reason: {payload['fullContent']}")
            print("-" * 50)
            return

        if event_type == "pipeline_done":
            import json
            payload = json.loads(data)
            final_report = payload["fullContent"]


    # Save to "demo runs"
    output_path = Path(__file__).resolve().parent.parent / "demo runs"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Aurora v4 Research Report\n")
        f.write(f"**Query**: {query}\n")
        f.write("-" * 50 + "\n\n")
        f.write(final_report)
    
    print("-" * 50)
    print(f"✅ Research Complete. Report saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(run_live_trial())
