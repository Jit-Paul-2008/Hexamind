# ARIA UX Deployment Runbook

**Document Version:** 1.0  
**Last Updated:** 2026-04-04  
**Status:** Ready for Production  
**On-Call Contact:** [Your Name] — [your@email.com]

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Development Deployment (Local)](#development-deployment-local)
3. [Staging Deployment](#staging-deployment)
4. [Production Deployment](#production-deployment)
5. [Post-Deployment Validation](#post-deployment-validation)
6. [Rollback Procedures](#rollback-procedures)
7. [Troubleshooting](#troubleshooting)
8. [Disaster Recovery](#disaster-recovery)

---

## Pre-Deployment Checklist

### Before Any Deployment

- [ ] All tests passing: `npm run test && python -m pytest ai-service/tests/`
- [ ] Code review approved (2 reviewers minimum for production)
- [ ] No security vulnerabilities: `npm audit` and `safety check`
- [ ] Database migration tested on staging
- [ ] Feature flags configured
- [ ] Alert rules verified in monitoring stack
- [ ] Rollback plan documented (see [Rollback Procedures](#rollback-procedures))
- [ ] On-call engineer standing by
- [ ] Stakeholders notified via Slack #deployments

### Environment Validation

```bash
# Verify env files are in place
ls -la .env.local
ls -la .env.production (don't check this into git!)

# Validate env syntax
python scripts/validate-env.py

# Check secrets are filled
grep "REPLACE_ME" .env.production && echo "⚠️  Incomplete secrets!" || echo "✓ All secrets configured"
```

---

## Development Deployment (Local)

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/your-org/hexamind.git
cd hexamind

# 2. Create Python venv
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
npm install
pip install -r ai-service/requirements.txt

# 4. Setup environment
cp .env.example .env.local
# Edit .env.local with your local values (database, API keys, etc.)

# 5. Initialize database
alembic upgrade head

# 6. Seed feature flags
python scripts/seed-feature-flags.py

# 7. Generate test data
python scripts/db-seed-dev.py
```

### Running Locally

```bash
# Terminal 1: Backend
source .venv/bin/activate
cd ai-service
python main.py
# Should print: "Uvicorn running on http://0.0.0.0:8000"

# Terminal 2: Frontend
npm run dev
# Should print: "  ▲ Next.js 16.2.2"
# Open http://localhost:3000

# Terminal 3: Database
# (if using docker-compose)
docker-compose up -d postgres redis
```

### Verify Local Deployment

```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/health/readiness
curl http://localhost:3000

# Test authentication
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@local.dev","password":"testpass123"}'

# Test pipeline
curl -X POST http://localhost:8000/api/pipeline/start \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is AI?","mode":"chat"}'
```

---

## Staging Deployment

### 1. Build Docker Images

```bash
# Build backend
docker build -t aria-api:staging -f Dockerfile.api .
docker tag aria-api:staging $DOCKER_REGISTRY/aria-api:staging
docker push $DOCKER_REGISTRY/aria-api:staging

# Build frontend (if dockerized)
docker build -t aria-web:staging -f Dockerfile.web .
docker tag aria-web:staging $DOCKER_REGISTRY/aria-web:staging
docker push $DOCKER_REGISTRY/aria-web:staging
```

### 2. Deploy to Staging Environment

```bash
# Update staging manifests
cd k8s/
sed -i "s|aria-api:.*|aria-api:staging|g" aria-api-deployment.yaml
sed -i "s|aria-web:.*|aria-web:staging|g" aria-web-deployment.yaml

# Apply changes
kubectl apply -f aria-api-deployment.yaml
kubectl apply -f aria-web-deployment.yaml

# Monitor rollout
kubectl rollout status deployment/aria-api -n staging
kubectl rollout status deployment/aria-web -n staging
```

### 3. Run Database Migrations on Staging

```bash
# Connect to staging database
PGPASSWORD=$STAGING_DB_PASSWORD psql -h staging-db.example.com -U aria_user -d aria_staging

# Run migrations
alembic -n staging upgrade head

# Verify migration success
SELECT version FROM alembic_version;
```

### 4. Seed Staging Data

```bash
# Run seed script
python scripts/seed-feature-flags.py --env staging
python scripts/db-seed-staging.py
```

### 5. Smoke Test Staging

```bash
# Health checks
curl https://staging.aria.example.com/health

# Test auth
curl -X POST https://staging.aria.example.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"stagingtest@aria.dev","password":"stagingtest123"}'

# Test E2E workflow
npm run test:e2e:staging

# Monitor logs
kubectl logs -f deployment/aria-api -n staging
```

---

## Production Deployment

⚠️  **Production deployments require TWO approvals and should follow the 10% → 25% → 50% → 100% rollout strategy.**

### Phase 1: Preparation (1 hour before deployment)

```bash
# 1. Create deployment ticket
# Jira ticket: DEPLOY-XXXX
# Slack message in #deployments with rollout plan and rollback trigger

# 2. Notify stakeholders
# Slack message in #product, #sales, #support
# "Deploying ARIA v1.5.0 at 14:00 UTC. No downtime expected."

# 3. Verify database backups
aws s3 ls s3://aria-backups/prod/ | head -5
# Should show recent backups from last hour

# 4. Verify monitoring is active
# Check Prometheus, Grafana, Datadog are scraping
curl https://monitoring.example.com/api/v1/query?query=up\{job=\"aria-api\"\}

# 5. Enable maintenance mode (optional, for zero-downtime)
kubectl set env deployment/aria-api \
  -n production \
  MAINTENANCE_MODE=false  # Will set to true if needed
```

### Phase 2: 10% Rollout

```bash
# 1. Build production images
docker build -t aria-api:1.5.0 -f Dockerfile.api .
docker tag aria-api:1.5.0 $DOCKER_REGISTRY/aria-api:1.5.0
docker push $DOCKER_REGISTRY/aria-api:1.5.0

# 2. Deploy to 10% of traffic (blue-green)
# Option A: Canary deployment
kubectl set image deployment/aria-api-canary aria-api=$DOCKER_REGISTRY/aria-api:1.5.0 -n production

# Option B: Manual canary pod
kubectl run aria-api-canary \
  --image=$DOCKER_REGISTRY/aria-api:1.5.0 \
  --replicas=1 \
  -n production

# 3. Monitor canary (5-10 minutes)
# Watch metrics: error rate, latency, cpu
watch 'kubectl top pod -n production | grep aria'

# Check error logs
kubectl logs -f deployment/aria-api-canary -n production | grep ERROR

# Verify no data corruption
psql -h prod-db.example.com -U aria_prod <<EOF
SELECT COUNT(*) as run_count FROM runs WHERE created_at > NOW() - INTERVAL '10 minutes';
SELECT COUNT(*) FROM audit_logs WHERE timestamp > NOW() - INTERVAL '10 minutes';
EOF

# 4. Review metrics (Grafana dashboard)
# P50 latency should be < 500ms
# P95 latency should be < 5000ms
# Error rate should be < 1%
# Success rate for auth endpoints > 99%
```

**Decision Point:** If metrics are healthy, proceed. If not, ROLLBACK.

```bash
# Rollback (if canary fails)
kubectl delete pod aria-api-canary -n production
# See [Rollback Procedures](#rollback-procedures) for full rollback
```

### Phase 3: 25% Rollout

```bash
# 1. Scale production deployment to 25%
kubectl set image deployment/aria-api aria-api=$DOCKER_REGISTRY/aria-api:1.5.0 -n production

# Gradually roll out by scaling replicas
kubectl scale deployment aria-api --replicas=2 -n production  # 25% of 8
watch 'kubectl get pods -n production | grep aria'

# 2-3. Monitor for 10 minutes
# Same metrics as Phase 2

# 4. Check database performance
# Monitor slow queries
PGPASSWORD=$PROD_DB_PASSWORD psql -h prod-db.example.com -U aria_prod <<EOF
SELECT * FROM pg_stat_statements 
WHERE query NOT LIKE '%pg_stat%' 
ORDER BY mean_time DESC LIMIT 10;
EOF
```

**Decision Point:** If healthy, proceed to 50%.

### Phase 4: 50% Rollout

```bash
# Scale to 50%
kubectl scale deployment aria-api --replicas=4 -n production

# Monitor for 15 minutes
watch 'kubectl top nodes -n production'
watch kubectl logs -f deployment/aria-api -n production

# Check business metrics
# Active users, runs executed, cost tracking
curl https://api.aria.example.com/api/metrics?filter=active_users
curl https://api.aria.example.com/api/metrics?filter=runs_completed
```

### Phase 5: 100% Rollout

```bash
# Full deployment
kubectl scale deployment aria-api --replicas=8 -n production

# Monitor rolling update
kubectl rollout status deployment/aria-api -n production

# Final validation
bash scripts/production-smoke-tests.sh
npm run test:e2e:production

# Mark deployment as complete
# Slack: "✅ ARIA v1.5.0 fully deployed to production (8 replicas, 100% traffic)"
```

---

## Post-Deployment Validation

### Immediate (5 mins after 100%)

```bash
# 1. Health checks
for i in {1..5}; do 
  curl -s https://api.aria.example.com/health/readiness | jq .
done

# 2. Check logs for errors
kubectl logs -f deployment/aria-api -n production --tail=100 | grep -E "ERROR|FATAL"

# 3. Verify database migrations applied
PGPASSWORD=$PROD_DB_PASSWORD psql -h prod-db.example.com -U aria_prod <<EOF
SELECT version, installed_on FROM alembic_version;
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';
EOF

# 4. Check feature flags
curl https://api.aria.example.com/api/feature-flags -H "Authorization: Bearer $ADMIN_TOKEN" | jq .
```

### Short-term (30 mins)

```bash
# Review metrics in Grafana
# Dashboard: ARIA Production
# Check:
# - HTTP request rate
# - Error rate (should be < 1%)
# - Latency P50/P95/P99
# - Database connection pool usage
# - Memory/CPU utilization

# Tail application logs
kubectl logs -f deployment/aria-api -n production --tail=200

# Check Sentry for new errors
curl https://sentry.example.com/api/0/projects/aria/latest-events/

# Monitor database
PGPASSWORD=$PROD_DB_PASSWORD psql -h prod-db.example.com -U aria_prod <<EOF
SELECT datname, numbackends FROM pg_stat_database WHERE datname = 'aria_prod';
SELECT count(*) FROM pg_stat_activity;
EOF
```

### Medium-term (2 hours)

```bash
# Run E2E test suite against production
npm run test:e2e:production --env=prod

# Synthetic uptime monitoring
bash scripts/synthetic-monitoring.sh

# Check business metrics
# Number of active sessions
# Cost tracking accumulation
# Export success rate

# Verify backups were created
aws s3 ls s3://aria-backups/prod/$(date +%Y-%m-%d)
```

### Long-term (24 hours)

```bash
# Analyze performance trends
# • Has error rate stayed < 1%?
# • Have latencies remained stable?
# • Any memory or CPU growth?

# Review cost impact
# Did this version increase/decrease request cost?

# User feedback
# Any issues reported in #support or #product?

# Database health
# Autovacuum running normally?
# Index bloat within limits?
```

---

## Rollback Procedures

### Automatic Rollback Triggers

**DO NOT WAIT — Automatic rollback happens immediately if:**
- Error rate > 5% for > 2 minutes
- P95 latency > 30 seconds for > 5 minutes
- Database connection pool exhausted for > 1 minute
- Service down (all replicas failing to start)

### Manual Rollback (from on-call)

```bash
# 1. Immediate notification
# Slack: @channel "🚨 ARIA production rollback initiated. See runbook."

# 2. Kill new deployment
kubectl rollout undo deployment/aria-api -n production

# 3. Verify previous version is healthy
kubectl rollout status deployment/aria-api -n production
curl https://api.aria.example.com/health/readiness

# 4. Revert feature flags (optional)
python scripts/rollback-feature-flags.py

# 5. Revert database (if migration caused issue)
# ONLY if absolutely necessary — coordinate with DB team first
# alembic -n prod downgrade -1

# 6. Verify business is running
# Check: users can login, pipelines execute, exports work

# 7. Post-incident
# Slack channel #incident-postmortem
# Create ticket: What went wrong? How to prevent?
```

### If Rollback Fails

```bash
# 1. Disable service from traffic
kubectl scale deployment aria-api --replicas=0 -n production

# 2. Switch external traffic to previous environment (if available)
# Edit DNS / load balancer to point to backup cluster

# 3. Call executive on-call
# PagerDuty: PAGE_EXECUTIVE

# 4. Assess damage
# Database: check for corrupted rows
# Users: how many impacted? How long was outage?

# 5. Recovery plan
# Can we salvage this deployment with a fix?
# Or do we need to rebuild from backups?
```

---

## Troubleshooting

### Common Issues

#### Issue: Database Migration Fails

```bash
# 1. Check migration status
alembic -n prod history

# 2. Check for locks
PGPASSWORD=$PROD_DB_PASSWORD psql -h prod-db.example.com -U aria_prod <<EOF
SELECT * FROM pg_locks WHERE transaction IS NOT NULL;
SELECT * FROM pg_stat_activity WHERE state = 'active';
EOF

# 3. Kill blocking query (if safe)
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE pid != pg_backend_pid() AND application_name ILIKE '%alembic%';

# 4. Retry migration
alembic -n prod upgrade head --sql  # Preview first!
alembic -n prod upgrade head
```

#### Issue: API Pods Won't Start

```bash
# 1. Check logs
kubectl logs pod/aria-api-xyz -n production

# 2. Check resource limits
kubectl describe pod aria-api-xyz -n production | grep -A 5 Limits

# 3. Check environment variables
kubectl exec -it pod/aria-api-xyz -- env | grep -E "DATABASE|JWT|SECRET"

# 4. Check image pull
kubectl describe pod aria-api-xyz -n production | grep -E "Image|Pull"

# 5. Manual remediation
# Edit deployment to pass env/image, or inject via configmap
kubectl set image deployment/aria-api aria-api=$DOCKER_REGISTRY/aria-api:prev -n production
```

#### Issue: High Latency After Deploy

```bash
# 1. Check database performance
PGPASSWORD=$PROD_DB_PASSWORD psql -h prod-db.example.com -U aria_prod <<EOF
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;

EXPLAIN ANALYZE SELECT * FROM cases WHERE created_at > NOW() - INTERVAL '1 day';
EOF

# 2. Check query plan changed
# Compare query plans before/after deployment

# 3. Rebuild indexes if needed
REINDEX INDEX idx_runs_case_started;

# 4. Check cache hit rates
curl https://api.aria.example.com/api/cache-stats

# 5. If persistent, rollback
kubectl rollout undo deployment/aria-api -n production
```

#### Issue: Out of Memory

```bash
# 1. Identify memory leak
kubectl top pod -n production | sort -k4 -nr | head -5

# 2. Check for unbounded caches
# Review code for missing cache TTLs or memory leaks

# 3. Temporarily increase limits
kubectl set resources deployment aria-api \
  -n production \
  --limits=memory=4Gi,cpu=2 \
  --requests=memory=2Gi,cpu=1

# 4. Restart pods
kubectl rollout restart deployment/aria-api -n production

# 5. Fix root cause and redeploy
# Update code, redeploy with fix
```

---

## Disaster Recovery

### Data Backup/Restore

```bash
# 1. List recent backups
aws s3 ls s3://aria-backups/prod/ | tail -10

# 2. Restore from backup (CAUTION: DATA LOSS)
# This should only be done with explicit approval from Engineering Lead

# First, create new DB instance from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier aria-prod-recovery \
  --db-snapshot-identifier aria-prod-2026-04-04-14-00

# Wait for restore to complete
aws rds wait db-instance-available --db-instance-identifier aria-prod-recovery

# 3. Test recovered data
# Connect to recovery DB and verify data integrity

# 4. Switch production to recovered DB
# Coordinate with DevOps/DBA
# Update DNS, connection strings, etc.

# 5. Decommission old DB
# After verification of recovery success
```

### Complete Service Outage

```bash
# 1. Activate incident response
# Slack: @channel "🚨 ARIA Service Outage - Incident Active"
# Page on-call team via PagerDuty

# 2. Assess status
# Is it frontend only? Backend? Database?
# Narrow down root cause

# 3. Restore from last good state
# Option A: Deploy previous working version
kubectl rollout undo deployment/aria-api -n production --to-revision=2

# Option B: Restore database from backup (see above)

# Option C: Switch to disaster recovery environment
# Pre-configured secondary cluster in different region

# 4. Communicate with users
# Status page: https://status.aria.example.com
# Email: customers@aria.example.com
# Twitter: @AriaSupport

# 5. Post-incident analysis
# Schedule: 24 hours after incident resolved
# Questions: What failed? Why? How to prevent?
# Document in Confluence or internal wiki
```

---

## Appendix: Useful Commands

```bash
# View deployment status in real-time
watch kubectl get pods -n production

# View logs with grep
kubectl logs deployment/aria-api -n production -f | grep "ERROR\|WARN"

# SSH into pod for debugging
kubectl exec -it pod/aria-api-xyz -n production -- /bin/bash

# Port-forward to local machine
kubectl port-forward svc/aria-api 8000:8000 -n production

# View previous 10 deployments
kubectl rollout history deployment/aria-api -n production

# Get detailed deployment info
kubectl describe deployment aria-api -n production

# View resource usage
kubectl top nodes -n production
kubectl top pods -n production --sort-by=memory

# Update replicas manually
kubectl scale deployment aria-api --replicas=10 -n production

# Monitor specific pod
kubectl logs pod/aria-api-xyz -n production -f --tail=50

# Get Swagger docs from running API
curl https://api.aria.example.com/openapi.json | jq .

# Health check from CLI
curl https://api.aria.example.com/health \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

**END OF RUNBOOK**

*Last tested: 2026-04-04*  
*Next review: 2026-05-04*
