"""Configuration for autonomous research loop."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AutonomousConfig:
    """Configuration for autonomous research loop."""
    
    # Data sources (pipe-separated URIs)
    data_sources: str = field(default_factory=lambda: os.getenv(
        "AUTONOMOUS_DATA_SOURCES", 
        "pdf:/home/papers"
    ))
    
    # Timing
    iteration_interval_seconds: int = field(default_factory=lambda: int(
        os.getenv("AUTONOMOUS_ITERATION_INTERVAL_SECONDS", str(6 * 3600))  # 6 hours
    ))
    
    # Parallel iterations
    max_parallel_iterations: int = field(default_factory=lambda: int(
        os.getenv("AUTONOMOUS_PARALLEL_ITERATIONS", "1")
    ))
    
    # Strict local-only mode
    local_strict_mode: bool = field(default_factory=lambda: os.getenv(
        "HEXAMIND_LOCAL_STRICT", "1"
    ).lower() in {"1", "true", "yes", "on"})
    
    # Model assignments
    small_model: str = field(default_factory=lambda: os.getenv(
        "HEXAMIND_LOCAL_MODEL_SMALL", "llama3.1:8b"
    ))
    medium_model: str = field(default_factory=lambda: os.getenv(
        "HEXAMIND_LOCAL_MODEL_MEDIUM", "llama3.1:70b-instruct-q4_K_M"
    ))
    large_model: str = field(default_factory=lambda: os.getenv(
        "HEXAMIND_LOCAL_MODEL_LARGE", "llama3.1:70b-instruct-q4_K_M"
    ))
    
    # Quality gates
    min_evidence_depth: float = field(default_factory=lambda: float(
        os.getenv("AUTONOMOUS_MIN_EVIDENCE_DEPTH", "0.7")
    ))
    min_contradiction_detection: float = field(default_factory=lambda: float(
        os.getenv("AUTONOMOUS_MIN_CONTRADICTION_DETECTION", "0.8")
    ))
    min_source_coverage: float = field(default_factory=lambda: float(
        os.getenv("AUTONOMOUS_MIN_SOURCE_COVERAGE", "0.85")
    ))
    
    # Improvement thresholds
    improvement_min_delta: float = field(default_factory=lambda: float(
        os.getenv("AUTONOMOUS_IMPROVEMENT_MIN_DELTA", "0.10")
    ))
    rollback_if_regression: bool = field(default_factory=lambda: os.getenv(
        "AUTONOMOUS_ROLLBACK_IF_REGRESSION", "true"
    ).lower() in {"1", "true", "yes", "on"})
    
    # Storage
    reports_versioned_path: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports-versioned"
    ))
    
    # Enable autonomous loop
    enabled: bool = field(default_factory=lambda: os.getenv(
        "AUTONOMOUS_ENABLED", "false"
    ).lower() in {"1", "true", "yes", "on"})
    
    def get_data_sources_list(self) -> list[str]:
        """Parse data sources from pipe-separated string."""
        return [s.strip() for s in self.data_sources.split("|") if s.strip()]
