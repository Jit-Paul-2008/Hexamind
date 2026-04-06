import asyncio
import os
import sys
from pathlib import Path

# Fix python path to find local modules
sys.path.append(str(Path(__file__).resolve().parent))

from reasoning_graph import AuroraGraph

async def main():
    query = "What are the core technical advantages of DeepSeek-R1 for local research?"
    print(f"--- Testing Aurora Engine (v4) ---")
    print(f"Query: {query}")
    
    graph = AuroraGraph(query)
    
    try:
        async for event in graph.run():
            etype = event["event"]
            edata = event["data"]
            print(f"[{etype}] step...")
            
            # Print a bit of the final output
            if etype == "PIPELINE_DONE":
                import json
                data = json.loads(edata)
                print("\n--- FINAL REPORT SUMMARY ---")
                print(data["fullContent"][:500] + "...")
                
    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
