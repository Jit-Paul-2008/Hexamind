"""Core orchestrator for autonomous research loop."""

from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

project_root = Path(__file__).resolve().parents[1]
ai_service_path = project_root / "ai-service"
if str(ai_service_path) not in sys.path:
    sys.path.insert(0, str(ai_service_path))

from .config import AutonomousConfig
from data_sources.ingestors import UniversalIngestor
from comparison_engine.diff import SemanticDiff
from comparison_engine.metrics import QualityAnalyzer
from comparison_engine.change_detection import ChangeDetector
from comparison_engine.storage import ComparisonStorage
from improvement_engine.analyzer import GapAnalyzer
from improvement_engine.suggester import ImprovementSuggester
from improvement_engine.implementor import ConfigImplementor
from improvement_engine.feedback_loop import FeedbackLoop, ImprovementResult
from pipeline import pipeline_service


class AutonomousOrchestrator:
    """Orchestrates autonomous research iterations."""

    def __init__(self, config: AutonomousConfig | None = None) -> None:
        self.config = config or AutonomousConfig()
        self.reports_path = Path(self.config.reports_versioned_path)
        self.iterations_path = self.reports_path / "iterations"
        self.aggregated_path = self.reports_path / "aggregated"
        self.iterations_path.mkdir(parents=True, exist_ok=True)
        self.aggregated_path.mkdir(parents=True, exist_ok=True)
        self.ingestor = UniversalIngestor()
        self.diff_engine = SemanticDiff()
        self.quality_analyzer = QualityAnalyzer()
        self.change_detector = ChangeDetector()
        self.comparison_storage = ComparisonStorage(self.aggregated_path)
        self.gap_analyzer = GapAnalyzer()
        self.improvement_suggester = ImprovementSuggester(model=self.config.large_model)
        self.config_implementor = ConfigImplementor()
        self.feedback_loop = FeedbackLoop()
        self._iteration_count = 0
        self._last_report_path: Path | None = None
        self._last_report_text: str = ""

    async def run_autonomous_loop(self) -> None:
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

    async def run_single_iteration(self) -> None:
        iteration_id = self._generate_iteration_id()
        iteration_path = self._create_iteration_directory(iteration_id)
        print(f"\n[Iteration {self._iteration_count + 1}] {iteration_id}")

        extracted_data = await self._extract_data(iteration_path)
        if not extracted_data.get("raw_content", "").strip():
            self._save_iteration_manifest(iteration_path, {"iteration_id": iteration_id, "status": "no-data"})
            print("  No new data extracted. Skipping iteration.")
            return

        research_report = await self._run_research(extracted_data, iteration_path)
        comparison_result = await self._compare_reports(research_report, iteration_path)
        metrics = await self._analyze_quality(research_report, comparison_result, iteration_path)
        improvements_applied = await self._suggest_and_implement_improvements(metrics, comparison_result, iteration_path)

        manifest = {
            "iteration_id": iteration_id,
            "timestamp": datetime.utcnow().isoformat(),
            "extracted_data_sources": extracted_data.get("sources", []),
            "quality_metrics": metrics,
            "comparison": comparison_result,
            "improvements_applied": improvements_applied,
            "report_path": str(iteration_path / "research" / "full-report.md"),
        }
        self._save_iteration_manifest(iteration_path, manifest)
        self._last_report_path = iteration_path
        self._iteration_count += 1
        print("  Run complete.")

    async def _extract_data(self, iteration_path: Path) -> dict[str, Any]:
        results = await self.ingestor.extract(self.config.get_data_sources_list(), dedup=True, tag=iteration_path.name)
        input_path = iteration_path / "input" / "source-data.json"
        input_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        (iteration_path / "input" / "extraction-log.md").write_text(results.get("extraction_log", ""), encoding="utf-8")
        return {"sources": results.get("sources", []), "raw_content": results.get("raw_content", ""), "records_extracted": results.get("records_extracted", 0), "dedup_skipped": results.get("dedup_skipped", 0)}

    async def _run_research(self, extracted_data: dict[str, Any], iteration_path: Path) -> dict[str, Any]:
        query = extracted_data.get("raw_content", "")[:12000]
        session_id = pipeline_service.start(query=query or "Autonomous research iteration", tenant_id="autonomous")
        async for _event in pipeline_service.stream_events(session_id, tenant_id="autonomous"):
            pass
        final_report = pipeline_service.get_final_report(session_id, tenant_id="autonomous")
        quality_report = pipeline_service.get_quality_report(session_id, tenant_id="autonomous")
        research_dir = iteration_path / "research"
        research_dir.joinpath("full-report.md").write_text(final_report, encoding="utf-8")
        research_dir.joinpath("metadata.json").write_text(json.dumps(quality_report, indent=2), encoding="utf-8")
        self._last_report_text = final_report
        return {"session_id": session_id, "final_report": final_report, "quality_report": quality_report, "query": query}

    async def _compare_reports(self, current_report: dict[str, Any], iteration_path: Path) -> dict[str, Any]:
        previous_text = self._load_previous_report_text()
        current_text = current_report.get("final_report", "")
        semantic_changes = self.diff_engine.compare(previous_text, current_text) if previous_text else []
        delta = self.change_detector.detect_changes({"final_report": current_text}, {"final_report": previous_text} if previous_text else None)
        comparison = {"semantic_changes": [change.__dict__ for change in semantic_changes], "delta": delta.__dict__, "previous_exists": bool(previous_text)}
        (iteration_path / "analysis" / "prev-comparison.md").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
        self.comparison_storage.save_comparison(iteration_path.name, comparison)
        return comparison

    async def _analyze_quality(self, report: dict[str, Any], comparison: dict[str, Any], iteration_path: Path) -> dict[str, Any]:
        metrics = self.quality_analyzer.analyze(report.get("final_report", "")).to_dict()
        (iteration_path / "analysis" / "quality-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        gaps = self.gap_analyzer.analyze(report.get("final_report", ""), metrics)
        (iteration_path / "analysis" / "gaps-identified.md").write_text(json.dumps(gaps.__dict__, indent=2), encoding="utf-8")
        return metrics

    async def _suggest_and_implement_improvements(self, metrics: dict[str, Any], comparison: dict[str, Any], iteration_path: Path) -> list[str]:
        gaps = self.gap_analyzer.analyze(self._last_report_text, metrics)
        suggestions = await self.improvement_suggester.suggest(self._last_report_text, metrics, gaps.__dict__)
        suggestion_dicts = [s.__dict__ for s in suggestions]
        (iteration_path / "improvements" / "suggestions.md").write_text(json.dumps(suggestion_dicts, indent=2), encoding="utf-8")
        recommended = await self.improvement_suggester.recommend_config(suggestions)
        if recommended:
            await self.config_implementor.apply(recommended)
            (iteration_path / "improvements" / "applied-config.json").write_text(json.dumps(recommended, indent=2), encoding="utf-8")
        return list(recommended.keys()) if recommended else []

    def _generate_iteration_id(self) -> str:
        return f"iter-{self._iteration_count + 1:03d}-{datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')}-{uuid.uuid4().hex[:8]}"

    def _create_iteration_directory(self, iteration_id: str) -> Path:
        iteration_path = self.iterations_path / iteration_id
        for subpath in ["input", "research/agent-outputs", "analysis", "improvements"]:
            (iteration_path / subpath).mkdir(parents=True, exist_ok=True)
        return iteration_path

    def _save_iteration_manifest(self, iteration_path: Path, manifest: dict[str, Any]) -> None:
        (iteration_path / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def _load_previous_report_text(self) -> str:
        if self._last_report_path is None:
            return ""
        report_path = self._last_report_path / "research" / "full-report.md"
        return report_path.read_text(encoding="utf-8") if report_path.exists() else ""
