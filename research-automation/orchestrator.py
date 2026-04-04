"""Core orchestrator for autonomous research loop."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import AutonomousConfig


class AutonomousOrchestrator:
    """Orchestrates autonomous research iterations."""
    
    def __init__(self, config: Optional[AutonomousConfig] = None) -> None:
        self.config = config or AutonomousConfig()
        self.reports_path = Path(self.config.reports_versioned_path)
        self.iterations_path = self.reports_path / "iterations"
        self.aggregated_path = self.reports_path / "aggregated"
        
        # Ensure directories exist
        self.iterations_path.mkdir(parents=True, exist_ok=True)
        self.aggregated_path.mkdir(parents=True, exist_ok=True)
        
        self._iteration_count = 0
        self._last_improvement_config: dict | None = None
    
    async def run_autonomous_loop(self) -> None:
        """Main autonomous loop: extract → research → compare → improve → repeat."""
        if not self.config.enabled:
            print("Autonomous loop disabled. Set AUTONOMOUS_ENABLED=true to start.")
            return
        
        print("[Orchestrator] Starting autonomous research loop...")
        
        try:
            while True:
                await self.run_single_iteration()
                await asyncio.sleep(self.config.iteration_interval_seconds)
        except KeyboardInterrupt:
            print("[Orchestrator] Loop interrupted by user.")
        except Exception as e:
            print(f"[Orchestrator] Fatal error: {type(e).__name__}: {e}")
            raise
    
    async def run_single_iteration(self) -> None:
        """Execute one complete iteration: extract → research → compare → improve."""
        iteration_id = self._generate_iteration_id()
        iteration_path = self._create_iteration_directory(iteration_id)
        
        print(f"\n[Iteration {self._iteration_count + 1}] {iteration_id}")
        print(f"  Path: {iteration_path}")
        
        try:
            # Stage 1: Extract data from sources
            print("  [1/5] Extracting data from sources...")
            extracted_data = await self._extract_data(iteration_path)
            if not extracted_data:
                print("  [!] No new data extracted. Skipping iteration.")
                return
            
            # Stage 2: Run research pipeline
            print("  [2/5] Running research pipeline...")
            research_report = await self._run_research(extracted_data, iteration_path)
            
            # Stage 3: Compare with previous iteration
            print("  [3/5] Comparing with previous iteration...")
            comparison_result = await self._compare_reports(research_report, iteration_path)
            
            # Stage 4: Analyze quality metrics
            print("  [4/5] Analyzing quality metrics...")
            metrics = await self._analyze_quality(research_report, comparison_result, iteration_path)
            
            # Stage 5: Suggest and implement improvements
            print("  [5/5] Analyzing improvements...")
            improvements_applied = await self._suggest_and_implement_improvements(
                metrics, comparison_result, iteration_path
            )
            
            # Save iteration manifest
            self._save_iteration_manifest(iteration_path, {
                "iteration_id": iteration_id,
                "timestamp": datetime.utcnow().isoformat(),
                "extracted_data_sources": extracted_data.get("sources", []),
                "quality_metrics": metrics,
                "comparison": comparison_result,
                "improvements_applied": improvements_applied,
            })
            
            self._iteration_count += 1
            print(f"  [✓] Iteration complete. Next run in {self.config.iteration_interval_seconds}s")
            
        except Exception as e:
            print(f"  [ERROR] Iteration failed: {type(e).__name__}: {e}")
            # Log error but don't crash loop
            self._save_error_log(iteration_path, str(e))
    
    async def _extract_data(self, iteration_path: Path) -> dict | None:
        """Extract data from configured sources."""
        # TODO: Implement data extraction
        # Placeholder for now
        return {
            "sources": self.config.get_data_sources_list(),
            "records_extracted": 0,
            "dedup_skipped": 0,
        }
    
    async def _run_research(self, extracted_data: dict, iteration_path: Path) -> dict:
        """Run research pipeline on extracted data."""
        # TODO: Integrate with ai-service/pipeline.py
        # Will call pipeline_service with local-only mode
        return {
            "research_output": "placeholder",
            "tokens_used": 0,
            "agents_executed": ["advocate", "skeptic", "synthesiser", "oracle", "verifier"],
        }
    
    async def _compare_reports(self, current_report: dict, iteration_path: Path) -> dict:
        """Compare current report with previous iteration."""
        # TODO: Integrate comparison-engine
        return {
            "previous_iteration": None,
            "new_claims": 0,
            "modified_claims": 0,
            "retracted_claims": 0,
        }
    
    async def _analyze_quality(self, report: dict, comparison: dict, iteration_path: Path) -> dict:
        """Compute quality metrics."""
        # TODO: Integrate quality analysis
        return {
            "evidence_depth": 0.75,
            "contradiction_detection": 0.85,
            "source_coverage": 0.80,
        }
    
    async def _suggest_and_implement_improvements(
        self, 
        metrics: dict, 
        comparison: dict, 
        iteration_path: Path
    ) -> list[str]:
        """Suggest improvements using 70B and optionally implement them."""
        # TODO: Integrate improvement-engine
        # Will use llama3.1:70b to suggest config changes
        return []
    
    def _generate_iteration_id(self) -> str:
        """Generate iteration ID with timestamp."""
        now = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        unique = str(uuid.uuid4())[:8]
        return f"iter-{self._iteration_count + 1:03d}-{now}-{unique}"
    
    def _create_iteration_directory(self, iteration_id: str) -> Path:
        """Create subdirectories for iteration."""
        iteration_path = self.iterations_path / iteration_id
        (iteration_path / "input").mkdir(parents=True, exist_ok=True)
        (iteration_path / "research").mkdir(parents=True, exist_ok=True)
        (iteration_path / "research" / "agent-outputs").mkdir(parents=True, exist_ok=True)
        (iteration_path / "analysis").mkdir(parents=True, exist_ok=True)
        (iteration_path / "improvements").mkdir(parents=True, exist_ok=True)
        return iteration_path
    
    def _save_iteration_manifest(self, iteration_path: Path, manifest: dict) -> None:
        """Save iteration summary manifest."""
        manifest_path = iteration_path / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
    
    def _save_error_log(self, iteration_path: Path, error_message: str) -> None:
        """Log iteration error."""
        error_path = iteration_path / "error.log"
        with open(error_path, "w") as f:
            f.write(f"{datetime.utcnow().isoformat()}: {error_message}\n")


async def main():
    """Entry point for orchestrator."""
    config = AutonomousConfig()
    orchestrator = AutonomousOrchestrator(config)
    await orchestrator.run_autonomous_loop()


if __name__ == "__main__":
    asyncio.run(main())
