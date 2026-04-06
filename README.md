# Hexamind Research Console

Hexamind is a high-fidelity, multi-agent research and synthesis platform. It uses a swarm of specialized AI agents to automate internet research, fact-verification, and structured reporting.

## 🚀 Fresh Start - April 6, 2026
This workspace has been reset to a "Fresh Start" state to begin the **70B Model Redesign**. All legacy documentation and temporary artifacts have been removed to focus on core AI integrations and deployment infrastructure.

## 🏗️ Architecture
- **Frontend**: Next.js 16 + React 19 (App Router). Features a node-based research canvas with a "Retro Pastel" aesthetic.
- **Backend**: FastAPI service (`ai-service/`). Handles agent orchestration, real-time research pipelines, and local model integration.
- **AI Stack**: Optimized for local models (e.g., Llama 3.1 70B) and internet retrieval via specialized connectors.

## 🛠️ Getting Started

### Local Development
1. **Frontend**:
   ```bash
   npm install
   npm run dev
   ```
2. **Backend**:
   ```bash
   # Create and activate venv
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r ai-service/requirements.txt
   
   # Start backend
   npm run dev:backend
   ```

### Deployment
- **Docker**: `docker-compose up --build`
- **Cloud**: Deployment-ready for Render via `render.yaml`.

## 📍 Core Capabilities
- **Multi-Agent Swarm**: Specialized roles for Advocacy, Skepticism, Synthesis, and Oracle reasoning.
- **Internet Grounding**: Real-time web retrieval with automated source citation.
- **Quality Gates**: Post-generation verification to ensure factual density and cohesion.
- **Research Canvas**: Interactive XYFlow-based visualization of agent progress.

---
*Cleaned and reset for the Hexamind 70B Redesign.*

