"""Core orchestrator for autonomous research loop."""

from __future__ import annotations

import asyncio
import json
import os
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
from importlib import import_module

pipeline_service = import_module("pipeline").pipeline_service


class AutonomousOrchestrator:
    """Orchestrates autonomous research iterations."""

    def __init__(self, config: AutonomousConfig | None = None) -> None:
        self.config = config or AutonomousConfig()
        if self.config.allow_web_research:
            os.environ["HEXAMIND_WEB_RESEARCH"] = "1"
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
        self._last_coverage_summary: dict[str, Any] = {}

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
            "coverage_summary": self._last_coverage_summary,
            "quality_metrics": metrics,
            "comparison": comparison_result,
            "improvements_applied": improvements_applied,
            "report_path": str(iteration_path / "research" / "full-report.md"),
        }
        self._save_iteration_manifest(iteration_path, manifest)
        self._ensure_human_review_form(iteration_path, iteration_id)
        run_snapshot = self._build_run_snapshot(
            iteration_id=iteration_id,
            iteration_path=iteration_path,
            research_report=research_report,
            quality_metrics=metrics,
            coverage_summary=self._last_coverage_summary,
            improvements_applied=improvements_applied,
        )
        self._update_visual_dashboard(run_snapshot)
        self._last_report_path = iteration_path
        self._iteration_count += 1
        print("  Run complete.")

    async def _extract_data(self, iteration_path: Path) -> dict[str, Any]:
        results = await self.ingestor.extract(self.config.get_data_sources_list(), dedup=True, tag=iteration_path.name)
        coverage_summary = self._compute_source_coverage(results)
        self._last_coverage_summary = coverage_summary
        input_path = iteration_path / "input" / "source-data.json"
        results["coverage_summary"] = coverage_summary
        input_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        (iteration_path / "input" / "extraction-log.md").write_text(results.get("extraction_log", ""), encoding="utf-8")
        return {"sources": results.get("sources", []), "raw_content": results.get("raw_content", ""), "records_extracted": results.get("records_extracted", 0), "dedup_skipped": results.get("dedup_skipped", 0), "coverage_summary": coverage_summary}

    async def _run_research(self, extracted_data: dict[str, Any], iteration_path: Path) -> dict[str, Any]:
        query = self._build_research_query(extracted_data)
        session_id = pipeline_service.start(query=query, tenant_id="autonomous")
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
        suggestions = await self.improvement_suggester.suggest(
            report=self._last_report_text,
            metrics=metrics,
            gaps=gaps.__dict__,
            coverage_summary=self._last_coverage_summary,
            comparison=comparison,
            max_suggestions=self.config.improvement_max_suggestions,
        )
        suggestion_dicts = [s.__dict__ for s in suggestions]
        (iteration_path / "improvements" / "suggestions.md").write_text(json.dumps(suggestion_dicts, indent=2), encoding="utf-8")
        recommended = await self.improvement_suggester.recommend_config(
            suggestions,
            min_confidence=self.config.improvement_min_confidence,
            min_delta=self.config.improvement_min_delta,
        )
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

    def _compute_source_coverage(self, extracted_data: dict[str, Any]) -> dict[str, Any]:
        sources = [source for source in extracted_data.get("sources", []) if source]
        raw_content = extracted_data.get("raw_content", "") or ""
        source_count = len(sources)
        unique_domains = len({self._source_domain(source) for source in sources})
        extracted_chars = len(raw_content)
        source_coverage_ratio = min(1.0, source_count / max(1, self.config.minimum_source_count))
        diversity_ratio = min(1.0, unique_domains / max(1, self.config.minimum_source_diversity))
        char_ratio = min(1.0, extracted_chars / max(1, self.config.minimum_extracted_chars))
        overall = round((source_coverage_ratio + diversity_ratio + char_ratio) / 3.0, 3)
        return {
            "sourceCount": source_count,
            "uniqueDomains": unique_domains,
            "extractedChars": extracted_chars,
            "sourceCoverageRatio": round(source_coverage_ratio, 3),
            "sourceDiversityRatio": round(diversity_ratio, 3),
            "extractedCharRatio": round(char_ratio, 3),
            "overallCoverage": overall,
            "allowWebResearch": self.config.allow_web_research,
        }

    def _build_research_query(self, extracted_data: dict[str, Any]) -> str:
        raw_content = (extracted_data.get("raw_content", "") or "").strip()
        sources = extracted_data.get("sources", []) or []
        coverage_summary = extracted_data.get("coverage_summary", {}) or {}
        source_lines = "\n".join(f"- {source}" for source in sources[:12]) or "- no sources"
        directive = (
            "Use the supplied source corpus as the primary evidence base. "
            "Corroborate claims with any available live research only if web research is enabled. "
            "Surface missing evidence, contradictions, and source gaps explicitly."
        )
        if self.config.allow_web_research:
            directive += " Use live web retrieval to increase source diversity and coverage where relevant."
        query = (
            f"Autonomous research task.\n"
            f"Coverage summary: {json.dumps(coverage_summary, sort_keys=True)}\n"
            f"Source inventory:\n{source_lines}\n\n"
            f"Source corpus:\n{raw_content[: self.config.maximum_source_chars]}\n\n"
            f"Directive: {directive}"
        )
        return query[: self.config.maximum_source_chars]

    @staticmethod
    def _source_domain(source: str) -> str:
        if "//" not in source:
            return source.split("/", 1)[0]
        try:
            return source.split("//", 1)[1].split("/", 1)[0].lower()
        except Exception:
            return source

    def _build_run_snapshot(
        self,
        iteration_id: str,
        iteration_path: Path,
        research_report: dict[str, Any],
        quality_metrics: dict[str, Any],
        coverage_summary: dict[str, Any],
        improvements_applied: list[str],
    ) -> dict[str, Any]:
        quality_report = research_report.get("quality_report", {}) if isinstance(research_report, dict) else {}
        run_metadata = quality_report.get("runMetadata", {}) if isinstance(quality_report, dict) else {}
        stage_timings = run_metadata.get("stageTimings", {}) if isinstance(run_metadata, dict) else {}
        provider_diagnostics = run_metadata.get("providerDiagnostics", {}) if isinstance(run_metadata, dict) else {}
        raw_report = research_report.get("final_report", "") if isinstance(research_report, dict) else ""

        overall_score = float(quality_report.get("overallScore", quality_metrics.get("overall_score", 0.0)) or 0.0)
        trust_score = float(quality_report.get("trustScore", 0.0) or 0.0)
        verification_rate = float(
            (quality_report.get("metrics", {}) if isinstance(quality_report.get("metrics", {}), dict) else {}).get(
                "claimVerificationRate", 0.0
            )
            or 0.0
        )
        total_seconds = float(stage_timings.get("totalSeconds", 0.0) or 0.0)
        token_used = int(provider_diagnostics.get("tokenBudgetUsed", 0) or 0)
        api_present = bool(provider_diagnostics.get("activeProvider", "").strip()) and provider_diagnostics.get("activeProvider") != "deterministic"
        quality_metrics_block = quality_report.get("metrics", {}) if isinstance(quality_report.get("metrics", {}), dict) else {}
        citation_count = int(quality_metrics_block.get("citationCount", 0) or 0)

        human_like_score = self._estimate_human_like_score(raw_report)
        usefulness_score = self._estimate_usefulness_score(
            overall_score=overall_score,
            verification_rate=verification_rate,
            coverage=coverage_summary,
            citation_count=citation_count,
            human_like_score=human_like_score,
        )
        accuracy_proxy = round(verification_rate * 100.0, 2)
        human_review_score = self._load_human_review_score(iteration_path)

        return {
            "iterationId": iteration_id,
            "timestamp": datetime.utcnow().isoformat(),
            "provider": provider_diagnostics.get("activeProvider", "unknown"),
            "apiPresent": api_present,
            "tokenUsed": token_used,
            "speedSeconds": round(total_seconds, 3),
            "overallScore": round(overall_score, 2),
            "trustScore": round(trust_score, 2),
            "accuracyProxy": accuracy_proxy,
            "humanLikeScore": human_like_score,
            "usefulnessScore": usefulness_score,
            "humanReviewScore": human_review_score,
            "citationCount": citation_count,
            "coverage": coverage_summary,
            "improvementsApplied": improvements_applied,
        }

    def _update_visual_dashboard(self, snapshot: dict[str, Any]) -> None:
        history_path = self.aggregated_path / "run-metrics-history.json"
        dashboard_path = self.aggregated_path / "run-results-dashboard.md"

        history: list[dict[str, Any]] = []
        if history_path.exists():
            try:
                loaded = json.loads(history_path.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    history = loaded
            except Exception:
                history = []

        history.append(snapshot)
        history = history[-120:]
        history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
        dashboard_path.write_text(self._render_dashboard_markdown(history), encoding="utf-8")

    def _render_dashboard_markdown(self, history: list[dict[str, Any]]) -> str:
        runs = [str(index + 1) for index in range(len(history))]
        speed = [round(float(item.get("speedSeconds", 0.0) or 0.0), 2) for item in history]
        accuracy = [round(float(item.get("accuracyProxy", 0.0) or 0.0), 2) for item in history]
        usefulness = [round(float(item.get("usefulnessScore", 0.0) or 0.0), 2) for item in history]
        human_like = [round(float(item.get("humanLikeScore", 0.0) or 0.0), 2) for item in history]
        human_review = [round(float(item.get("humanReviewScore", 0.0) or 0.0), 2) for item in history]
        tokens = [int(item.get("tokenUsed", 0) or 0) for item in history]

        latest = history[-1] if history else {}
        latest_iteration = latest.get("iterationId", "n/a")
        latest_provider = latest.get("provider", "unknown")
        latest_api = "yes" if latest.get("apiPresent") else "no"

        table_lines = [
            "| Run | Iteration | Provider | API | Speed(s) | Accuracy* | Human-like* | Usefulness* | Human Review | Tokens | Overall | Trust |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for idx, item in enumerate(history, start=1):
            human_review_value = item.get("humanReviewScore")
            human_review_text = f"{float(human_review_value):.2f}" if human_review_value is not None else "pending"
            table_lines.append(
                "| "
                + f"{idx} | {item.get('iterationId', 'n/a')} | {item.get('provider', 'unknown')} | "
                + ("yes" if item.get("apiPresent") else "no")
                + f" | {float(item.get('speedSeconds', 0.0) or 0.0):.2f} | {float(item.get('accuracyProxy', 0.0) or 0.0):.2f}"
                + f" | {float(item.get('humanLikeScore', 0.0) or 0.0):.2f} | {float(item.get('usefulnessScore', 0.0) or 0.0):.2f}"
                + f" | {human_review_text} | {int(item.get('tokenUsed', 0) or 0)} | {float(item.get('overallScore', 0.0) or 0.0):.2f}"
                + f" | {float(item.get('trustScore', 0.0) or 0.0):.2f} |"
            )

        return "\n".join(
            [
                "# Autonomous Run Results Dashboard",
                "",
                "Auto-updated after each autonomous run.",
                "",
                f"Latest iteration: {latest_iteration}",
                f"Latest provider: {latest_provider}",
                f"API present: {latest_api}",
                "",
                "## Trend Charts",
                "",
                "```mermaid",
                "xychart-beta",
                "    title \"Run Speed and Quality Trends\"",
                f"    x-axis \"Run\" [{', '.join(runs)}]",
                "    y-axis \"Score / Seconds\" 0 --> 100",
                f"    line \"Accuracy\" [{', '.join(str(v) for v in accuracy)}]",
                f"    line \"Human-like\" [{', '.join(str(v) for v in human_like)}]",
                f"    line \"Usefulness\" [{', '.join(str(v) for v in usefulness)}]",
                f"    line \"HumanReview\" [{', '.join(str(v) for v in human_review)}]",
                f"    line \"SpeedSeconds\" [{', '.join(str(v) for v in speed)}]",
                "```",
                "",
                "```mermaid",
                "xychart-beta",
                "    title \"Token Usage Per Run\"",
                f"    x-axis \"Run\" [{', '.join(runs)}]",
                "    y-axis \"Tokens\" 0 --> 50000",
                f"    bar \"TokensUsed\" [{', '.join(str(v) for v in tokens)}]",
                "```",
                "",
                "## Run Table",
                "",
                *table_lines,
                "",
                "*Accuracy, Human-like, and Usefulness are proxy metrics for continuous comparison.",
                "*Human Review is a manual score from the per-run review form (0.00/pending means not yet filled).",
            ]
        )

    def _ensure_human_review_form(self, iteration_path: Path, iteration_id: str) -> None:
        review_path = iteration_path / "analysis" / "human-review-form.json"
        if review_path.exists():
            return
        template = {
            "iterationId": iteration_id,
            "status": "pending",
            "reviewer": "",
            "reviewedAt": "",
            "scoringScale": "0-10",
            "scores": {
                "accuracy": None,
                "humanLikeResponse": None,
                "usefulness": None,
                "overallHumanReviewScore": None,
            },
            "notes": "",
            "actionItems": [],
            "instructions": "Fill numeric scores (0-10). Set overallHumanReviewScore explicitly or leave null to auto-average when dashboard reads it.",
        }
        review_path.write_text(json.dumps(template, indent=2), encoding="utf-8")

    def _load_human_review_score(self, iteration_path: Path) -> float | None:
        review_path = iteration_path / "analysis" / "human-review-form.json"
        if not review_path.exists():
            return None
        try:
            payload = json.loads(review_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return None
            scores = payload.get("scores", {}) if isinstance(payload.get("scores", {}), dict) else {}
            explicit = scores.get("overallHumanReviewScore")
            if explicit is not None:
                return round(float(explicit) * 10.0, 2)

            values = []
            for key in ("accuracy", "humanLikeResponse", "usefulness"):
                value = scores.get(key)
                if value is None:
                    continue
                values.append(float(value))
            if not values:
                return None
            return round((sum(values) / len(values)) * 10.0, 2)
        except Exception:
            return None

    def _estimate_human_like_score(self, report_text: str) -> float:
        text = (report_text or "").strip()
        if not text:
            return 0.0
        word_count = len(text.split())
        section_hits = sum(1 for section in ["## Abstract", "## 1. Introduction", "## 3. Results", "## 4. Discussion", "## References"] if section in text)
        sentence_count = max(1, text.count(".") + text.count("!") + text.count("?"))
        avg_sentence_words = word_count / sentence_count
        structure_score = min(40.0, section_hits * 8.0)
        length_score = min(35.0, word_count / 45.0)
        fluency_score = max(0.0, 25.0 - abs(avg_sentence_words - 20.0))
        return round(min(100.0, structure_score + length_score + fluency_score), 2)

    def _estimate_usefulness_score(
        self,
        overall_score: float,
        verification_rate: float,
        coverage: dict[str, Any],
        citation_count: int,
        human_like_score: float,
    ) -> float:
        coverage_score = float(coverage.get("overallCoverage", 0.0) or 0.0) * 100.0
        verification_score = verification_rate * 100.0
        citation_score = min(100.0, citation_count * 10.0)
        combined = (
            (overall_score * 0.35)
            + (verification_score * 0.25)
            + (coverage_score * 0.20)
            + (citation_score * 0.10)
            + (human_like_score * 0.10)
        )
        return round(min(100.0, combined), 2)
