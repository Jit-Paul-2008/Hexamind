"""Entry point for autonomous research loop."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "ai-service"))

from research_automation import AutonomousOrchestrator, AutonomousConfig


def main():
    """Start the autonomous research loop."""
    config = AutonomousConfig()
    
    if not config.enabled:
        print("❌ Autonomous loop is DISABLED")
        print("   To enable, set: AUTONOMOUS_ENABLED=true in .env.autonomous")
        print("   Example config: .env.autonomous.example")
        return 1
    
    print("=" * 70)
    print("🔬 HEXAMIND AUTONOMOUS RESEARCH LOOP")
    print("=" * 70)
    print(f"✓ Model Provider: {config.small_model} (small), {config.large_model} (large)")
    print(f"✓ Iteration Interval: {config.iteration_interval_seconds}s ({config.iteration_interval_seconds / 3600:.1f}h)")
    print(f"✓ Data Sources: {len(config.get_data_sources_list())} source(s)")
    print(f"✓ Quality Gates: Evidence={config.min_evidence_depth}, Coverage={config.min_source_coverage}")
    print(f"✓ Strict Local: {config.local_strict_mode}")
    print(f"✓ Storage: {config.reports_versioned_path}")
    print("=" * 70)
    print()
    
    try:
        orchestrator = AutonomousOrchestrator(config)
        asyncio.run(orchestrator.run_autonomous_loop())
        return 0
    except KeyboardInterrupt:
        print("\n🛑 Loop interrupted by user")
        return 0
    except Exception as e:
        print(f"\n❌ Fatal error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
