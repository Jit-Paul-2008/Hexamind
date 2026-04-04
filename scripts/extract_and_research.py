"""Single iteration script for testing and manual runs."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "ai-service"))

from research_automation import AutonomousOrchestrator, AutonomousConfig


async def main():
    """Run a single research iteration."""
    config = AutonomousConfig()
    orchestrator = AutonomousOrchestrator(config)
    
    print("=" * 70)
    print("HEXAMIND SINGLE ITERATION")
    print("=" * 70)
    print(f"Models: Small={config.small_model}, Large={config.large_model}")
    print(f"Sources: {config.get_data_sources_list()}")
    print("=" * 70)
    print()
    
    try:
        await orchestrator.run_single_iteration()
        print("\nIteration complete")
        return 0
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
