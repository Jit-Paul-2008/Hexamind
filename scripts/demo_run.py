import asyncio
import sys
import os
import json
import re
from pathlib import Path

# Add ai-service to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "ai-service"))

from reasoning_graph import AuroraGraph
from schemas import PipelineEventType

def titleize(q: str) -> str:
    q = re.sub(r'^(is|what|how|why|does|do|can|will|should)\s+', '', q, flags=re.IGNORECASE)
    words = [w.capitalize() for w in re.findall(r'\w+', q)]
    return "_".join(words[:5]) or "General_Research"

async def run_demo(query: str):
    print(f"🚀 Starting DIRECT Aurora Research: {query}")
    graph = AuroraGraph(query, aga_mode=False, math_mode=False)
    
    # Path to fixed status log
    status_path = Path("research_status.md")
    wiki_dir = Path("data/wiki")
    wiki_dir.mkdir(parents=True, exist_ok=True)
    wiki_path = wiki_dir / f"{titleize(query)}.md"
    
    # Ensure status file exists
    if not status_path.exists():
        status_path.write_text("# Research Status Log\n", encoding="utf-8")
        
    with open(status_path, "a", encoding="utf-8") as f:
        f.write(f"\n--------------------------------------------------\n")
        f.write(f"🚀 [NEW RUN] {query}\n")
        f.write(f"Time: {os.popen('date').read().strip()}\n")
        f.flush()
        
        async for event in graph.run():
            etype = event["event"]
            data = event["data"]
            payload = json.loads(data)
            agent_id = payload.get("agentId", "unknown")
            content = payload.get("fullContent", "") or payload.get("chunk", "")
            
            if etype == PipelineEventType.AGENT_START.value:
                f.write(f"🧠 [BRAIN] Stage: {agent_id.upper()} initialized...\n")
                print(f"🧠 [BRAIN] Stage: {agent_id.upper()} initialized...")
            elif etype == PipelineEventType.AGENT_DONE.value:
                f.write(f"✅ [BRAIN] Stage: {agent_id.upper()} completed.\n")
                print(f"✅ [BRAIN] Stage: {agent_id.upper()} completed.")
                if agent_id != "synthesiser":
                    f.write(f"📄 [REPORT] {agent_id.upper()} Findings (Summary Preview):\n{content[:200]}...\n")
            elif etype == PipelineEventType.PIPELINE_DONE.value:
                f.write(f"🏆 [FINAL] Research Synthesis completed successfully.\n")
                f.write(f"📂 Output Saved to Wiki: {wiki_path}\n")
                print(f"🏆 [FINAL] Research Synthesis completed.")
                # Save to Wiki
                with open(wiki_path, "w", encoding="utf-8") as wiki_f:
                    wiki_f.write(f"# Research Report: {query}\n\n")
                    wiki_f.write(content)
            elif etype == PipelineEventType.PIPELINE_ERROR.value:
                f.write(f"❌ [ERROR] {content}\n")
                print(f"❌ [ERROR] {content}")
            
            f.flush()

if __name__ == "__main__":
    query = "Impact of AI on K-12 Literacy"
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    asyncio.run(run_demo(query))
