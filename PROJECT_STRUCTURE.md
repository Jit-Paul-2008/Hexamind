# Hexamind Project Structure

## Directory Organization

### Frontend (`/src`)
- `app/` - Next.js pages and layouts
- `components/` - Reusable React components
  - `canvas/` - 3D visualization components
  - `ui/` - UI controls and indicators
- `hooks/` - Custom React hooks
- `lib/` - Utility libraries and state management
- `types/` - TypeScript type definitions
- `docs/` - Documentation and guides

### Backend (`/ai-service`)
- `agents.py` - Agent definitions and orchestration
- `benchmarking.py` - Performance evaluation suite
- `competitive_research.py` - Multi-provider comparison
- `governance.py` - PII redaction and policies
- `knowledge_cache.py` - Local offline knowledge storage
- `main.py` - FastAPI application entry
- `model_provider.py` - LLM provider abstractions
- `pipeline.py` - Research pipeline orchestration
- `prompt_registry.py` - Cached system prompts
- `quality.py` - Report quality analysis
- `research.py` - Internet research and evidence gathering
- `sarvam_service.py` - Translation and document export
- `schemas.py` - Data models and Pydantic schemas
- `workflow.py` - Workflow profile and research strategy
- `.data/` - Runtime data and artifacts
  - `reports/` - Generated research reports
  - `benchmarks/` - Benchmark run results
  - `reports-archive/` - Older/duplicate reports
  - `benchmarks-archive/` - Older/duplicate benchmarks

### Scripts (`/scripts`)
- `run_benchmarks.py` - Benchmark suite runner
- `run_competitive_research.py` - Multi-model comparison runner
- `run_local_random_topic_iterations.py` - Iterative tuning harness
- `generate_one_topic_report.py` - Single-run report generation
- `dev-all.mjs` - Development server launcher

### Testing (`/tests`)
- `unit/` - Unit tests for frontend utilities
- `e2e/` - End-to-end contract tests
- `ai-service/tests/` - Backend unit tests

### Configuration
- `package.json` - Node.js dependencies and scripts
- `tsconfig.json` - TypeScript configuration
- `next.config.ts` - Next.js build config
- `eslint.config.mjs` - Linting rules
- `postcss.config.mjs` - CSS processing
- `Dockerfile`, `docker-compose.yml` - Container configuration

## Known Redundancy Issues
1. **Duplicate reports**: Multiple batches of run01-run10 at different timestamps
2. **Duplicate benchmarks**: Multiple benchmark versions for same run numbers
3. **Early test report**: random-topic-full-report-20260404-035511.md (no run label)

## Cleanup Plan
1. Archive old batch reports (04:12-05:39 timestamps) to `reports-archive/`
2. Archive old batch benchmarks to `benchmarks-archive/`
3. Keep latest batch (05:54+ timestamps) as primary
4. Delete remaining duplicates after archival confirmation
5. Update symlinks or references to point to latest batch

## Environment & Configuration
- **Python**: 3.12, venv at .venv/
- **Node**: 16+, uses npm for package management
- **Local Models**: Ollama integration for llama3.1:8b, qwen2.5:7b, etc.
- **APIs**: OpenRouter (GPT, Gemini), Tavily (web search), Sarvam (translation)
- **Token Mode**: Lean (cost-optimized)
- **Retrieval**: max_sources=13, max_hits_per_term=9, min_relevance=0.2
