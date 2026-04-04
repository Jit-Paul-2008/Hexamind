# ARIA UX Architecture Decision Records (ADRs)

**Format:** ADR [Status] — Decision Title

---

## ADR-001 [ACCEPTED] — Database Choice: PostgreSQL with SQLAlchemy ORM

**Date:** 2026-04-04  
**Supercedes:** N/A  
**Superseded By:** N/A  
**Authors:** Engineering Team  

### Context

ARIA previously used in-memory session storage. For production readiness with multi-user support, we needed:
- Persistent data across server restarts
- Multi-tenancy support (organizations, projects, cases)
- ACID compliance for financial/audit data
- Transactional consistency for concurrent users

### Decision

Use **PostgreSQL** as primary database with **SQLAlchemy 2.0 ORM** in async mode (`asyncpg` driver).

### Rationale

| Criteria | PostgreSQL | MongoDB | DynamoDB |
|----------|-----------|---------|----------|
| Transactions | ✅ Full ACID | ⚠️ Limited | ❌ No |
| Schema Drifts | ✅ Enforced | ❌ Free-form | ⚠️ Limited |
| Cost (prod) | ✅ ~$50/mo | ⚠️ ~$100/mo | ❌ ~$200/mo |
| Async Support | ✅ asyncpg | ⚠️ Motor | ❌ Limited |
| Learning Curve | ⚠️ Medium | ✅ Low | ❌ High |

### Consequences

**✅ Advantages:**
- Strong consistency guarantees (no data races)
- Powerful query optimization (indices, EXPLAIN ANALYZE)
- Audit trail support via triggers
- Free tier available (Supabase, Railway)

**⚠️ Trade-offs:**
- Requires schema migrations (Alembic)
- Slower startup (connection pooling overhead)
- More DevOps complexity than SQLite

**✅ Mitigations:**
- Alembic for safe schema versioning
- PgBouncer for connection pooling
- Automated backups via RDS/Supabase

### Alternative Approaches Considered

1. **MongoDB** — Rejected due to lack of transactions
2. **Redis only** — Rejected, high memory cost at scale
3. **SQLite** — Used for development/testing only

### Implementation Notes

- Primary: PostgreSQL 14+
- Development: SQLite for local testing
- ORM: SQLAlchemy 2.0 with async (`sqlalchemy[asyncio]`)
- Migrations: Alembic with auto-migration support
- Connection: asyncpg driver with pooling
- Backup: Nightly to S3

---

## ADR-002 [ACCEPTED] — Authentication: JWT + Passlib + HTTPBearer

**Date:** 2026-04-04  
**Authors:** Engineering Team  

### Context

ARIA requires stateless authentication for scale (no session server). Options:
1. JWT tokens (stateless, scalable)
2. Session cookies (stateful, requires session store)
3. OAuth2 (delegated, limits control)

### Decision

Use **JWT (JSON Web Tokens)** with:
- **python-jose** for JWT creation/validation
- **passlib** with pbkdf2_sha256 for password hashing
- **HTTPBearer** for token extraction from Authorization header

### Rationale

| Aspect | JWT | Sessions | OAuth2 |
|--------|-----|----------|--------|
| Stateless | ✅ | ❌ | ✅ |
| Scalable | ✅ | ⚠️ | ✅ |
| Revocation | ⚠️ Slow | ✅ Fast | ❌ Slow |
| Setup Complexity | ✅ Low | ⚠️ Medium | ❌ High |
| User Control | ✅ | ✅ | ❌ |

### Configuration

```python
JWT_SECRET_KEY = "secure-random-32+-char-key"  # Generated via openssl rand -hex 32
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
```

### Consequences

**✅ Pros:**
- No session server needed (scale to millions)
- Can validate at every microservice
- Works with mobile/SPA apps natively

**⚠️ Cons:**
- Tokens can't be revoked instantly (exp time is revocation delay)
- Token size in URL (JWT is ~500 bytes)
- No built-in refresh token flow in python-jose

**✅ Mitigations:**
- Short expiry (30 min) + refresh tokens (7 days)
- Blacklist critical tokens in Redis if revocation needed
- Use Authorization header (not URL params)

### Password Hashing Choice

**pbkdf2_sha256** over bcrypt:
- ✅ Works in restricted environments (no bcrypt C extension)
- ✅ Standard (PBKDF2 in NIST spec)
- ⚠️ Slightly faster (bcrypt safer but overkill for auth endpoints)
- Iteration count: 29000 (OWASP minimum)

### Refresh Token Flow (Future)

```
POST /api/auth/login
  → Returns: access_token (30 min), refresh_token (7 days)

When access_token expired:
POST /api/auth/refresh
  body: refresh_token
  → Returns: new access_token

When logout:
POST /api/auth/logout
  body: refresh_token
  → Revokes refresh_token in Redis
```

---

## ADR-003 [ACCEPTED] — API Versioning: v1 (Legacy) + v2 (Current)

**Date:** 2026-04-04  
**Authors:** Engineering Team  

### Context

ARIA had backwards-incompatible API changes:
- v1: Session-based (`/api/pipeline/start` returns sessionId)
- v2: Run-based (`/api/v2/runs` CRUD with database backing)

Must support both during transition (old clients still work).

### Decision

Maintain both versions:
- **v1:** Legacy endpoints unchanged (deprecated marker)
- **v2:** New standardized REST API with database models

Routes:
```
/api/pipeline/start          # v1 (legacy)
/api/pipeline/{sessionId}/*  # v1 (legacy)

/api/v2/organizations        # v2 (current)
/api/v2/projects             # v2 (current)
/api/v2/cases                # v2 (current)
/api/v2/runs                 # v2 (current)
/api/v2/shares               # v2 (current)
```

### Rationale

| Approach | Cost | Compatibility |
|----------|------|---------------|
| Parallel (v1+v2) | ✅ Low | ✅ Smooth |
| Shim Layer | ⚠️ Medium | ⚠️ Fragile |
| Hard Cut | ❌ High | ❌ Breakage |

### Migration Path

**Phase 1 (Current):** Both endpoints live
**Phase 2 (Month 2):** v1 deprecated (warning headers)
**Phase 3 (Month 3):** v1 removed

### Deprecation Headers

```
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sun, 01 Jun 2026 02:00:00 GMT
Link: </api/v2/...>; rel="successor-version"
Content-Type: application/json
```

### Consequences

**✅ Pros:**
- Zero breaking changes for existing clients
- Gradual migration period
- Can run both versions in canary

**⚠️ Cons:**
- Double maintenance burden (both code paths)
- Risk of divergence (bug in v1 not in v2)
- Memory/code size increases

**✅ Mitigations:**
- Clear deprecation timeline (3 months)
- v1 → v2 shim if possible (thin wrapper)
- Monitoring of v1 usage (metrics per endpoint)

---

## ADR-004 [ACCEPTED] — Frontend State Management: Zustand + React Hooks

**Date:** 2026-04-04  
**Authors:** Engineering Team  

### Context

ARIA frontend needs to manage:
- Workspace state (org, project, case selection)
- Pipeline state (current run, streaming output)
- Evidence state (sources, quality metrics)
- UI state (modal visibility, sort order)

Options: Redux, Zustand, Recoil, Jotai, Context API

### Decision

Use **Zustand** with React Hooks pattern:
```typescript
// Example: usePipeline hook
const usePipeline = () => {
  const [state, setState] = useState({...});
  const [isRunning, setIsRunning] = useState(false);
  
  const run = async (question) => {...};
  const updateQuality = (report) => {...};
  
  return { state, isRunning, run, updateQuality };
};
```

Multiple stores:
- `workspaceStore.ts` — org/project/case selection
- `caseStore.ts` — current case details
- `runStore.ts` — run list and current run
- `evidenceStore.ts` — sources, quality, contradictions

### Rationale

| Library | Bundle | Learning | Debugging | Type Safety |
|---------|--------|----------|-----------|-------------|
| Redux | ❌ 15KB | ❌ Hard | ✅ DevTools | ⚠️ Manual |
| Zustand | ✅ 2KB | ✅ Easy | ⚠️ Basic | ✅ Auto |
| Recoil | ⚠️ 10KB | ⚠️ Medium | ⚠️ Limited | ✅ Auto |
| Context API | ✅ Built-in | ✅ Easy | ❌ None | ⚠️ Manual |

### Consequences

**✅ Pros:**
- Minimal boilerplate (~50 lines for a store)
- Excellent TypeScript support
- Works perfectly with custom hooks
- Tiny bundle size (2KB)

**⚠️ Cons:**
- No built-in time travel debugging (like Redux DevTools)
- Less ecosystem tooling than Redux
- Requires discipline to avoid tight coupling

**✅ Mitigations:**
- Custom debugging hook `useDebugStore`
- Clear separation of concerns (one store per domain)
- Strict TypeScript for type safety

---

## ADR-005 [ACCEPTED] — Database Migrations: Alembic with Automatic DDL

**Date:** 2026-04-04  
**Authors:** Engineering Team  

### Context

Need safe schema versioning:
- Can roll forward/backward
- Audit trail of all schema changes
- No surprise breaking changes

### Decision

Use **Alembic** (SQLAlchemy's migration tool):

```bash
# Auto-generate migrations from model changes
alembic revision --autogenerate -m "add_user_phone_number"

# Apply to database
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

### Structure

```
ai-service/database/
  ├── migrations/
  │   ├── versions/
  │   │   ├── 001_initial_schema.py
  │   │   ├── 002_add_user_phone.py
  │   │   └── ...
  │   └── env.py
  ├── models.py          # SQLAlchemy models
  └── connection.py      # Engine/session factory
```

### Rationale

Alembic features:
- ✅ Version tracking in `alembic_version` table
- ✅ Automatic DDL generation from SQLAlchemy models
- ✅ Manual migration support for complex changes
- ✅ Batch operations (rename column safely)
- ✅ Integrated with FastAPI lifecycle

### Consequences

**✅ Pros:**
- History of all schema changes
- Safe rollbacks (downgrade with old code)
- No manual SQL (less error-prone)

**⚠️ Cons:**
- Requires discipline (always use Alembic, not raw SQL)
- Auto-generated migrations need review
- Learning curve for Alembic specifics

**✅ Mitigations:**
- Code review all migrations before apply
- Test migrations on staging first
- Keep downgrade path working

### Dangerous Migrations

Avoid these without thinking:
```python
# ❌ Don't: Dropping column without backup
op.drop_column('users', 'old_field')

# ✅ Do: Rename with batch operator
with op.batch_alter_table('users') as batch_op:
    batch_op.alter_column('old_field', new_column_name='new_field')

# ❌ Don't: Large batch update (will lock table)
op.execute("UPDATE users SET role='member' WHERE role IS NULL")

# ✅ Do: Break into batches
connection = op.get_bind()
for i in range(0, 1000000, 10000):
    connection.execute(...)
```

---

## ADR-006 [ACCEPTED] — Real-Time Updates: Server-Sent Events (SSE) + Polling Fallback

**Date:** 2026-04-04  
**Authors:** Engineering Team  

### Context

ARIA: needs real-time pipeline streaming:
- Show agent output as it happens (per-token)
- Emit source discovery events
- Signal completion

Options:
1. WebSockets (stateful, complex)
2. SSE (stateless, simple)
3. Polling (wasteful, laggy)
4. GraphQL Subscriptions (overkill)

### Decision

Use **Server-Sent Events (SSE)** for:
- V1 `/api/pipeline/{sessionId}/stream` endpoint
- Parse newline-delimited JSON events
- Auto-reconnect on disconnect

### Event Format

```
data: {"event_type":"agent_start","agent_role":"advocate","timestamp":"2026-04-04T..."}
data: {"event_type":"agent_output","output":"Strategic...", "chunk":true}
data: {"event_type":"source_added","url":"https://...", "title":"..."}
data: {"event_type":"pipeline_complete","final_answer":"...", "total_cost":0.25}
```

### Implementation

**Backend (FastAPI):**
```python
@app.get("/api/pipeline/{sessionId}/stream")
async def stream_pipeline(sessionId: str):
    async def event_generator():
        # ... fetch session
        for event in session.events:
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

**Frontend (React):**
```javascript
const usePipeline = () => {
  const [output, setOutput] = useState('');
  
  const run = async (question) => {
    const response = await fetch(`/api/pipeline/${sessionId}/stream`);
    const reader = response.body.getReader();
    
    reader.read().then(function processEvent({ done, value }) {
      if (done) return;
      const text = new TextDecoder().decode(value);
      const event = JSON.parse(text.replace('data: ', ''));
      
      if (event.event_type === 'agent_output') {
        setOutput(prev => prev + event.output);
      }
    });
  };
};
```

### Consequences

**✅ Pros:**
- Stateless (no connection tracking)
- Efficient (HTTP long-polling alternative)
- Works through proxies/CDNs
- Native browser API (EventSource)

**⚠️ Cons:**
- One-way only (client can't send mid-stream)
- Limited reconnection logic (manual)
- No binary data (JSON only)

**✅ Mitigations:**
- Implement graceful reconnection with exponential backoff
- For bidirectional: keep separate control HTTP API
- For binary: Base64 encode or use HTTP POST with chunking

---

## ADR-007 [ACCEPTED] — Observability: Prometheus Metrics with Liveness/Readiness Probes

**Date:** 2026-04-04  
**Authors:** Engineering Team  

### Context

Need to:
- Monitor request latency
- Track error rates
- Know if service is healthy (for Kubernetes)

### Decision

Implement three layers:

**1. Liveness Probe** — Is the service alive?
```
GET /health/liveness → 200 "alive"
Used by: Kubernetes to restart dead pods
```

**2. Readiness Probe** — Can it handle traffic?
```
GET /health/readiness → 200 (if DB connected, else 503)
Used by: Kubernetes load balancer routing
```

**3. Prometheus Metrics** — Performance data
```
GET /metrics → Prometheus format
Metrics: hexamind_http_requests_total, hexamind_http_request_duration_seconds
```

### Rationale

| Tool | Liveness | Readiness | Metrics |
|------|----------|-----------|---------|
| Application Insights | ⚠️ No | ⚠️ No | ✅ Yes |
| Prometheus | ✅ Yes | ✅ Yes | ✅ Yes |
| New Relic | ✅ Yes | ✅ Yes | ✅ Yes |
| Datadog | ✅ Yes | ✅ Yes | ✅ Yes |

### Implementation

```python
# Middleware to instrument all requests
@app.middleware("http")
async def add_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)
    
    return response
```

### Consequences

**✅ Pros:**
- Complete visibility into performance
- Detect issues before users do
- Works with any monitoring stack (Prometheus, Datadog, etc.)
- Kubernetes-native

**⚠️ Cons:**
- Metrics can itself add latency (~2-5ms per request)
- Requires monitoring setup (Prometheus, Grafana)
- Potential metrics explosion (high cardinality endpoints)

**✅ Mitigations:**
- Use summary/histogram (not gauge for each request)
- Label endpoints, not raw paths (avoid cardinality explosion)
- Sample slow requests only if needed

---

## ADR-008 [ACCEPTED] — Feature Flags: Environment-Based (Memory) Provider

**Date:** 2026-04-04  
**Authors:** Engineering Team  

### Context

Need ability to:
- Gradually roll out new features
- Kill feature instantly if bad
- A/B test with percentage rollout

### Decision

For **Phase 1-3:** Environment-based feature flags (simplest)

```bash
# .env
FLAG_ENABLE_NEW_UI=true
FLAG_ENABLE_DATABASE_PERSISTENCE=false
FLAG_ENABLE_SSO_GOOGLE=false
```

For **Phase 4+:** Can upgrade to:
- LaunchDarkly (enterprise)
- Unleash (open-source)
- Local Redis (custom)

### Implementation

```python
# ai-service/config.py
class FeatureFlags:
    ENABLE_NEW_UI = os.getenv("FLAG_ENABLE_NEW_UI", "false").lower() == "true"
    ENABLE_DATABASE_PERSISTENCE = ...
    
    @classmethod
    def is_enabled(cls, flag: str) -> bool:
        return getattr(cls, flag, False)

# Usage in routes
@app.get("/api/feature-flags")
async def get_flags():
    return {
        "enable_new_ui": FeatureFlags.ENABLE_NEW_UI,
        "enable_persistence": FeatureFlags.ENABLE_DATABASE_PERSISTENCE,
    }

# Frontend
const { enable_new_ui } = await fetch("/api/feature-flags").then(r => r.json());
if (enable_new_ui) {
    <NewWorkspaceUI />
} else {
    <LegacyCanvasUI />
}
```

### Consequences

**✅ Pros:**
- Zero overhead (compile-time constants)
- No external dependency
- Easy to understand

**⚠️ Cons:**
- Requires app restart to change flags
- No percentage rollout (0% or 100%)
- No per-user flags

**✅ Mitigations:**
- Use environment-based rollout only for Phase 1-2
- Upgrade to LaunchDarkly after Phase 3 if needed
- For gradual rollout, use Kubernetes replicas instead

---

## ADR-009 [PROPOSED] — Caching Strategy: Redis for Sessions + HTTP Cache Headers

**Date:** 2026-04-04  
**Authors:** Engineering Team  
**Status:** PROPOSED (Phase 5)

### Context

As traffic grows, need to reduce database load:
- Expensive queries (quality reports)
- Session data (current user)
- Static data (organizations, project metadata)

### Proposal

Use **Redis** for caching:
- Session tokens (TTL: 7 days, matches refresh token)
- Quality reports (TTL: 1 hour, per run)
- Organization metadata (TTL: 24 hours)

Plus HTTP cache headers:
```
Cache-Control: public, max-age=3600  # for /api/models/status
Cache-Control: private, max-age=300  # for /api/v2/projects (user-specific)
Cache-Control: no-cache             # for /api/pipeline/*/quality (always fresh)
```

### Rationale

| Layer | What | TTL | Hit Rate |
|-------|------|-----|----------|
| Browser | Organization, models | 24h | 80% |
| CDN | Public endpoints | 1h | 60% |
| App | Session tokens | 7d | 90% |
| Redis | Quality reports | 1h | 75% |
| Database | Source of truth | - | - |

### Consequences

**✅ Pros:**
- 3-5x reduction in DB load
- <100ms latency (Redis vs 500ms DB)

**⚠️ Cons:**
- Stale data risk (if TTL too long)
- Cache invalidation complexity
- Additional infrastructure (Redis)

**Implementation Status:** Planned for Phase 5

---

## ADR-010 [PROPOSED] — Disaster Recovery: Multi-Region Failover

**Date:** 2026-04-04  
**Authors:** Engineering Team  
**Status:** PROPOSED (Post-GA)

### Context

For production SLA (99.9% uptime), need disaster recovery:
- Primary region fails
- Data center outage
- Entire cloud provider issue

### Proposal

**Passive Failover** (initially):
1. Primary database: PostgreSQL in us-east-1
2. Replica: PostgreSQL in us-west-1 (read-only)
3. On failure: DNS failover to us-west-1, promote replica to primary

**Advantages:**
- RPO: ~30 seconds (replication lag)
- RTO: ~5 minutes (DNS propagation)
- Cost: +30% (one replica)

### Alternative: Active-Active (Future)

Both regions serve traffic, conflicts resolved via CRDTs.
Cost: +100%, complexity: very high.

### Consequences

**✅ Pros:**
- Can survive single region outage
- Achieves 99.99% SLA

**⚠️ Cons:**
- Data replication lag
- DNS failover manual or slow
- Need monitoring for replica health

**Implementation Status:** Planned for post-GA

---

## Cross-Cutting Decisions

### Error Handling Strategy

**Frontend:**
- Toast notifications for user errors (400, 4xx)
- Modal dialogs for critical errors (500, 5xx)
- Automatic retry for transient errors (503, timeout)

**Backend:**
- All errors return JSON: `{"error": "...", "error_code": "...", "details": {...}}`
- Status codes follow REST conventions (400, 401, 403, 404, 409, 429, 500, 503)
- Errors logged to Sentry + audit logs

### Naming Conventions

**Database:**
- Tables: `snake_case`, plural (users, cases, run_events)
- Columns: `snake_case`, singular (user_id, case_name)
- Indexes: `idx_{table}_{columns}` (idx_users_email)
- Foreign keys: `{table}_{referenced_table}_id` (case_project_id)

**API:**
- Paths: `/api/{version}/{resource}/{id}` (GET /api/v2/projects/123)
- Query params: `snake_case` (sort_by, created_after)
- Request/response: `camelCase` in JSON (userId, createdAt)

**Code:**
- Classes: `PascalCase`, nouns (PipelineRunner, CaseView)
- Functions: `snake_case`, verbs (run_pipeline, update_case)
- Constants: `UPPER_SNAKE_CASE` (DB_POOL_SIZE, JWT_SECRET_KEY)
- React components: `PascalCase`.tsx (CaseView.tsx)

### Logging Strategy

- **Development:** `console.log` + structured JSON to stdout
- **Production:** JSON to CloudWatch/ELK with correlation IDs
- **Sensitive data:** Never log passwords, tokens, PII
- **Performance:** Special logging for queries >500ms, requests >5s

### Testing Strategy

- **Unit:** Functions in isolation (utilities, helpers)
- **Integration:** API endpoints + database (TestClient)
- **E2E:** Full user workflows (Playwright)
- **Load:** Sustained traffic simulation (load-test.py)

---

**Document Status:** Living document, updated as new decisions made.  
**Last Updated:** 2026-04-04
