# Hexamind

Hexamind is a minimal full-stack multi-agent reasoning demo.

- Frontend: Next.js app router UI with a 4-agent canvas and live status widgets
- Backend: FastAPI service with pipeline session start + SSE event streaming

## Architecture

- `src/`: frontend app and UI state/store
- `ai-service/`: Python API service (`FastAPI` + `sse-starlette`)

The UI is a single full-window experience at `/` with the existing 4 agents:

1. Advocate
2. Skeptic
3. Synthesiser
4. Oracle

## API

- `GET /health` -> service health
- `GET /api/agents` -> agent metadata
- `POST /api/pipeline/start` -> create pipeline session
- `GET /api/pipeline/{sessionId}/stream` -> SSE events (`agent_start`, `agent_chunk`, `agent_done`, `pipeline_done`)

## Run Backend

This environment may require `--break-system-packages` for Python installs.

```bash
python3 -m pip install --user --break-system-packages -r ai-service/requirements.txt
python3 -m uvicorn main:app --app-dir ai-service --host 127.0.0.1 --port 8000
```

## Run Frontend

```bash
npm install
npm run dev
```

## Quick Start

If you want the easiest local check, do this:

1. Open the repo folder.
2. Copy this into a terminal and press Enter:

```bash
npm run dev:all
```

3. Open this in your browser after it starts:

```text
http://localhost:3000
```

If you want to use the free API later, put these values in the files below:

```text
frontend file: .env.local
backend file: .env
```

Paste this into `.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Paste this into `.env` if you want Gemini:

```bash
HEXAMIND_MODEL_PROVIDER=gemini
HEXAMIND_MODEL_NAME=gemini-2.0-flash
GOOGLE_API_KEY=your_free_google_ai_studio_key
HEXAMIND_WEB_RESEARCH=1
```

Frontend defaults to backend `http://localhost:8000`. Override with:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

For local development, put frontend values in a root `.env.local` file and backend
values in a root `.env` file. The backend loads `.env` automatically on startup.

Example root `.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Example root `.env` for the free Gemini path:

```bash
HEXAMIND_MODEL_PROVIDER=gemini
HEXAMIND_MODEL_NAME=gemini-2.0-flash
GOOGLE_API_KEY=your_free_google_ai_studio_key
HEXAMIND_WEB_RESEARCH=1
```

Example root `.env` for ARIA deep-research mode with per-agent model routing:

```bash
HEXAMIND_MODEL_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_key
HEXAMIND_MODEL_NAME=openai/gpt-4.1-mini
HEXAMIND_WEB_RESEARCH=1

# Optional role-specific overrides
HEXAMIND_AGENT_MODEL_ADVOCATE=google/gemini-2.5-flash-preview
HEXAMIND_AGENT_MODEL_SKEPTIC=anthropic/claude-3.7-sonnet
HEXAMIND_AGENT_MODEL_SYNTHESIS=openai/gpt-4.1
HEXAMIND_AGENT_MODEL_ORACLE=openai/o3-mini
HEXAMIND_AGENT_MODEL_FINAL=openai/gpt-4.1
```

Example root `.env` for fully local mode with an OpenAI-compatible local server:

```bash
HEXAMIND_MODEL_PROVIDER=local
HEXAMIND_MODEL_NAME=llama3.1:8b
HEXAMIND_LOCAL_BASE_URL=http://127.0.0.1:11434/v1
HEXAMIND_WEB_RESEARCH=1
```

To use this path, start a local model server first. Ollama is the easiest option:

```bash
ollama serve
ollama pull llama3.1:8b
```

If you already use LM Studio or another OpenAI-compatible local server, set `HEXAMIND_LOCAL_BASE_URL` to that server's `/v1` endpoint and keep `HEXAMIND_MODEL_NAME` aligned with the installed model tag.

Free-power tuning (recommended to maximize quality with free-tier keys):

```bash
HEXAMIND_COST_MODE=free
HEXAMIND_WEB_RESEARCH=1
HEXAMIND_RESEARCH_MAX_SOURCES=10
HEXAMIND_MAX_SOURCES_PER_DOMAIN=2
HEXAMIND_AUTO_REGENERATE_ON_FAIL=1

# Deep retrieval controls
HEXAMIND_RESEARCH_MAX_TERMS=10
HEXAMIND_RESEARCH_MAX_HITS_PER_TERM=8
HEXAMIND_RESEARCH_FETCH_CONCURRENCY=5
HEXAMIND_RESEARCH_MIN_RELEVANCE=0.24
HEXAMIND_RESEARCH_AUDIENCE=auto
HEXAMIND_TOKEN_MODE=smart
```

Workflow design reference:

- `src/docs/aria-free-power-workflow.md`
- `src/docs/free-api-setup-and-smoke-test.md`

Quality API for each completed session:

- `GET /api/pipeline/{sessionId}/quality`

## Quality Checks

```bash
npm run lint
npm run build
```

## Deployment

The project is ready for Docker-based deployment. Use the root `Dockerfile` for the
frontend and `ai-service/Dockerfile` for the backend, or run both with
`docker-compose.yml`.

Local Docker run:

```bash
docker compose up --build
```

Service URLs:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

Environment variables:

- `NEXT_PUBLIC_API_BASE_URL` is required for the frontend build. Set it to the public
	backend URL in production, or leave the default `http://localhost:8000` for local
	Docker usage.
- `HEXAMIND_MODEL_PROVIDER` is optional. Leave it as `deterministic` for a no-key
	deployment, or set it to `gemini` to use Google Gemini.
- `HEXAMIND_MODEL_NAME` is optional and only applies when `HEXAMIND_MODEL_PROVIDER`
	is set to `gemini`.

If you want the real model path, enter the Google API key in your platform's secret
store for the Gemini provider package. The deterministic mode needs no external API
key.
