import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to sys.path to import reasoning_graph
sys.path.append(str(Path(__file__).resolve().parent))

from reasoning_graph import AuroraGraph


def _resolve_query() -> tuple[str, bool]:
    args = sys.argv[1:]
    aga_mode = False
    if "--aga" in args:
        aga_mode = True
        args.remove("--aga")
    value = " ".join(args).strip()
    if value:
        return value, aga_mode
    return "Importance of switching to project based teaching rather than traditional course based teaching", aga_mode

async def run_live_trial():
    query, aga_mode = _resolve_query()
    graph = AuroraGraph(query, aga_mode=aga_mode)
    final_report = ""

    status_file = Path(__file__).resolve().parent.parent / "research_status.md"
    with open(status_file, "w", encoding="utf-8") as f:
        mode_str = "AGA Enabled" if aga_mode else "Standard"
        f.write(f"🚀 Initiating Aurora v4 Deep Research... (Mode: {mode_str})\n")
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


    # 5. SAVE TO WIKI (Dual Report Separation)
    def titleize(q: str) -> str:
        import re
        q = re.sub(r'^(is|what|how|why|does|do|can|will|should)\s+', '', q, flags=re.IGNORECASE)
        words = [w.capitalize() for w in re.findall(r'\w+', q)]
        return "_".join(words[:5]) or "General_Research"

    output_dir = Path(__file__).resolve().parent.parent / "data" / "wiki"
    output_dir.mkdir(parents=True, exist_ok=True)
    wiki_title = titleize(query)
    
    # Check for Dual Report headers
    if "## Technical report" in final_report and "## Strategic Executive Summary" in final_report:
        parts = final_report.split("## Strategic Executive Summary")
        tech_part = parts[0]
        strat_part = "## Strategic Executive Summary" + parts[1]
        
        # Save Technical Intelligence
        tech_path = output_dir / f"{wiki_title}_TECHNICAL.md"
        with open(tech_path, "w", encoding="utf-8") as f:
            f.write(f"# Technical Intelligence: {wiki_title.replace('_', ' ')}\n")
            f.write(tech_part)
        
        # Save Strategic Executive Summary
        strat_path = output_dir / f"{wiki_title}_STRATEGIC.md"
        with open(strat_path, "w", encoding="utf-8") as f:
            f.write(f"# Strategic Executive Summary: {wiki_title.replace('_', ' ')}\n")
            f.write(strat_part)
            
        print("-" * 50)
        print(f"✅ Dual Reports saved successfully:")
        print(f"   1. Technical: {tech_path}")
        print(f"   2. Strategic: {strat_path}")
    else:
        # Fallback to single file
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
