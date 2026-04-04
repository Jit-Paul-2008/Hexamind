"""Configuration for autonomous research loop."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class AutonomousConfig:
    data_sources: str = field(default_factory=lambda: os.getenv("AUTONOMOUS_DATA_SOURCES", "file:///home/papers"))
    iteration_interval_seconds: int = field(default_factory=lambda: int(os.getenv("AUTONOMOUS_ITERATION_INTERVAL_SECONDS", str(6 * 3600))))
    max_parallel_iterations: int = field(default_factory=lambda: int(os.getenv("AUTONOMOUS_PARALLEL_ITERATIONS", "1")))
    local_strict_mode: bool = field(default_factory=lambda: os.getenv("HEXAMIND_LOCAL_STRICT", "1").lower() in {"1", "true", "yes", "on"})
    small_model: str = field(default_factory=lambda: os.getenv("HEXAMIND_LOCAL_MODEL_SMALL", "llama3.1:8b"))
    medium_model: str = field(default_factory=lambda: os.getenv("HEXAMIND_LOCAL_MODEL_MEDIUM", "llama3.1:70b-instruct-q4_K_M"))
    large_model: str = field(default_factory=lambda: os.getenv("HEXAMIND_LOCAL_MODEL_LARGE", "llama3.1:70b-instruct-q4_K_M"))
    min_evidence_depth: float = field(default_factory=lambda: float(os.getenv("AUTONOMOUS_MIN_EVIDENCE_DEPTH", "0.7")))
    min_contradiction_detection: float = field(default_factory=lambda: float(os.getenv("AUTONOMOUS_MIN_CONTRADICTION_DETECTION", "0.8")))
    min_source_coverage: float = field(default_factory=lambda: float(os.getenv("AUTONOMOUS_MIN_SOURCE_COVERAGE", "0.85")))
    improvement_min_delta: float = field(default_factory=lambda: float(os.getenv("AUTONOMOUS_IMPROVEMENT_MIN_DELTA", "0.10")))
    rollback_if_regression: bool = field(default_factory=lambda: os.getenv("AUTONOMOUS_ROLLBACK_IF_REGRESSION", "true").lower() in {"1", "true", "yes", "on"})
    reports_versioned_path: str = field(default_factory=lambda: os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports-versioned"))
    enabled: bool = field(default_factory=lambda: os.getenv("AUTONOMOUS_ENABLED", "false").lower() in {"1", "true", "yes", "on"})

    def get_data_sources_list(self) -> list[str]:
        return [source.strip() for source in self.data_sources.split("|") if source.strip()]
