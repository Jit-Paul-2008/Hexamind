# Hexamind Aurora State Handoff (v6.8)

## 🎯 Current Objectives
The goal is to maintain and extend the Hexamind Aurora multi-agent research engine. We have just completed a major refactoring to adapt the AI stack for local execution on a Dual-Core Xeon machine. 

## 🏗️ System Architecture & Recent Upgrades
The application has transitioned from a fixed-response loop to a high-speed, parallelized **Industrial Reasoning Engine**.

### 1. Hybrid-Precision Orchestration (Implemented)
- **Concept:** Not every task requires a 14-billion parameter model. 
- **Current State:** 
  - `qwen2.5:7b` is used for front-line data gathering tasks (`historian`, `researcher`, `verifier`, `advocate`).
  - `deepseek-r1:14b` is reserved exclusively for deep reasoning tasks (`auditor`, `synthesiser`, `critic`, `skeptic`).
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
