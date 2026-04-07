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
    graph = AuroraGraph(query)
    final_report = ""

    status_file = Path(__file__).resolve().parent.parent / "research_status.md"
    with open(status_file, "w", encoding="utf-8") as f:
        f.write(f"🚀 Initiating Aurora v4 Deep Research...\n")
        f.write(f"Query: {query}\n")
        f.write("-" * 50 + "\n")

    def log_status(msg: str):
        print(msg)
        with open(status_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    async for event in graph.run():
        event_type = event["event"]
        data = event["data"]
        
        # Simple console feedback
        if event_type == "agent_start":
            import json
            payload = json.loads(data)
            log_status(f"🧠 [BRAIN] Stage: {payload['agentId'].upper()} initialized...")
        
        if event_type == "agent_done":
            import json
            payload = json.loads(data)
            log_status(f"✅ [BRAIN] Stage: {payload['agentId'].upper()} completed.")
            log_status(f"📄 [REPORT] {payload['agentId'].upper()} Findings:\n{payload['fullContent']}\n")
            log_status("-" * 50)
        
        if event_type == "pipeline_error":
            import json
            payload = json.loads(data)
            log_status("-" * 50)
            log_status(f"❌ [CRITICAL ERROR] Stage: {payload['agentId'].upper()} failed.")
            log_status(f"Reason: {payload['fullContent']}")
            log_status("-" * 50)
            return

        if event_type == "pipeline_done":
            import json
            payload = json.loads(data)
            final_report = payload["fullContent"]


    # 5. SAVE TO WIKI
    def titleize(q: str) -> str:
        import re
        # Strip common question words
        q = re.sub(r'^(is|what|how|why|does|do|can|will|should)\s+', '', q, flags=re.IGNORECASE)
        # Title Case and join underscores
        words = [w.capitalize() for w in re.findall(r'\w+', q)]
        return "_".join(words[:5]) or "General_Research"

    output_dir = Path(__file__).resolve().parent.parent / "data" / "wiki"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    wiki_title = titleize(query)
    output_path = output_dir / f"{wiki_title}.md"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# {wiki_title.replace('_', ' ')}\n")
        f.write(f"**Research Context**: {query}\n")
        from datetime import datetime
        f.write(f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 50 + "\n\n")
        f.write(final_report)
    
    print("-" * 50)
    print(f"✅ Research Complete. Persistent Wiki Page saved: {output_path}")

if __name__ == "__main__":
    asyncio.run(run_live_trial())
