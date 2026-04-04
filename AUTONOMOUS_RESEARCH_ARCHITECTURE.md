"""Autonomous Research System Architecture

Autonomous loop structure for self-improving research using local models.

## System Overview

The autonomous research system continuously:
1. **Extracts** real data from configured sources (PDFs, web, APIs)
2. **Researches** using local models (no fallback, strict local-only)
3. **Stores** full versioned reports and agent outputs
4. **Compares** with previous iterations using semantic diff
5. **Analyzes** quality metrics (evidence depth, source coverage, etc)
6. **Improves** pipeline configuration based on 70B analysis
7. **Loops** automatically at configured interval (default 6h)

## Architecture

### 1. Orchestrator (research-automation/orchestrator.py)
Main loop coordinator managing iteration lifecycle.
- Calls data extraction
- Invokes research pipeline
- Triggers comparison and analysis
- Coordinates improvement suggestions

### 2. Data Sources (data-sources/)
Universal ingestion from multiple source types.
- File extraction (PDFs, TXT)
- Web crawling (ArXiv, websites)
- API endpoints
- Deduplication and caching

### 3. Comparison Engine (comparison-engine/)
Semantic diff and quality analysis.
- Semantic diff between reports
- Quality metrics (evidence, coverage, contradiction detection)
- Change detection (new/modified/retracted claims)
- Storage of historical comparisons

### 4. Improvement Engine (improvement-engine/)
Self-refinement using 70B model.
- Gap analysis in current reports
- 70B-powered improvement suggestions
- Configuration implementation
- ROI tracking and feedback loop

### 5. Report Storage (reports-versioned/)
Structured versioning of all outputs.
- Each iteration: input, research, analysis, improvements
- Artifact preservation for reproducibility
- Aggregated views for trend analysis

## Configuration

Create `.env.autonomous` (from .env.autonomous.example):

    AUTONOMOUS_ENABLED=true
    AUTONOMOUS_DATA_SOURCES=file:///path/to/papers|web://arxiv.org
    AUTONOMOUS_ITERATION_INTERVAL_SECONDS=21600  # 6 hours
    HEXAMIND_LOCAL_MODEL_SMALL=llama3.1:8b
    HEXAMIND_LOCAL_MODEL_LARGE=llama3.1:70b-instruct-q4_K_M
    AUTONOMOUS_MIN_EVIDENCE_DEPTH=0.7
    AUTONOMOUS_IMPROVEMENT_MIN_DELTA=0.10
    AUTONOMOUS_ROLLBACK_IF_REGRESSION=true

## Running

Single iteration (test):
    python scripts/extract_and_research.py

Continuous loop:
    python scripts/run_autonomous_loop.py

## Storage Structure

    reports-versioned/
    ├── iterations/
    │   ├── iter-001-2026-04-04T10-30-abc123/
    │   │   ├── input/
    │   │   │   ├── source-data.json       # What was researched
    │   │   │   └── extraction-log.md
    │   │   ├── research/
    │   │   │   ├── full-report.md
    │   │   │   ├── agent-outputs/        # Individual agent outputs
    │   │   │   └── metadata.json          # Tokens, timing, models
    │   │   ├── analysis/
    │   │   │   ├── prev-comparison.md    # vs previous
    │   │   │   ├── quality-metrics.json
    │   │   │   └── gaps-identified.md
    │   │   ├── improvements/
    │   │   │   ├── suggestions.md         # 70B suggestions
    │   │   │   ├── applied-config.json    # What was applied
    │   │   │   └── roi-analysis.md        # Did it help?
    │   │   └── manifest.json
    │   └── iter-002-...
    └── aggregated/
        ├── topic-evolution.md
        ├── improvement-timeline.md
        ├── model-performance.json
        └── comparison-matrix.json

## Typical Iteration Flow

(1h30m total per iteration)

1. **Extract** (15min)
   - Poll configured sources
   - Parse PDFs, crawl web, fetch APIs
   - De-duplicate with local cache
   - Skip if already processed

2. **Research** (45min)
   - Advocate: Build upside case (10min, llama3.1:8b)
   - Skeptic: Identify risks (10min, llama3.1:8b)
   - Synthesiser: Integrate perspectives (15min, llama3.1:70b)
   - Oracle: Forecast scenarios (10min, llama3.1:70b)
   - Verifier: Audit evidence (10min, llama3.1:8b)

3. **Compare** (10min)
   - Semantic diff vs previous report
   - Extract claims from both versions
   - Identify new/modified/retracted claims

4. **Analyze** (10min)
   - Compute quality metrics
   - Evidence depth, source coverage, etc
   - Identify gaps

5. **Improve** (10min)
   - Feed gap analysis to llama3.1:70b
   - Get specific config suggestions
   - Evaluate expected ROI
   - Apply top suggestions if >10% improvement expected

6. **Store** (5min)
   - Save all outputs in versioned structure
   - Create iteration manifest
   - Update aggregated views

## Quality Gate Thresholds

By default, improvements trigger when:

    - Evidence depth < 0.7
    - Contradiction detection < 0.8
    - Source coverage < 0.85

Applied improvements only if expected ROI > 0.10 (10%)
Automatic rollback if regression detected

## Minimal Copilot Usage

- ✓ 0% fallback to external APIs (strict local)
- ✓ All reasoning via local llama3.1 models
- ✓ Embeddings via local nomic-embed-text
- ✓ No external LLM calls needed
- ✓ Copilot quota reserved for emergencies only

## Next Steps

1. Implement data extractors (PDFs, web crawl, APIs)
2. Integrate with ai-service/pipeline.py
3. Implement semantic diff using embeddings
4. Add 70B improvement suggestion prompts
5. Deploy configuration implementor
6. Test single iteration with real data
7. Monitor first autonomous loop run

## Monitoring

Key metrics to track:
- Iteration success rate
- Quality metric trajectories
- Configuration changes & their impact
- Token usage per iteration
- Model utilization (8b vs 70b time split)

Use aggregated reports for trend analysis.
"""

# This is a documentation file. No code to execute.
