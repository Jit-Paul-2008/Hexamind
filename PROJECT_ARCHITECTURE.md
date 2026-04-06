# ARIA Project Architecture - Complete Overview

## Project Structure & Components

### 1. Frontend (React/Next.js)
**Location:** `/src/`
**Deployment:** GitHub Pages (`https://jit-paul-2008.github.io/Hexamind`)
**Purpose:** User interface for research queries and report visualization

**Key Files:**
- `src/app/layout.tsx` - Main app layout
- `src/app/page.tsx` - Homepage with query input
- `src/components/` - UI components (pipeline visualization, report display)
- `src/lib/agents.ts` - Agent metadata for frontend visualization
- `src/hooks/` - React hooks for API calls
- `public/` - Static assets

**How it works:**
1. User enters query and clicks "Start Research"
2. Frontend calls `/api/pipeline/start` to create session
3. Opens Server-Sent Events connection to `/api/pipeline/{session}/stream`
4. Displays real-time agent progress in visual graph
5. Shows final report in "Report" tab and technical details in "Technical" tab

---

### 2. Backend (FastAPI/Python)
**Location:** `/ai-service/`
**Deployment:** Systemd service on VM (`http://20.196.129.73:8000`)
**Purpose:** Research pipeline orchestration and agent execution

**Key Files:**
- `main.py` - FastAPI app entry point, API routes
- `pipeline.py` - Core pipeline logic, agent orchestration
- `governance.py` - Framework version selection and agent sequence logic
- `agents.py` - Agent configuration metadata
- `model_provider.py` - Local Ollama model integration
- `agent_model_config.py` - Per-agent model configurations
- `database/models.py` - Research context and session models
- `auth/` - JWT authentication (currently disabled)

**How it works:**
1. `/api/pipeline/start` creates new session with query
2. `/api/pipeline/{session}/stream` streams real-time events
3. Pipeline runs agents based on framework version (v1/v2/v3)
4. Agents use local Ollama models via HTTP API
5. Results streamed back as SSE events

---

### 3. Search Service (SearXNG)
**Location:** Docker container
**Deployment:** `http://127.0.0.1:8080`
**Purpose:** Privacy-preserving web search without API keys

**Configuration:** `/searxng-config/settings.yml`
- Searches multiple search engines
- Returns structured results with URLs, titles, snippets
- No tracking or API limits

---

### 4. Model Service (Ollama)
**Location:** System service
**Deployment:** `http://127.0.0.1:11434`
**Purpose:** Local LLM inference (no external APIs)

**Models Available:**
- `mistral:7b` - Fast agent model (researcher, critic)
- `llama3.1:70b-instruct-q4_K_M` - Large final synthesis model
- `llama3.1:8b` - Medium model (currently unused)

---

## Data Flow Architecture

```
User Query → Frontend → Backend Pipeline → Research → Agents → Final Report
     ↓              ↓              ↓           ↓        ↓         ↓
   React       FastAPI       SearXNG     Ollama    Ollama    React UI
```

### Detailed Flow:

1. **Query Input**
   - User enters query in React frontend
   - Frontend sends POST to `/api/pipeline/start`
   - Backend creates session with unique ID

2. **Research Retrieval**
   - Pipeline calls SearXNG API with query terms
   - SearXNG searches multiple engines
   - Returns structured source list (URLs, titles, snippets)
   - Sources stored in ResearchContext

3. **Agent Execution**
   - Framework version determines agent sequence:
     - v1: Single synthesiser agent
     - v2: 5 agents (advocate → skeptic → synthesiser → oracle → verifier)
     - v3: 2 agents (researcher → critic)
   - Each agent gets query + research context
   - Agents call Ollama models via HTTP
   - Results collected as agent outputs

4. **Final Synthesis**
   - Large model (llama3.1:70b) processes all agent outputs
   - Generates comprehensive final report
   - Includes citations and technical metadata

5. **Response Streaming**
   - All events streamed via Server-Sent Events
   - Frontend updates UI in real-time
   - Shows agent progress and final results

---

## Configuration & Environment

### Backend Environment (`.env.local`)
```bash
# Framework selection
HEXAMIND_FRAMEWORK_VERSION=v3  # v1/v2/v3

# Model assignments
HEXAMIND_LOCAL_MODEL_SMALL=mistral:7b      # Agent models
HEXAMIND_LOCAL_MODEL_LARGE=llama3.1:70b     # Final model

# Performance tuning
HEXAMIND_STREAM_MAX_CONCURRENT=10
HEXAMIND_AGENT_TIMEOUT_SECONDS=600
HEXAMIND_STAGE_TIMEOUT_AGENT_SECONDS=550

# Research parameters
HEXAMIND_RESEARCH_MAX_SOURCES=2
HEXAMIND_RESEARCH_MAX_TERMS=2
HEXAMIND_RESEARCH_MAX_HITS_PER_TERM=2

# Service URLs
HEXAMIND_SEARXNG_BASE_URL=http://127.0.0.1:8080
HEXAMIND_OLLAMA_BASE_URL=http://127.0.0.1:11434
```

### Frontend Configuration
- Backend URL hardcoded: `https://20.196.129.73:8000`
- CORS enabled for GitHub Pages domain
- No authentication required

---

## Service Connections

### Network Architecture
```
Internet → GitHub Pages (Frontend)
    ↓ HTTPS API calls
VM (20.196.129.73) → Nginx (HTTPS termination) → Backend (Port 8000)
    ↓ Local calls
Backend → SearXNG (Port 8080) → Ollama (Port 11434)
```

### Service Dependencies
- **Frontend** depends on: Backend API
- **Backend** depends on: SearXNG, Ollama
- **SearXNG** depends on: External search engines
- **Ollama** depends on: Local GPU/CPU resources

---

## Framework Versions

### V1: Single-Pass (Fast)
- **Agents:** 1 (synthesiser)
- **Time:** ~2-3 minutes
- **Quality:** Good, single perspective
- **Use case:** Quick queries, simple topics

### V2: Multi-Agent (Comprehensive)
- **Agents:** 5 (advocate → skeptic → synthesiser → oracle → verifier)
- **Time:** ~25+ minutes (CPU-only)
- **Quality:** Excellent, multiple perspectives
- **Use case:** Complex analysis, high-stakes decisions

### V3: Two-Brain (Balanced)
- **Agents:** 2 (researcher → critic)
- **Time:** ~4-6 minutes
- **Quality:** Good with bias control
- **Use case:** General purpose, balanced analysis

---

## Deployment Architecture

### Production Services
1. **GitHub Pages** - Frontend hosting (free)
2. **VM (20.196.129.73)** - All backend services
   - Nginx (HTTPS termination)
   - Systemd (backend service)
   - Docker (SearXNG)
   - Ollama (model serving)

### Service Management
```bash
# Backend service
sudo systemctl restart hexamind-backend

# SearXNG Docker
docker restart searxng

# Ollama service
sudo systemctl restart ollama
```

---

## Data Storage

### Temporary Data
- **Sessions:** In-memory only (no persistence)
- **Research Context:** Stored during pipeline execution
- **Agent Outputs:** Collected for final synthesis

### No Databases
- No user accounts or history
- No persistent storage
- Each query is independent

---

## Security & Privacy

### Privacy Features
- **Local models:** No data sent to external APIs
- **SearXNG:** No tracking, private search
- **No logging:** Queries not stored
- **HTTPS:** Encrypted communication

### Security Considerations
- Public backend endpoint (no authentication)
- No rate limiting
- No input validation beyond basic checks
- CORS restricted to GitHub Pages

---

## Monitoring & Debugging

### Health Endpoint
`GET /health` returns:
- Agent model mappings
- Timeout configurations
- Active stream count
- Circuit breaker status

### Logs
```bash
# Backend logs
sudo journalctl -u hexamind-backend -f

# Ollama logs
sudo journalctl -u ollama -f
```

### Debug Mode
Set `HEXAMIND_DEBUG=1` in environment for verbose logging.

---

## Development Workflow

### Making Changes
1. Backend: Edit files in `/ai-service/`
2. Restart service: `sudo systemctl restart hexamind-backend`
3. Frontend: Edit files in `/src/`
4. Deploy: `git push origin main` (auto-deploys to GitHub Pages)

### Testing
```bash
# Backend health
curl http://localhost:8000/health

# Pipeline test
curl -X POST http://localhost:8000/api/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"query":"test query","reportLength":"brief"}'
```

---

## Current Implementation Status

### ✅ Completed
- V1 framework (single agent)
- V2 framework (5 agents)
- V3 framework (2 agents) - NEW
- Local model integration
- SearXNG search integration
- Real-time streaming UI
- HTTPS deployment
- Basic error handling

### 🚧 In Progress
- V3 framework optimization (timeout issues)
- Agent prompt refinement
- Performance tuning

### ❌ Not Implemented
- User authentication
- Query history
- Export features
- Advanced monitoring
- Load balancing

---

## Key Technical Decisions

1. **Local-first architecture** - No external API dependencies
2. **CPU-only inference** - Works without GPU but slower
3. **Sequential execution** - Prevents resource contention
4. **Framework versioning** - Allows switching between speed/quality
5. **Streaming responses** - Real-time user feedback
6. **Free deployment stack** - GitHub Pages + VM + Docker

This architecture prioritizes privacy, cost-efficiency, and simplicity over enterprise features.
