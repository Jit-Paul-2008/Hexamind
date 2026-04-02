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

Frontend defaults to backend `http://localhost:8000`. Override with:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Quality Checks

```bash
npm run lint
npm run build
```
