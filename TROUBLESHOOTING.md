# ARIA UX Troubleshooting Guide

**Quick Reference:** Use Ctrl+F to search for your error message.

---

## Frontend Issues

### "Cannot GET /workspace"

**Symptoms:** User navigates to `/workspace` but gets 404 or blank page

**Solutions:**

```bash
# 1. Check if Next.js built correctly
npm run build
# Should return exit code 0

# 2. Check if routes are registered
grep -r "workspace" src/app --include="*.tsx"
# Should show: src/app/workspace/[projectId]/page.tsx

# 3. Check getStaticParams is defined (if using static generation)
grep -A5 "getStaticParams" src/app/workspace/\[projectId\]/page.tsx

# 4. Verify layout structure
cat src/app/layout.tsx | grep -A 10 "export default"

# 5. If using App Router, ensure no conflicting page.tsx
find src/app -name "page.tsx" | wc -l
# workspace should have at least 3 page.tsx files

# 6. Clear Next.js cache
rm -rf .next/
npm run build
npm run dev
```

### "useAuth hook only works inside AuthContext"

**Symptoms:** Error when calling `useAuth()` in a component

**Solutions:**

```bash
# 1. Verify AuthContext is wrapping components
grep -r "AuthProvider" src/app/layout.tsx
# Should show: <AuthProvider>...</AuthProvider>

# 2. Check AuthContext import
grep "import.*AuthContext" src/contexts/AuthContext.tsx

# 3. Verify provider is in layout.tsx, not just app.tsx
grep "AuthProvider" src/app/layout.tsx
# Should output non-empty

# 4. Check for nested layout issues
cat src/app/workspace/layout.tsx | grep -i "provider\|context"
# workspace layout might be overriding parent provider

# 5. Solution: Wrap workspace layout with auth
# Edit src/app/workspace/layout.tsx to inherit parent providers
```

### "Streaming output not appearing"

**Symptoms:** User runs case but nothing appears in the UI

**Solutions:**

```bash
# 1. Check backend is running
curl http://localhost:8000/health
# Should return { status: "ok" }

# 2. Check API endpoint in frontend
grep "NEXT_PUBLIC_API_URL" .env.local
# Should be correct (http://localhost:8000 for dev)

# 3. Check if SSE connection is opening
# Open DevTools → Network → Filter "EventStream"
# Find the `/api/pipeline/{sessionId}/stream` request
# Should show Status 200 and "Text" tab showing events

# 4. Check if sessionId is valid
grep -A 20 "usePipeline" src/hooks/usePipeline.ts | grep sessionId
# sessionId should come from /api/pipeline/start response

# 5. Test SSE endpoint manually
curl -N http://localhost:8000/api/pipeline/{sessionId}/stream \
  -H "Authorization: Bearer $TOKEN"
# Should output streaming events like:
# data: {"event_type":"agent_start",...}

# 6. Check browser console for CORS errors
# If you see "Cross-Origin Request Blocked"
# Update CORS_ORIGINS in backend .env

# 7. Check for SSE connection timeouts
# If request shows as "pending" but no response
# Backend might not be writing events
# Check ai-service/main.py for SSE implementation
```

### "Cost tracker shows $0.00"

**Symptoms:** User runs pipeline but cost is always 0

**Solutions:**

```bash
# 1. Check cost tracking is implemented
grep -r "cost" src/lib/api/pipeline.ts
# Should show cost calculation logic

# 2. Verify model costs are configured
grep -r "COST_PER" .env.example
# Should show: COST_PER_INPUT_TOKEN, COST_PER_OUTPUT_TOKEN

# 3. Check run quality report includes cost
curl http://localhost:8000/api/pipeline/{sessionId}/quality
# Response should include: "total_cost": 0.125 (not 0)

# 4. Verify backend is calculating costs
# Check ai-service/pipeline.py line where costs are calculated
grep -A 10 "total_cost\|calculate_cost" ai-service/pipeline.py

# 5. If still 0, enable cost tracking in feature flags
python scripts/seed-feature-flags.py
# Verify: enable_cost_tracking = true

# 6. Test cost calculation locally
python -c "
from ai_service.pipeline import calculate_cost
result = calculate_cost(
    input_tokens=1000,
    output_tokens=500,
    model='gemini-2.0-flash'
)
print(f'Cost: ${result}')
"
```

### "Elements not rendering (blank white page)"

**Symptoms:** Page loads but components don't show

**Solutions:**

```bash
# 1. Check for TypeScript errors
npm run typecheck

# 2. Check for build errors
npm run build 2>&1 | grep -E "error|Error"

# 3. Check for missing dependencies
grep "import.*from" src/components/case/CaseView.tsx | \
  while read line; do
    lib=$(echo "$line" | grep -oP "'[^']+'" | head -1 | tr -d "'")
    npm ls "$lib" >/dev/null 2>&1 || echo "Missing: $lib"
  done

# 4. Check for circular imports
npm run lint | grep -i "circular"

# 5. Check React error boundary
grep -r "ErrorBoundary" src/app/layout.tsx
# Should show ErrorBoundary wrapping children

# 6. Debug in browser console
# Open DevTools → Console
# Look for React errors: "Cannot read property 'x' of undefined"
# Usually means missing optional chaining (?.

# 7. Check for null data
# If DataStore component shows blank:
grep -A 20 "data\?" src/components/*/index.tsx |
grep -E "data\?.length|data\?.map"
# Should use optional chaining everywhere

# 8. Verify fallback/loading states
grep -B 5 "return " src/components/case/CaseView.tsx |
grep -E "loading|pending"
# If status.loading returned early, should show loading state
```

---

## Backend Issues

### "alembic: command not found"

**Symptoms:** Running `alembic` in terminal doesn't work

**Solutions:**

```bash
# 1. Activate venv
source .venv/bin/activate

# 2. Verify alembic installed
pip list | grep alembic
# Should show: alembic 1.13.1

# 3. If not installed, install it
pip install alembic sqlalchemy

# 4. Use full path instead
python -m alembic --version

# 5. Add to PATH permanently
alias alembic='python -m alembic'
# Add to ~/.bashrc for persistence
```

### "sqlalchemy.exc.OperationalError: (sqlite3.DatabaseError) database disk image is malformed"

**Symptoms:** Database file is corrupted

**Solutions:**

```bash
# 1. Backup corrupted database (just in case)
cp aria.db aria.db.corrupt.backup

# 2. Remove corrupted database
rm aria.db
rm aria.db-wal
rm aria.db-shm

# 3. Reinitialize
alembic upgrade head
python scripts/db-seed-dev.py

# 4. If using production SQLite, convert to PostgreSQL
# Edit DATABASE_URL in .env
# DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# 5. Test connection
python -c "
import asyncio
from ai_service.database.connection import async_engine
async def test():
    async with async_engine.connect() as conn:
        result = await conn.execute('SELECT 1')
        print(result.fetchall())
asyncio.run(test())
"
```

### "CORS error: Cross-Origin Request Blocked"

**Symptoms:** Frontend API calls blocked with CORS error

**Solutions:**

```bash
# 1. Check CORS config in backend
grep -A 5 "CORSMiddleware" ai-service/main.py

# 2. Update CORS allowed origins
# Edit .env:
CORS_ORIGINS='["http://localhost:3000","http://localhost:3001"]'

# 3. Verify frontend URL is in CORS list
echo $NEXT_PUBLIC_APP_URL
# Should match one of the CORS_ORIGINS

# 4. Test CORS preflight
curl -X OPTIONS http://localhost:8000/api/v2/projects \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -v
# Should return 200 with Access-Control-* headers

# 5. Check if credentials are being sent
grep "credentials:" src/lib/api/pipeline.ts
# Should have: credentials: 'include'

# 6. For production, use exact domain
sed -i "s|http://localhost|https://app.aria.example.com|g" .env.production
```

### "JWT token has expired"

**Symptoms:** User gets 401 "token expired" after a period of time

**Solutions:**

```bash
# 1. Check token expiry setting
grep "ACCESS_TOKEN_EXPIRE" .env.local
# Default: 30 minutes

# 2. Verify token creation includes exp claim
grep -A 10 "create_access_token" ai-service/auth/jwt.py
# Should include: "exp": datetime.utcnow() + timedelta(...)

# 3. Check if frontend is refreshing token
grep -r "refresh" src/hooks/useAuth.ts
# Should attempt to call /api/auth/refresh before token expires

# 4. Test token manually
python -c "
from ai_service.auth.jwt import create_access_token
from jose import jwt
import os

token = create_access_token({'sub': 'test@example.com'})
decoded = jwt.decode(
    token,
    os.getenv('JWT_SECRET_KEY'),
    algorithms=[os.getenv('JWT_ALGORITHM', 'HS256')]
)
print(f'Token expires at: {decoded[\"exp\"]}')
from datetime import datetime
print(f'Current time: {datetime.utcnow().timestamp()}')
"

# 5. For long-running sessions, implement refresh token flow
# Edit auth.py to issue refresh tokens alongside access tokens

# 6. For testing, increase token expiry
export ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours
python main.py
```

### "No module named 'ai_service'"

**Symptoms:** Import error when running Python scripts

**Solutions:**

```bash
# 1. Verify you're in correct directory
pwd
# Should be: /home/Jit-Paul-2008/Desktop/Hexamind

# 2. Add project to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 3. Verify ai-service folder exists
ls -la ai-service/__init__.py

# 4. Activate venv
source .venv/bin/activate

# 5. Try import
python -c "from ai_service.main import app; print('OK')"

# 6. If still failing, reinstall dependencies
pip install -e ai-service/
```

### "Database connection pool is exhausted"

**Symptoms:** "asyncpg.exceptions.TooManyConnectionsError"

**Solutions:**

```bash
# 1. Check current connections
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME <<EOF
SELECT count(*) FROM pg_stat_activity;
SELECT datname, numbackends FROM pg_stat_database WHERE datname='aria_dev';
EOF

# 2. Kill idle connections
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER <<EOF
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes';
EOF

# 3. Check pool size configuration
grep "DB_POOL" .env
# Should show: DB_POOL_SIZE=5, DB_POOL_MAX_OVERFLOW=10

# 4. Increase pool size if needed
# Edit .env:
DB_POOL_SIZE=10
DB_POOL_MAX_OVERFLOW=20

# 5. Check database connection string
grep "DATABASE_URL" .env
# Make sure it's correct and not pointing to wrong database

# 6. Verify app is closing connections properly
grep -A 5 "async_session" ai-service/api/dependencies.py
# Should show: async with async_session() as session:

# 7. Restart backend
pkill -f "python main.py" ai-service/
source .venv/bin/activate
cd ai-service && python main.py
```

### "Request timed out after 30 seconds"

**Symptoms:** Long-running API calls return 504 Gateway Timeout

**Solutions:**

```bash
# 1. Check request timeout setting
grep "REQUEST_TIMEOUT" .env
# Default: 30 seconds

# 2. Check if pipeline is taking > 30 seconds
# Check ai-service/pipeline.py for long-running operations

# 3. Increase timeout for specific endpoints
# Edit ai-service/main.py:
@app.post("/api/pipeline/start", timeout=300)  # 5 minutes

# 4. Use background tasks for long operations
from fastapi import BackgroundTasks

@app.post("/api/long-operation")
async def long_operation(background_tasks: BackgroundTasks):
    background_tasks.add_task(do_work)
    return {"status": "queued"}

# 5. Check if database query is slow
# Enable slow query logging
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME <<EOF
SET log_min_duration_statement = 5000;  # Log queries > 5 seconds
EOF

# 6. Monitor query performance
tail -f /var/log/postgresql/postgresql.log | grep "duration:"
```

---

## Database Issues

### "Table does not exist"

**Symptoms:** "ProgrammingError: relation 'public.cases' does not exist"

**Solutions:**

```bash
# 1. Check if migrations were run
alembic current
# Should show: 001_initial_schema

# 2. Run migrations
alembic upgrade head

# 3. Verify tables created
psql -h localhost -U aria_user -d aria_dev <<EOF
\dt  # List tables
SELECT table_name FROM information_schema.tables WHERE table_schema='public';
EOF

# 4. Check migration file exists
ls -la ai-service/database/migrations/versions/
# Should show: 001_initial_schema.py

# 5. If migration is broken, fix it
# Edit ai-service/database/migrations/versions/001_initial_schema.py
# Then try upgrade again
alembic upgrade head

# 6. As last resort, downgrade and upgrade
alembic downgrade base
alembic upgrade head
```

### "Unique constraint violation"

**Symptoms:** "IntegrityError: duplicate key value violates unique constraint"

**Solutions:**

```bash
# 1. Identify which constraint
# Error message usually shows: constraint "idx_users_email"

# 2. List all constraints
PGPASSWORD=$DB_PASSWORD psql -h localhost -U aria_user -d aria_dev <<EOF
SELECT constraint_name, table_name, column_name 
FROM information_schema.key_column_usage 
WHERE table_schema='public' AND constraint_type='UNIQUE';
EOF

# 3. Check for duplicates
PGPASSWORD=$DB_PASSWORD psql -h localhost -U aria_user -d aria_dev <<EOF
SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;
EOF

# 4. Remove duplicate
DELETE FROM users WHERE id IN (
  SELECT id FROM (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY email ORDER BY created_at) as rn
    FROM users
  ) WHERE rn > 1
);

# 5. Or use UPSERT (INSERT ... ON CONFLICT)
# Edit code to handle duplicates gracefully
INSERT INTO users (email, password) VALUES (...) 
ON CONFLICT (email) DO UPDATE SET updated_at = NOW();
```

### "Slow queries"

**Symptoms:** API endpoints taking >500ms, especially list endpoints

**Solutions:**

```bash
# 1. Identify slow queries
PGPASSWORD=$DB_PASSWORD psql -h localhost -U aria_user -d aria_dev <<EOF
SELECT median(mean_time) as median_time, query FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat%'
GROUP BY query
ORDER BY median_time DESC
LIMIT 10;
EOF

# 2. Analyze query plan
PGPASSWORD=$DB_PASSWORD psql -h localhost -U aria_user -d aria_dev <<EOF
EXPLAIN ANALYZE SELECT * FROM cases WHERE project_id = 'xxx';
EOF

# 3. Create missing indexes
CREATE INDEX idx_cases_project_created ON cases(project_id, created_at DESC);

# 4. Verify index usage
PGPASSWORD=$DB_PASSWORD psql -h localhost -U aria_user -d aria_dev <<EOF
SELECT schemaname, tablename, indexname, idx_scan FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
EOF

# 5. Vacuum and analyze
VACUUM ANALYZE;

# 6. Implement pagination in backend routes
# Edit ai-service/api/routes/cases.py
@app.get("/api/v2/cases")
async def list_cases(skip: int = 0, limit: int = 50):
    # Use skip/limit in query
    return db.query(Case).offset(skip).limit(limit).all()
```

---

## Authentication Issues

### "Invalid credentials"

**Symptoms:** Login fails even with correct password

**Solutions:**

```bash
# 1. Verify user exists
PGPASSWORD=$DB_PASSWORD psql -h localhost -U aria_user -d aria_dev <<EOF
SELECT id, email, is_active FROM users WHERE email='test@example.com';
EOF

# 2. Verify password was hashed
grep -A 10 "register" ai-service/api/routes/auth.py
# Should use: passlib.pbkdf2_sha256.hash(password)

# 3. Test password hashing locally
python -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')
hashed = pwd_context.hash('mypassword123')
is_valid = pwd_context.verify('mypassword123', hashed)
print(f'Valid: {is_valid}')
"

# 4. Reset password
PGPASSWORD=$DB_PASSWORD psql -h localhost -U aria_user -d aria_dev <<EOF
UPDATE users SET hashed_password = crypt('newpassword123', gen_salt('bf'))
WHERE email='test@example.com';
EOF

# 5. Check JWT secret is consistent
echo $JWT_SECRET_KEY | wc -c
# Should be > 32 characters
```

---

## Deployment Issues

### "Docker image fails to build"

**Symptoms:** `docker build` returns error

**Solutions:**

```bash
# 1. Check Dockerfile syntax
docker build --progress=plain --no-cache -t aria-api .
# Shows detailed build logs

# 2. Common errors:
# - Missing requirements.txt
ls -la ai-service/requirements.txt

# - Python dependency conflict
pip install -r ai-service/requirements.txt --dry-run

# - Base image doesn't exist
docker pull python:3.11-slim

# 3. Build with specific base
docker build \
  --build-arg PYTHON_VERSION=3.11 \
  -t aria-api .
```

### "Pod stuck in CrashLoopBackOff"

**Symptoms:** Kubernetes pod keeps restarting

**Solutions:**

```bash
# 1. Check pod logs
kubectl logs pod/aria-api-xyz -n production
# Look for errors in last 50 lines

# 2. Check previous logs
kubectl logs pod/aria-api-xyz -n production --previous

# 3. Get pod events
kubectl describe pod aria-api-xyz -n production | grep -A 20 "Events:"

# 4. Common causes:
# - Missing environment variable
kubectl exec pod/aria-api-xyz -- env | grep JWT_SECRET_KEY

# - Missing volume mount
kubectl describe pod aria-api-xyz | grep -A 5 "Mounts:"

# - Database connection
kubectl exec pod/aria-api-xyz -- nc -zv $DATABASE_HOST:5432

# 5. Fix and redeploy
# Edit deployment.yaml with correct env/mounts
kubectl apply -f deployment.yaml

# 6. Monitor startup
kubectl logs -f pod/aria-api-xyz -n production
```

---

## Performance Issues

### "Application slow after deployment"

**Symptoms:** Requests take much longer than before

**Solutions:**

```bash
# 1. Compare before/after metrics
# Check Prometheus dashboard for latency graphs

# 2. Identify slow endpoint
curl -w "@perf.txt" https://api.aria.example.com/api/v2/cases
# Shows: time_connect, time_starttransfer, etc.

# 3. Profile code
python -m cProfile -s cumulative ai-service/main.py

# 4. Check new migration didn't add index
git diff HEAD~1 ai-service/database/migrations/
# Look for CREATE INDEX statements

# 5. Check query count increased
grep -E "SELECT|INSERT|UPDATE" ai-service/api/routes/cases.py | wc -l

# 6. Enable debug logging
export LOG_LEVEL=DEBUG
python main.py  2>&1 | grep -E "SELECT|duration"

# 7. Compare database connection pool stats
PGPASSWORD=$DB_PASSWORD psql -h localhost -U aria_user <<EOF
SELECT * FROM pg_stat_statements WHERE query LIKE '%cases%' ORDER BY mean_time DESC;
EOF

# 8. If necessary, rollback
kubectl rollout undo deployment/aria-api -n production
```

---

## Monitor and Alert Issues

### "No metrics in Prometheus"

**Symptoms:** `/metrics` endpoint returns empty or is down

**Solutions:**

```bash
# 1. Check if endpoint is exposed
curl http://localhost:8000/metrics
# Should return Prometheus-format text

# 2. Check if instrumentation middleware is registered
grep -A 10 "prometheus" ai-service/main.py
# Should show: app.add_middleware(PrometheusMiddleware)

# 3. Install prometheus_client
pip list | grep prometheus
pip install prometheus-client

# 4. Verify Prometheus scrape config
cat /etc/prometheus/prometheus.yml | grep -A 10 "aria-api"
# Should show job_name and targets

# 5. Check scrape interval
grep "scrape_interval" /etc/prometheus/prometheus.yml
# Default: 15s

# 6. Manually scrape
curl http://aria-api:8000/metrics | head -20

# 7. Check Prometheus targets dashboard
# Navigate to: http://localhost:9090/targets
# Should show aria-api as "UP"

# 8. Test metric query
# In Prometheus UI, type: hexamind_http_requests_total
# Should return values if any requests have been made
```

### "Alert not firing"

**Symptoms:** Metric exceeds threshold but alert doesn't trigger

**Solutions:**

```bash
# 1. Check alert rule is loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name=="aria_application")'

# 2. Verify condition is correct
# Edit prometheus-alerts.yml and check PromQL expression
grep -A 3 "HighErrorRate" prometheus-alerts.yml

# 3. Query the alert condition directly
# In Prometheus UI, evaluate:
(sum(rate(hexamind_http_requests_total{status=~"5.."}[5m])) /
 sum(rate(hexamind_http_requests_total[5m]))) > 0.05

# 4. Check if data exists
curl http://localhost:9090/api/v1/query?query=hexamind_http_requests_total

# 5. Check alert routing
cat /etc/alertmanager/config.yml | jq '.route.routes[] | select(.group_by_str[]=="severity")'

# 6. Check webhook receiver
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "status":"firing",
    "labels":{"alertname":"TestAlert","severity":"critical"},
    "annotations":{"summary":"test"}
  }]'
```

---

**For additional help, create a GitHub issue or contact support@aria.example.com**

**Last Updated:** 2026-04-04
