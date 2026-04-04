# ARIA Production-Ready Rollout Plan
## Claude-Style UX → Database → Governance

**Version:** 1.0  
**Created:** 2026-04-04  
**Status:** APPROVED FOR EXECUTION  
**Risk Level:** Medium (phased, reversible approach)

---

## 1. Title and Objective

**Project Name:** ARIA UX Transformation & Production Hardening  
**Primary Objective:** Transform ARIA from a backend-heavy research system into a production-ready, Claude-like user experience with workspace organization, persistence, collaboration, and enterprise governance.

**Success Criteria:**
- Users can create cases, run ARIA, inspect evidence/quality, and compare runs through an intuitive, organized interface
- All ARIA capabilities (Deep Research, Decision Brief, Model Compare, Scenario Test) are accessible through clean UI controls
- Database persistence enables workspace continuity, audit trails, and multi-user collaboration
- System meets production reliability, security, and observability standards

---

## 2. Current-State Diagnosis

### Verified Existing Strengths

**Backend Architecture (ai-service/):**
- FastAPI application with SSE streaming (`main.py` - 454 lines)
- 4-agent pipeline system (Advocate, Skeptic, Synthesiser, Oracle) via `agents.py` and `pipeline.py`
- Multi-provider model support (`model_provider.py`): Gemini, OpenRouter, Ollama, local models
- Research capabilities (`research.py`): Tavily/web integration
- Quality diagnostics (`quality.py`): Trust scores, evidence coverage
- Governance primitives (`governance.py`): Tenant resolution
- Sarvam integration (`sarvam_service.py`): Language transform + DOCX export
- Competitive benchmarking (`competitive_research.py`, `benchmarking.py`)

**Existing API Surface:**
| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/health` | GET | Service health + config | ✅ Working |
| `/api/agents` | GET | Agent metadata | ✅ Working |
| `/api/pipeline/start` | POST | Create pipeline session | ✅ Working |
| `/api/pipeline/{sessionId}/stream` | GET | SSE event streaming | ✅ Working |
| `/api/pipeline/{sessionId}/quality` | GET | Quality diagnostics | ✅ Working |
| `/api/pipeline/{sessionId}/sarvam-transform` | POST | Language transform | ✅ Working |
| `/api/pipeline/{sessionId}/export-docx` | POST | DOCX export | ✅ Working |
| `/api/models/status` | GET | Local model inventory | ✅ Working |
| `/api/benchmark/local` | GET | Local model benchmarks | ✅ Working |
| `/api/benchmark/competitive` | GET | Competitive analysis | ✅ Working |

**Security/Reliability Primitives (Verified in main.py):**
- Rate limiting via `HEXAMIND_RATE_LIMIT_PER_MINUTE` (lines 232-245)
- Auth token middleware via `HEXAMIND_AUTH_TOKEN` (lines 248-258)
- JSONL audit logging to `.data/audit-log.jsonl` (lines 262-288)
- Tenant resolution via `governance.py`
- CORS middleware configured (lines 38-44)

**Frontend Architecture (src/):**
- Next.js 16.2.2 with App Router (`src/app/`)
- React 19.2.4 with React Three Fiber for 3D visualization
- Zustand 5.0.12 for state management
- Framer Motion for animations
- TailwindCSS 4 for styling
- Current UI: Single-page canvas with 4 agent nodes (`page.tsx`)

### Verified Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| No workspace organization | Users cannot save/resume research | P0 |
| Transient state (in-memory only) | Data lost on restart | P0 |
| Single canvas UI | No evidence panels, history, comparisons | P0 |
| No user auth | Single-user only | P1 |
| No collaboration | No teams/sharing | P1 |
| Limited observability | No Prometheus metrics, dashboards | P2 |

---

## 3. Target End-State (Product + Technical)

### Product Vision: Claude-Like Experience

**Workspace Hierarchy:**
```
Organization
  └─ Projects (e.g., "Q2 Market Research")
      └─ Cases (e.g., "Is ARIA viable for healthcare?")
          └─ Runs (timestamped pipeline executions)
              ├─ Final Report
              ├─ Quality Metrics
              ├─ Sources
              └─ Agent Traces
```

**UI Layout Target:**
```
┌─────────────────────────────────────────────────────────────────┐
│ [Org Switcher]          ARIA                    [User] [Settings]│
├──────────────┬──────────────────────────────┬───────────────────┤
│              │                              │                   │
│  PROJECTS    │    CONVERSATION CENTER       │  EVIDENCE PANEL   │
│  └─ Cases    │                              │                   │
│     └─ Runs  │  [Mode: Deep Research ▼]     │  [Sources]        │
│              │                              │  [Quality]        │
│  [+ New]     │  Question/Response Area      │  [Contradictions] │
│              │  with streaming output       │  [Reasoning]      │
│              │                              │                   │
│              │  [Run ARIA] [Export] [Share] │                   │
│              │                              │                   │
├──────────────┴──────────────────────────────┴───────────────────┤
│ [Model: gemini-2.0-flash] [Cost: $0.002] [Status: ●]            │
└─────────────────────────────────────────────────────────────────┘
```

**ARIA Mode Controls:**
| Mode | Description | Backend Mapping |
|------|-------------|-----------------|
| Chat | Simple Q&A | Lightweight pipeline, no retrieval |
| Deep Research | Full 4-agent pipeline | Full pipeline with web research |
| Decision Brief | Structured pro/con | Custom prompt template |
| Compare Models | Parallel model runs | Multiple pipeline configs |
| Scenario Test | Batch variations | Sequential runs with diff |

### Technical End-State

**New Frontend Routes:**
```
/                           → Workspace home (project list)
/workspace/[projectId]      → Project view (case list)
/workspace/[projectId]/case/[caseId]  → Case view (run history + current)
/workspace/[projectId]/compare        → Side-by-side run comparison
/login                      → Authentication
/register                   → User registration
/settings                   → User/org settings
```

**New Backend Routes (v2 API):**
```
/api/v2/organizations       → CRUD for orgs
/api/v2/projects            → CRUD for projects
/api/v2/cases               → CRUD for cases
/api/v2/runs                → CRUD for runs (replaces sessionId)
/api/v2/runs/{runId}/stream → SSE streaming (DB-backed)
/api/v2/shares              → Share link management
/api/auth/*                 → Authentication endpoints
```

**Database (PostgreSQL):**
- 14 core tables across 6 domains
- Alembic migrations for version control
- SQLAlchemy async ORM
- Row-level security for multi-tenancy

---

## 4. Phase-by-Phase Rollout Plan

### Phase 0: Planning Validation
**Status:** ✅ Complete (this document)

**Deliverables:**
- [x] Architecture review completed
- [x] Current state verified against codebase
- [x] File touch boundaries defined
- [x] Rollout plan approved

---

### Phase 1: Claude-Style UX Shell (UI-Only, No DB)

**Objective:** Implement workspace navigation shell with mock data

**Entry Criteria:**
- Phase 0 complete
- Shadcn/ui component library selected
- Mock data schema defined

**Tasks:**
| ID | Task | Files Created | Files Modified |
|----|------|---------------|----------------|
| 1.1 | Install UI dependencies | - | `package.json` |
| 1.2 | Create workspace layout | `src/components/workspace/WorkspaceLayout.tsx` | `src/app/layout.tsx` |
| 1.3 | Build navigation tree | `src/components/workspace/NavigationTree.tsx` | - |
| 1.4 | Create project selector | `src/components/workspace/ProjectSelector.tsx` | - |
| 1.5 | Build case view | `src/components/case/CaseView.tsx` | - |
| 1.6 | Implement mode selector | `src/components/case/ModeSelector.tsx` | - |
| 1.7 | Create run history | `src/components/case/RunHistory.tsx` | - |
| 1.8 | Build evidence panel | `src/components/evidence/EvidencePanel.tsx` | - |
| 1.9 | Create sources list | `src/components/evidence/SourcesList.tsx` | - |
| 1.10 | Build quality metrics | `src/components/evidence/QualityMetrics.tsx` | - |
| 1.11 | Create contradiction view | `src/components/evidence/ContradictionView.tsx` | - |
| 1.12 | Build compare view | `src/components/compare/CompareView.tsx` | - |
| 1.13 | Create run diff | `src/components/compare/RunDiff.tsx` | - |
| 1.14 | Create Zustand stores | `src/store/workspaceStore.ts`, `src/store/caseStore.ts`, `src/store/runStore.ts`, `src/store/evidenceStore.ts` | - |
| 1.15 | Add workspace routes | `src/app/workspace/[projectId]/page.tsx`, `src/app/workspace/[projectId]/case/[caseId]/page.tsx`, `src/app/workspace/[projectId]/compare/page.tsx` | - |
| 1.16 | Create mock data | `src/lib/mock-data.ts` | - |
| 1.17 | Update Tailwind config | - | `tailwind.config.ts` |

**Exit Criteria:**
- [ ] `npm run build` exits 0
- [ ] `npm run lint` exits 0
- [ ] All 5 user flows navigable with mock data
- [ ] Evidence panel renders all tabs
- [ ] Comparison view shows mock diff
- [ ] No console errors

**File Touch Boundary (Phase 1):**
```
ALLOWED CREATE:
  src/components/workspace/**/*.tsx
  src/components/case/**/*.tsx
  src/components/evidence/**/*.tsx
  src/components/compare/**/*.tsx
  src/store/*.ts
  src/app/workspace/**/*.tsx
  src/lib/mock-data.ts

ALLOWED MODIFY:
  package.json (add Shadcn/ui dependencies)
  src/app/layout.tsx (add workspace routes)
  tailwind.config.ts (extend with design tokens)

FORBIDDEN:
  ai-service/** (no backend changes)
  src/app/page.tsx (preserve existing canvas)
```

**Risk Level:** Low (UI-only, reversible)

---

### Phase 2: Wire ARIA Capabilities to UI

**Objective:** Connect existing backend APIs to new UI components

**Entry Criteria:**
- Phase 1 complete
- Backend `/api/pipeline` routes functional
- SSE streaming tested

**Tasks:**
| ID | Task | Files Created | Files Modified |
|----|------|---------------|----------------|
| 2.1 | Create API client layer | `src/lib/api/pipeline.ts`, `src/lib/api/quality.ts`, `src/lib/api/models.ts`, `src/lib/api/export.ts` | - |
| 2.2 | Implement SSE client | `src/lib/sse-client.ts` | - |
| 2.3 | Add React Query | - | `package.json` |
| 2.4 | Create pipeline hooks | `src/hooks/usePipeline.ts`, `src/hooks/useQuality.ts`, `src/hooks/useModels.ts` | - |
| 2.5 | Wire mode selector | - | `src/components/case/ModeSelector.tsx` |
| 2.6 | Connect SSE streaming | - | `src/components/case/CaseView.tsx` |
| 2.7 | Integrate quality API | - | `src/components/evidence/EvidencePanel.tsx` |
| 2.8 | Add model status display | `src/components/status/ModelStatus.tsx`, `src/components/status/CostTracker.tsx` | - |
| 2.9 | Wire export buttons | - | `src/components/case/CaseView.tsx` |
| 2.10 | Create error boundary | `src/components/error/ErrorBoundary.tsx` | - |
| 2.11 | Replace mock stores | - | `src/store/runStore.ts` |

**Exit Criteria:**
- [ ] Users can select mode, start pipeline, see streaming results
- [ ] Evidence panel populates with live sources/quality
- [ ] Model status indicator shows provider health
- [ ] Export buttons trigger backend endpoints
- [ ] E2E test: Create case → run → inspect → export

**File Touch Boundary (Phase 2):**
```
ALLOWED CREATE:
  src/lib/api/*.ts
  src/lib/sse-client.ts
  src/hooks/*.ts
  src/components/status/*.tsx
  src/components/error/*.tsx

ALLOWED MODIFY:
  package.json (add @tanstack/react-query)
  src/components/case/*.tsx (wire to APIs)
  src/components/evidence/*.tsx (connect to quality API)
  src/store/*.ts (replace mock data)

FORBIDDEN:
  ai-service/** (no backend changes)
  src/app/page.tsx (preserve existing canvas)
```

**Risk Level:** Medium (integration complexity)

---

### Phase 3: Database Design, Migration, Persistence

**Objective:** Implement PostgreSQL schema and migrate to DB-backed storage

**Entry Criteria:**
- Phase 2 complete
- PostgreSQL instance available
- Schema design approved

**Database Schema:**

```sql
-- Domain 1: Identity & Access
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    owner_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE organization_members (
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (org_id, user_id)
);

-- Domain 2: Workspace
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    archived_at TIMESTAMPTZ
);

CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(300) NOT NULL,
    initial_question TEXT NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    archived_at TIMESTAMPTZ
);

-- Domain 3: Execution
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    session_id VARCHAR(100) UNIQUE,  -- Legacy compatibility
    mode VARCHAR(50) NOT NULL CHECK (mode IN ('chat', 'deep_research', 'decision_brief', 'compare', 'scenario')),
    config JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE run_events (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    agent_role VARCHAR(50),
    payload JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    sequence_number INTEGER NOT NULL,
    UNIQUE (run_id, sequence_number)
);

CREATE TABLE run_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    artifact_type VARCHAR(50) NOT NULL CHECK (artifact_type IN ('final_report', 'quality_report', 'docx_export')),
    content TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Domain 4: Knowledge
CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title VARCHAR(500),
    snippet TEXT,
    relevance_score REAL,
    domain VARCHAR(255),
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE quality_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE UNIQUE,
    trust_score REAL,
    evidence_coverage REAL,
    contradiction_count INTEGER DEFAULT 0,
    trace_coverage REAL,
    diagnostics JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE contradictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quality_report_id UUID REFERENCES quality_reports(id) ON DELETE CASCADE,
    statement_a TEXT NOT NULL,
    statement_b TEXT NOT NULL,
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high')),
    resolution_status VARCHAR(20) DEFAULT 'unresolved'
);

-- Domain 5: Collaboration
CREATE TABLE shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(20) NOT NULL CHECK (resource_type IN ('case', 'run')),
    resource_id UUID NOT NULL,
    share_token VARCHAR(64) UNIQUE NOT NULL,
    created_by UUID REFERENCES users(id),
    expires_at TIMESTAMPTZ,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Domain 6: Audit & Governance
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    org_id UUID REFERENCES organizations(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE change_history (
    id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    changed_by UUID REFERENCES users(id),
    changes JSONB NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_projects_org ON projects(org_id);
CREATE INDEX idx_cases_project ON cases(project_id);
CREATE INDEX idx_runs_case_started ON runs(case_id, started_at DESC);
CREATE INDEX idx_run_events_run_seq ON run_events(run_id, sequence_number);
CREATE INDEX idx_sources_run ON sources(run_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_shares_token ON shares(share_token);
```

**Tasks:**
| ID | Task | Files Created | Files Modified |
|----|------|---------------|----------------|
| 3.1 | Install DB dependencies | - | `ai-service/requirements.txt` |
| 3.2 | Create database module | `ai-service/database/__init__.py`, `ai-service/database/connection.py`, `ai-service/database/models.py` | - |
| 3.3 | Initialize Alembic | `ai-service/database/migrations/env.py`, `ai-service/alembic.ini` | - |
| 3.4 | Create initial migration | `ai-service/database/migrations/versions/001_initial_schema.py` | - |
| 3.5 | Create repository layer | `ai-service/database/repositories/*.py` | - |
| 3.6 | Add v2 API routes | `ai-service/api/routes/workspaces.py`, `ai-service/api/routes/projects.py`, `ai-service/api/routes/cases.py`, `ai-service/api/routes/runs.py` | - |
| 3.7 | Refactor pipeline persistence | - | `ai-service/pipeline.py`, `ai-service/main.py` |
| 3.8 | Update docker-compose | - | `docker-compose.yml` |
| 3.9 | Create seed script | `ai-service/database/seed.py` | - |
| 3.10 | Write migration tests | `ai-service/tests/test_migrations.py`, `ai-service/tests/test_repositories.py` | - |

**Exit Criteria:**
- [ ] `alembic upgrade head` succeeds
- [ ] `alembic downgrade -1` succeeds (tested on staging)
- [ ] All repository CRUD tests pass
- [ ] Case/run persists across page reload
- [ ] Pagination works (50 per page)
- [ ] No queries >500ms

**File Touch Boundary (Phase 3):**
```
ALLOWED CREATE:
  ai-service/database/**/*.py
  ai-service/api/routes/workspaces.py
  ai-service/api/routes/projects.py
  ai-service/api/routes/cases.py
  ai-service/api/routes/runs.py
  ai-service/tests/test_migrations.py
  ai-service/tests/test_repositories.py
  ai-service/alembic.ini

ALLOWED MODIFY:
  ai-service/requirements.txt (add sqlalchemy, alembic, asyncpg)
  ai-service/main.py (add DB lifecycle, register routes)
  ai-service/pipeline.py (add persistence hooks ONLY)
  docker-compose.yml (add postgres service)
  .env (add DATABASE_URL)

FORBIDDEN:
  ai-service/agents.py (preserve agent personas)
  ai-service/quality.py (preserve quality algorithm)
  ai-service/research.py (preserve retrieval logic)
  ai-service/benchmarking.py (preserve benchmark harness)
```

**Risk Level:** High (schema design, migration safety)

---

### Phase 4: Collaboration, Audit, Governance

**Objective:** Implement auth, RBAC, sharing, audit trails

**Entry Criteria:**
- Phase 3 complete and stable
- Security requirements reviewed
- RBAC model approved

**Tasks:**
| ID | Task | Files Created | Files Modified |
|----|------|---------------|----------------|
| 4.1 | Install auth dependencies | - | `ai-service/requirements.txt` |
| 4.2 | Create auth module | `ai-service/auth/__init__.py`, `ai-service/auth/password.py`, `ai-service/auth/jwt.py`, `ai-service/auth/middleware.py`, `ai-service/auth/dependencies.py` | - |
| 4.3 | Add auth routes | `ai-service/api/routes/auth.py` | - |
| 4.4 | Add org routes | `ai-service/api/routes/organizations.py` | - |
| 4.5 | Add share routes | `ai-service/api/routes/shares.py` | - |
| 4.6 | Create audit middleware | `ai-service/middleware/audit_logger.py` | - |
| 4.7 | Add RBAC to routes | - | `ai-service/api/routes/*.py` |
| 4.8 | Create frontend auth | `src/contexts/AuthContext.tsx`, `src/components/auth/*.tsx`, `src/app/login/page.tsx`, `src/app/register/page.tsx`, `src/lib/api/auth.ts`, `src/hooks/useAuth.ts` | - |
| 4.9 | Add protected routes | `src/components/auth/ProtectedRoute.tsx` | `src/app/layout.tsx` |
| 4.10 | Create org switcher | `src/components/workspace/OrganizationSwitcher.tsx`, `src/components/workspace/MemberManagement.tsx` | - |
| 4.11 | Create share UI | `src/components/share/ShareLinkGenerator.tsx` | - |
| 4.12 | Write security tests | `ai-service/tests/test_auth.py`, `ai-service/tests/test_rbac.py` | - |

**Exit Criteria:**
- [ ] Users can register, login, receive JWT
- [ ] RBAC enforced (viewers cannot create cases)
- [ ] Share links work for public access
- [ ] Audit logs capture all state changes
- [ ] Security scan passes (no high/critical vulnerabilities)

**File Touch Boundary (Phase 4):**
```
ALLOWED CREATE:
  ai-service/auth/**/*.py
  ai-service/api/routes/auth.py
  ai-service/api/routes/organizations.py
  ai-service/api/routes/shares.py
  ai-service/middleware/audit_logger.py
  ai-service/tests/test_auth.py
  ai-service/tests/test_rbac.py
  src/contexts/AuthContext.tsx
  src/components/auth/**/*.tsx
  src/components/workspace/OrganizationSwitcher.tsx
  src/components/workspace/MemberManagement.tsx
  src/components/share/*.tsx
  src/app/login/page.tsx
  src/app/register/page.tsx
  src/lib/api/auth.ts
  src/hooks/useAuth.ts

ALLOWED MODIFY:
  ai-service/requirements.txt (add passlib, python-jose)
  ai-service/main.py (add auth middleware)
  ai-service/api/routes/*.py (add permission checks)
  ai-service/database/repositories/*.py (add filtering)
  src/app/layout.tsx (add AuthContext)
  .env (add JWT_SECRET_KEY)

FORBIDDEN:
  ai-service/pipeline.py core logic
  ai-service/agents.py
  ai-service/quality.py
```

**Risk Level:** High (security implementation)

---

### Phase 5: Performance, Observability, Release

**Objective:** Optimize, monitor, and safely release

**Entry Criteria:**
- Phase 4 complete
- Load test environment ready
- Monitoring stack selected

**Tasks:**
| ID | Task | Description |
|----|------|-------------|
| 5.1 | Add Redis caching | Session caching, API response caching |
| 5.2 | Optimize queries | Fix N+1, add eager loading |
| 5.3 | Add Prometheus metrics | Request counts, latency histograms |
| 5.4 | Create health endpoints | `/health/liveness`, `/health/readiness` |
| 5.5 | Set up Grafana dashboards | System health, user activity, pipeline performance |
| 5.6 | Configure alerting | Error rate, latency, resource usage |
| 5.7 | Implement feature flags | Gradual rollout control |
| 5.8 | Run load tests | 100 concurrent users, P95 <5s |
| 5.9 | Test rollback procedure | Feature flag toggle, DB downgrade |
| 5.10 | Execute gradual rollout | 10% → 25% → 50% → 100% |

**Exit Criteria:**
- [ ] Load test passes (P95 <5s, error rate <1%)
- [ ] Prometheus scraping metrics
- [ ] Grafana dashboards display live data
- [ ] Alerting rules tested
- [ ] Feature flags functional
- [ ] Rollback tested on staging
- [ ] 72-hour smoke test passes

**Risk Level:** Medium (performance regression, rollout coordination)

---

## 5. UX Information Architecture

### Core User Flows

**Flow 1: Create Case → Run ARIA**
```
1. Login → Workspace Home
2. Select/Create Project
3. Click "New Case" → Enter question
4. Select Mode (Deep Research)
5. Click "Run ARIA"
6. View streaming results (center)
7. Inspect sources/quality (right panel)
8. Export report
```

**Flow 2: Compare Two Runs**
```
1. Open Case with multiple runs
2. Click "Compare" → Multi-select
3. Select Run 1 and Run 2
4. View side-by-side diff
5. Compare sources, quality metrics
6. Export comparison
```

**Flow 3: Resume Previous Work**
```
1. Open Workspace Home
2. Browse Recent Cases (starred)
3. Select previous case
4. View run history
5. Click "Continue" or "Fork"
```

---

## 6. Capability Exposure Map

| Backend Capability | UI Control | Endpoint |
|--------------------|-----------|----------|
| 4-agent pipeline | Mode: "Deep Research" | `/api/pipeline/start` |
| SSE streaming | Center panel live text | `/api/pipeline/{id}/stream` |
| Quality diagnostics | Evidence → Quality tab | `/api/pipeline/{id}/quality` |
| Web research | Evidence → Sources tab | Embedded in quality |
| Multi-provider | Settings → Model Config | `/api/models/status` |
| Sarvam transform | Export → Transform | `/api/pipeline/{id}/sarvam-transform` |
| DOCX export | Export → Download | `/api/pipeline/{id}/export-docx` |
| Benchmarks | Model selector → Benchmarks | `/api/benchmark/local` |

---

## 7. Validation Matrix

### Phase 1 Validation

| Test | Command | Expected | Gate |
|------|---------|----------|------|
| Build | `npm run build` | Exit 0 | REQUIRED |
| Lint | `npm run lint` | Exit 0 | REQUIRED |
| Navigation | Manual: `/workspace/mock` | Tree renders | REQUIRED |
| Mode selector | Manual: Click dropdown | 5 modes visible | REQUIRED |
| Evidence panel | Manual: Case view | 4 tabs render | REQUIRED |

### Phase 2 Validation

| Test | Command | Expected | Gate |
|------|---------|----------|------|
| Backend health | `curl localhost:8000/health` | 200 OK | REQUIRED |
| SSE streaming | Manual: Run Deep Research | Live text appears | REQUIRED |
| Quality populates | Manual: After run | Trust score displays | REQUIRED |
| Export works | Manual: Download DOCX | File downloads | REQUIRED |

### Phase 3 Validation

| Test | Command | Expected | Gate |
|------|---------|----------|------|
| Migration up | `alembic upgrade head` | Exit 0 | REQUIRED |
| Migration down | `alembic downgrade -1` | Exit 0 | REQUIRED |
| Repository tests | `pytest tests/test_repositories.py` | All pass | REQUIRED |
| Persistence | Refresh page after run | Data persists | REQUIRED |
| Query perf | Slow query log | All <500ms | REQUIRED |

### Phase 4 Validation

| Test | Command | Expected | Gate |
|------|---------|----------|------|
| Auth tests | `pytest tests/test_auth.py` | All pass | REQUIRED |
| RBAC tests | `pytest tests/test_rbac.py` | All pass | REQUIRED |
| Protected routes | No token → `/api/v2/projects` | 401 | REQUIRED |
| Share access | Open share link | Public view works | REQUIRED |
| Audit capture | Check audit_logs table | Entries exist | REQUIRED |

### Phase 5 Validation

| Test | Command | Expected | Gate |
|------|---------|----------|------|
| Load test | `./scripts/run-load-test.sh` | P95 <5s, err <1% | REQUIRED |
| Metrics endpoint | `curl localhost:8000/metrics` | Prometheus format | REQUIRED |
| Health check | `curl localhost:8000/health/readiness` | 200 + all healthy | REQUIRED |
| Feature flag | Toggle flag | UI switches | REQUIRED |
| Rollback | Disable flag | Old UI loads | REQUIRED |

---

## 8. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation | Rollback |
|----|------|-----------|--------|-----------|----------|
| R1 | UX confuses users | M | M | Beta testing with 5 users | Feature flag disable |
| R2 | SSE disconnects | H | M | Auto-reconnect logic | N/A (client-side) |
| R3 | Migration fails | L | H | Test on staging, dual-write | `alembic downgrade` |
| R4 | N+1 queries | M | H | Query analysis, eager load | Optimize before release |
| R5 | Auth bypass | L | Critical | Security audit, pen test | Immediate flag disable |
| R6 | API breaks | M | H | v1 shims, deprecation | Keep v1 active |
| R7 | Cache stale data | M | M | Conservative TTL (5min) | Clear cache |
| R8 | Load spike | M | M | Rate limiting, queue | Scale up or throttle |

---

## 9. Release Strategy

### Rollout Phases

| Phase | Audience | Duration | Success Criteria |
|-------|----------|----------|-----------------|
| Alpha | Internal (10) | 7 days | No P0/P1 bugs |
| Beta | Selected (50) | 14 days | NPS ≥7 |
| 10% | Random sample | 3 days | Error <1% |
| 25% | Expand | 3 days | Metrics stable |
| 50% | Expand | 4 days | Metrics stable |
| 100% | Full launch | - | - |

### Rollback Triggers

- Error rate >2% for 10 min → Auto-rollback
- P0 bug (data loss, security) → Manual rollback
- Quality regression >20% → Pause, investigate

### Rollback Procedure

1. Disable `ENABLE_NEW_UI` flag (instant)
2. If DB issue: `alembic downgrade -1`
3. Redeploy previous Docker tag
4. Verify health checks
5. Notify users

---

## 10. Out-of-Scope (Must Not Touch)

### Forbidden Files
- `ai-service/benchmarking.py`
- `ai-service/agents.py` (agent personas)
- `ai-service/quality.py` (quality algorithm)
- `ai-service/research.py` (retrieval logic)
- `comparison-engine/`, `comparison_engine/`
- `improvement-engine/`, `improvement_engine/`
- `research-automation/`, `research_automation/`
- `reports-versioned/`
- `ARIA_Complete_Build_Guide.docx`
- `ARIA_Healthcare_AI_Report.txt`

### Forbidden Changes
- Agent personalities (Advocate, Skeptic, Synthesiser, Oracle)
- Quality scoring algorithm
- Retrieval/research logic
- Benchmark harness
- Cost tracking formulas

### Not In Scope
- New agent personas
- Billing/payment integration
- Third-party integrations (Slack, Teams)
- Admin analytics dashboards

---

## 11. Definition of Done

### Per-Phase Gates

**Phase 1:** ✅ when:
- `npm run build` && `npm run lint` pass
- All 5 flows navigable with mock data
- Lighthouse accessibility ≥90

**Phase 2:** ✅ when:
- E2E test passes (create → run → inspect → export)
- SSE streaming works with reconnection
- All API errors handled gracefully

**Phase 3:** ✅ when:
- Migrations up/down tested
- All repository tests pass
- Persistence verified across refresh
- No queries >500ms

**Phase 4:** ✅ when:
- Auth/RBAC tests pass
- Security scan clean
- Audit logs capturing
- Share links functional

**Phase 5:** ✅ when:
- Load test passes
- Metrics/dashboards operational
- Alerting configured
- Rollback tested
- 72-hour smoke test passes

### Global Done Criteria
- [ ] All requirements traced to files and tests
- [ ] Documentation updated (API docs, README)
- [ ] Runbooks prepared
- [ ] Stakeholder sign-off obtained

---

## 12. Execution Contract

### Anti-Drift Commitments

**I commit to the following:**

1. **File Boundary Discipline:**
   - I will NOT modify files outside the approved touch map for each phase
   - Any scope expansion requires explicit user approval
   - I will maintain a change ledger for every modification

2. **No Random Refactors:**
   - I will NOT perform unrelated code cleanup or style changes
   - Pre-existing technical debt will be documented, not fixed

3. **Requirement Traceability:**
   - Every code change maps to a stated requirement
   - Every requirement maps to a validation test

4. **Validation Before Progression:**
   - I will run all phase validation commands before marking complete
   - I will NOT proceed if REQUIRED gates fail

5. **Backward Compatibility:**
   - I will maintain v1 API endpoints with shims
   - I will add deprecation headers before removal

6. **Scope Conflict Resolution:**
   - I will STOP and ask for clarification on ambiguity
   - I will NOT silently deviate from the plan

7. **Risk Preparedness:**
   - Rollback procedures verified before each phase exit
   - Feature flags enable instant rollback

8. **Change Ledger Delivery:**
   - At phase end: files created, modified, tests added, validation results

### Final Accountability

- This plan is the single source of truth
- Deviations require explicit approval
- Execution begins upon user confirmation

---

## Appendix: Quick Reference

### Commands Cheat Sheet

```bash
# Phase 1
npm install
npm run build
npm run lint
npm run dev

# Phase 2
curl http://localhost:8000/health
npm run test:e2e

# Phase 3
alembic upgrade head
alembic downgrade -1
pytest tests/test_repositories.py
psql $DATABASE_URL -c "\dt"

# Phase 4
pytest tests/test_auth.py
pytest tests/test_rbac.py

# Phase 5
./scripts/run-load-test.sh
curl http://localhost:8000/metrics
curl http://localhost:8000/health/readiness
```

### Environment Variables

```bash
# Database (Phase 3+)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/aria

# Auth (Phase 4+)
JWT_SECRET_KEY=your-secure-random-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis (Phase 5)
REDIS_URL=redis://localhost:6379

# Feature Flags
ENABLE_NEW_UI=false
ENABLE_DATABASE_PERSISTENCE=false
```

---

**END OF ROLLOUT PLAN**

*This document is the authoritative reference for the ARIA UX transformation project. All implementation work must adhere to this plan.*
