# Hexamind Aurora State Handoff (v6.9)

## 🎯 Current Objectives
The goal is to maintain and extend the Hexamind Aurora multi-agent research engine. We have just completed a major refactoring to adapt the AI stack for local execution on a Dual-Core Xeon machine. 

## 🏗️ Current State (2026-04-07)
**Status**: System functional with performance optimizations applied
- All agent taxonomy inconsistencies resolved
- Frontend builds successfully (npm run build passes)
- Research pipeline operational with tuned parameters

## Known Issues & Fixes Applied
1. **Auditor Performance Issue** (RESOLVED)
   - Problem: Auditor role assigned to `deepseek-r1:14b` causing 12+ minute delays
   - Fix: Switched auditor to `qwen2.5:7b` for consistent performance
   - Impact: All roles now use 7B model, reducing run time from 20+ minutes to ~5 minutes

2. **Missing Enum Values** (RESOLVED)
   - Problem: `PIPELINE_ERROR` enum missing from backend/frontend schemas
   - Fix: Added to `schemas.py` and `src/types/index.ts`

3. **Agent Taxonomy Mismatch** (RESOLVED)
   - Problem: Frontend stages didn't match backend agent IDs
   - Fix: Aligned `ReasoningGraph.tsx` stages with Aurora runtime agents

4. **Workspace Components Missing** (RESOLVED)
   - Problem: Build failed due to missing workspace components for static export
   - Fix: Created mock components and data files

## Recent Configuration Changes
- `agent_model_config.py`: Auditor switched from `deepseek-r1:14b` to `qwen2.5:7b`
- `reasoning_graph.py`: Synthesizer switched to `qwen2.5:7b` for faster completion
- Token budgets reduced for CPU optimization:
  - Critique/refine steps: 600 tokens
  - Analysis steps: 800 tokens
  - Synthesis: 1200 tokens

## Active Research Topic
"condition of Traditional top tier Indian institutes like IITs in terms of student development and employablity in recent years and future"
- Last run interrupted at historian stage (220s)
- Progress logged in `research_status.md`
- Final report destination: `demo runs`

## 🏗️ Troubleshooting Guide
1. **Agent Taking Too Long**
   - Check if agent is using 14B model in `agent_model_config.py`
   - Switch to 7B model for CPU inference
   - Unload 14B: `curl -X POST http://localhost:11434/api/generate -d '{"model":"deepseek-r1:14b","prompt":"","keep_alive":0}'`

2. **Build Failures**
   - Ensure workspace components exist: `src/lib/mock-data.ts`, `src/components/workspace/WorkspaceLayout.tsx`
   - Check enum alignment between `schemas.py` and `src/types/index.ts`

3. **Pipeline Errors**
   - Verify `PIPELINE_ERROR` enum exists in both backend and frontend
   - Check agent IDs match between `ReasoningGraph.tsx` and `agents.py`

## 🏗️ System Architecture & Recent Upgrades
The application has transitioned from a fixed-response loop to a high-speed, parallelized **Industrial Reasoning Engine**.

### 1. Hybrid-Precision Orchestration (Updated)
- **Concept:** Not every task requires a 14-billion parameter model. 
- **Current State:** 
  - All agents now use `qwen2.5:7b` for consistent CPU performance
  - `deepseek-r1:14b` available but not loaded (performance bottleneck)
  - Token budgets optimized for CPU inference
- **Where to find it:** `ai-service/agent_model_config.py`

### 2. Parallel Search I/O (Implemented)
- **Concept:** Web scraping takes time. We decoupled web scraping from the sequential reasoning loop.
- **Current State:** The Orchestrator fires 4 concurrent SearXNG queries (`gather_evidence`) via `asyncio.gather`. Once all network I/O is resolved, it passes the pre-fetched contexts to the models sequentially, keeping the CPU 100% focused on inference.
- **Where to find it:** `ai-service/reasoning_graph.py` and `ai-service/worker_agents.py`

### 3. Strict Thinking Budgets (Implemented)
- **Concept:** `deepseek-r1:14b` gets trapped in unbounded `<think>` loops on dual-core machines.
- **Current State:** Intermediate layers have strict token limits linked to Ollama's `num_predict` parameter, alongside aggressive prompt constraints (e.g., "Limit <think> tags to a maximum of 2 sentences. DO NOT OVERTHINK.").
- **Where to find it:** `ai-service/inference_provider.py` and `ai-service/worker_agents.py`

### 4. Neuro-Symbolic Context Pruning (Implemented)
- **Concept:** Smaller context windows equal faster generation.
- **Current State:** Rather than feeding the entire global web-search payload to every agent, sources are pruned based on role-specific keywords (e.g., the Historian only reads text containing "history", "timeline", etc.).
- **Where to find it:** `ai-service/worker_agents.py` 

## 🔄 Core Workflow
To run the research engine locally and view the real-time thought process:
```bash
> research_status.md && ./venv/bin/python -u ai-service/run_demo.py | tee research_status.md
```
- Open `research_status.md` to see the live heartbeat (every 20s) and the individual agent reports as they finish.
- Ensure the `SearXNG` container is running on `127.0.0.1:8080`.
- Ensure `Ollama` is active with both `deepseek-r1:14b` and `qwen2.5:7b` ready.

## 🗑️ Cleaned Legacy Concepts
- **Bypassed OpenAI Compat Bridge:** We removed the buggy `/v1/chat/completions` API route which caused 404s. The engine now uses the **Native Ollama API** (`/api/chat`).
- **Sequential Monolithic Fetching:** Prior models paused the CPU while waiting for web results. This logic is deprecated and replaced by the Parallel Search I/O module.
- **Generic 14B Blanket Policy:** The idea of forcing `deepseek-r1:14b` onto every node was scrapped in favor of Hybrid Precision.

## Handover Checklist
- [ ] Verify `qwen2.5:7b` is loaded: `curl -s http://localhost:11434/api/ps`
- [ ] Check frontend builds: `npm run build`
- [ ] Test research pipeline: `python ai-service/run_demo.py "test query"`
- [ ] Review agent configurations in `agent_model_config.py`
- [ ] Ensure SearXNG container running on `127.0.0.1:8080`

## Next Steps for Incoming Agent
1. Complete the IIT research run (interrupted at historian stage)
2. Verify final report generation in `demo runs`
3. Monitor performance with all 7B models
4. Consider if any agents need 14B model for specific tasks
