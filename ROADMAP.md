# ARIA & NEXT.js UI Roadmap

This document outlines the architectural plan to support a 3D-heavy, infinite scroll website integrated with the ARIA AI structure.

## Architecture Decision

We have decided on a **decoupled architecture**:
1. **Frontend**: Next.js + React Three Fiber (for 3D) + Framer Motion (for animations).
2. **Backend**: Python (FastAPI/LangGraph) to run the ARIA AI agents.

## Repository Structure

The following directories have been created to support this architecture:
- `src/components/canvas/` (React Three Fiber components)
- `src/components/ui/` (2D components, forms, infinite scroll lists)
- `src/hooks/api/` (React Query/SWR hooks for fetching from python backend)
- `public/models/` (.gltf / .glb files)
- `public/textures/` (materials)
- `ai-service/` (Root directory for ARIA Python code)

## Development Options (Next Session)

When development begins, we can select one of these three tracks:

### Option A: The "Frontend-First" Track 
Focus on the visual "wow" factor first.
1. Install `three`, `@react-three/fiber`, `@react-three/drei`, and `framer-motion`.
2. Build a basic 3D scene (e.g., a floating interactive object).
3. Implement a dummy infinite scroll list overlaid on the 3D background.
4. Connect the backend later.

### Option B: The "AI-Backend First" Track (ARIA strict)
Focus on the intelligence first, UI later.
1. Initialize the `ai-service/` directory with `requirements.txt`.
2. Build the Advocate and Skeptic LangGraph agents.
3. Expose them via a FastAPI endpoint.
4. Build the 3D Next.js frontend to consume these endpoints.

### Option C: The "Full-Stack Slice" Track
Build one feature from front to back.
1. Setup Next.js.
2. Setup FastAPI.
3. Create a single 3D animated search bar that triggers an AI agent and streams the first response into an infinite scroll list.
