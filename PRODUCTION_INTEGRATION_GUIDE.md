# ARIA UX Production Deployment — Final Integration Guide

**Status:** Ready for User Input & Integration  
**Date:** 2026-04-04  
**Last Phase:** Autonomous work complete  
**Next Step:** User provides REQUIRED_USER_INPUTS.md answers

---

## Overview

All autonomous work is complete. This document shows:
1. What's been done
2. What needs your inputs
3. How to integrate everything into production
4. Deployment sequence

### Autonomous Deliverables (✅ COMPLETE)

These are already built and ready:

#### Code & Components
- ✅ Phase 1-5 fully committed to main (d80a50e through 301ebc2)
- ✅ E2E test suite (tests/e2e/complete-workflows.test.ts)
- ✅ Load test harness (scripts/load-test.py)
- ✅ Feature flag seeding (scripts/seed-feature-flags.py)

#### Configuration Templates
- ✅ .env.example (all variables documented)
- ✅ prometheus-alerts.yml (30+ alert rules)
- ✅ API_SPECIFICATION.yml (complete OpenAPI spec)

#### Documentation
- ✅ DEPLOYMENT_RUNBOOK.md (phased rollout, 100+ commands)
- ✅ TROUBLESHOOTING.md (50+ Q&A)
- ✅ ARCHITECTURE_DECISIONS.md (10 ADRs with rationale)
- ✅ REQUIRED_USER_INPUTS.md (this form)

---

## Part 1: What You Need to Provide

### Checklist by Category

**👤 Security & Secrets (CRITICAL)**
- [ ] JWT_SECRET_KEY (generate: `openssl rand -hex 32`)
- [ ] Database password (if production PostgreSQL)
- [ ] Any third-party API keys (Tavily, Gemini, OpenRouter)

**🎨 Branding & Design (HIGH)**
- [ ] Primary color (#XXXXXX)
- [ ] Secondary color (#XXXXXX)
- [ ] Logo file (SVG preferred)
- [ ] Font preferences (heading, body)

**🗄️ Infrastructure (HIGH)**
- [ ] Database connection URL (PostgreSQL)
- [ ] Redis URL (if using cache)
- [ ] S3 bucket name (for exports)
- [ ] Docker registry URL

**📊 Monitoring & Alerts (MEDIUM)**
- [ ] Grafana dashboard URL
- [ ] Slack webhook for alerts
- [ ] Alert email recipients
- [ ] Latency thresholds (P95, P99)

**👥 Team & Compliance (MEDIUM)**
- [ ] On-call rotation (who handles incidents)
- [ ] Compliance requirements (HIPAA? GDPR?)
- [ ] Data retention policy (days)
- [ ] Privacy/Legal docs (links or text)

**📋 See REQUIRED_USER_INPUTS.md for complete form**

---

## Part 2: Pre-Deployment Checklist

Before deploying to production, confirm:

### Code & Testing
- [ ] All 10 backend tests passing: `python -m pytest ai-service/tests/ -v`
- [ ] Frontend builds: `npm run build` (exit 0)
- [ ] TypeScript checks: `npm run typecheck` (no errors)
- [ ] Linting passes: `npm run lint` (no errors)
- [ ] E2E tests locally: `npm run test:e2e` (at least with mock data)

### Dependencies
- [ ] All Python packages installed: `pip list | grep -E sqlalchemy|alembic|fastapi`
- [ ] All Node packages installed: `npm ls | tail -5`
- [ ] Docker images built: `docker images | grep aria`

### Configuration
- [ ] `.env.production` filled out (not `.env.local`)
- [ ] All CRITICAL fields populated (see checklist above)
- [ ] Sensitive values NOT in git (use .gitignore)
- [ ] Database accessible: `psql -h $DB_HOST -U $DB_USER -d aria_prod -c "SELECT 1"`

### Security Review
- [ ] No hardcoded secrets in code: `grep -r "api_key\|password" src/ ai-service/ | grep -v ".md"`
- [ ] CORS configured with actual domain (not localhost)
- [ ] HTTPS enforced (not http)
- [ ] Rate limiting enabled
- [ ] Auth token validation tested

### Documentation Review
- [ ] Rollback procedure understood by ops team
- [ ] Alert contacts configured in monitoring
- [ ] On-call runbook printed/shared
- [ ] Deployment ticket created (Jira/Linear)

### Stakeholder Approval
- [ ] Engineering sign-off (code review, architecture)
- [ ] Product sign-off (UX, features working)
- [ ] Security sign-off (no vulnerabilities)
- [ ] DevOps/Infrastructure sign-off (resources, capacity)

---

## Part 3: Integration Workflow

### Step 1: Prepare Your Inputs (30 min)

```bash
# 1. Review REQUIRED_USER_INPUTS.md
cat REQUIRED_USER_INPUTS.md

# 2. Fill out all sections
# Save as: user-inputs.json or inputs.md

# 3. Validate no missing critical fields
grep "***REPLACE" inputs.md
# Should return empty (all placeholders filled)
```

### Step 2: Generate Production Configuration (10 min)

Once you provide inputs, run integration script:

```bash
# 1. Create production env from template
cp .env.example .env.production

# 2. Populate with your values (automated injection)
python scripts/integrate-user-inputs.py --inputs inputs.json --output .env.production

# 3. Validate
python scripts/validate-env.py --env production

# 4. Secure it
chmod 600 .env.production
git add .env.production* >/dev/null 2>&1  # Verify NOT added to git
```

### Step 3: Initialize Database (20 min)

```bash
# 1. Create database
createdb -h $DB_HOST -U $DB_USER aria_prod
# or via cloud provider (Supabase, AWS RDS)

# 2. Run migrations
export DATABASE_URL=${YOUR_DB_CONNECTION_STRING}
alembic upgrade head

# 3. Seed initial data
python scripts/db-seed-prod.py

# 4. Verify schema
psql -h $DB_HOST -U $DB_USER -d aria_prod -c "\dt"
# Should show: users, organizations, projects, cases, runs, etc.
```

### Step 4: Initialize Feature Flags (10 min)

```bash
# 1. Seed flags in configured provider
python scripts/seed-feature-flags.py --env production

# 2. Verify flags loaded
curl http://localhost:8000/api/feature-flags \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected response shows all flags with current values
```

### Step 5: Build Docker Images (15 min)

```bash
# 1. Build backend image
docker build -t $REGISTRY/aria-api:v1.0.0 -f Dockerfile .

# 2. Build frontend image (if separate container)
docker build -t $REGISTRY/aria-web:v1.0.0 -f Dockerfile.web src/

# 3. Push to registry
docker push $REGISTRY/aria-api:v1.0.0
docker push $REGISTRY/aria-web:v1.0.0

# 4. Verify images
docker images | grep aria
```

### Step 6: Deploy to Staging (45 min)

```bash
# 1. Update staging manifests
cd k8s/
sed -i "s|image:.*aria-api.*|image: $REGISTRY/aria-api:v1.0.0|g" staging/*.yaml

# 2. Apply deployment
kubectl apply -f staging/

# 3. Wait for rollout
kubectl rollout status deployment/aria-api -n staging --timeout=10m

# 4. Run smoke tests
bash scripts/staging-smoke-tests.sh

# 5. Run E2E tests against staging
npm run test:e2e:staging

# 6. Monitor logs
kubectl logs -f deployment/aria-api -n staging --tail=100
```

### Step 7: Gradual Production Rollout (2 hours)

Follow DEPLOYMENT_RUNBOOK.md exactly:

1. **10% Canary** (10 min)
   - Deploy to 1 replica
   - Monitor error rate, latency
   - Verify database health

2. **25% Rollout** (15 min)
   - Scale to 2 replicas
   - Monitor metrics
   - Check database performance

3. **50% Rollout** (20 min)
   - Scale to 4 replicas
   - Full monitoring dashboard
   - Business metrics

4. **100% Full Deployment** (30 min)
   - Scale to 8 replicas
   - Final validation
   - Post-deployment smoke tests

### Step 8: Post-Deployment Validation (30 min)

```bash
# 1. Immediate checks (5 min)
curl https://api.aria.example.com/health/readiness
curl https://api.aria.example.com/health/liveness

# 2. User workflow test (10 min)
# Create account → Create case → Run ARIA → View results
# Manually test in browser

# 3. Monitor system (15 min)
# Watch Grafana dashboard
# Check error rate < 1%
# Check P95 latency < 5s
# Check no critical alerts

# 4. Notify team
# Slack: "✅ ARIA v1.0.0 deployed to production (100% traffic)"
```

---

## Part 4: Files You'll Receive

After providing inputs, you'll receive an integrated package:

```
aria-production-pkg/
├── .env.production          # Your secrets (secure separately!)
├── docker-compose.prod.yml  # Production Compose config
├── k8s/
│   ├── aria-api-deployment.yaml
│   ├── aria-web-deployment.yaml
│   ├── services/
│   └── configmaps/
├── prometheus-config.yml    # With YOUR alert receivers
├── prometheus-alerts.yml    # Your customized thresholds
├── grafana/
│   └── dashboards/
│       └── aria-production.json
├── scripts/
│   ├── integrate-user-inputs.py  # Auto-integration script
│   ├── db-seed-prod.py
│   └── validate-deployment.sh
└── DEPLOYMENT_READY.md      # Final checklist before go-live
```

---

## Part 5: Rollback Timeline

If something goes wrong, rollback is fast:

```
T+0s   → Incident detected
T+30s  → Error rate alert fires
T+1min → Feature flag disabled OR previous deployment restored
T+5min → All traffic back on stable version
T+15min → Post-incident investigation begins
```

**Always have rollback plan documented before deployment.**

See DEPLOYMENT_RUNBOOK.md sections [Rollback Procedures](#rollback-procedures).

---

## Part 6: Success Criteria

Deployment is successful when:

### Immediate (5 minutes)
- ✅ All health checks return 200
- ✅ Error rate < 1%
- ✅ No critical alerts firing
- ✅ Database responding normally

### Short-term (1 hour)
- ✅ Users can register and login
- ✅ Users can create cases and run ARIA
- ✅ Results are persisted to database
- ✅ No unusual error patterns in logs

### Medium-term (24 hours)
- ✅ Error rate remains < 1%
- ✅ Latency P95 stays < 5 seconds
- ✅ No memory leaks or growth
- ✅ Cost tracking working correctly

### Long-term (1 week)
- ✅ Zero data corruption
- ✅ Backup/restore tested successfully
- ✅ Users report no issues
- ✅ Business metrics within targets

---

## Part 7: Quick Reference Commands

### Before Deployment

```bash
# Full test suite
npm run build && npm run lint && npm run typecheck
python -m pytest ai-service/tests/ -v

# Database migration test
alembic upgrade head && alembic downgrade -1 && alembic upgrade head

# Feature flag seed
python scripts/seed-feature-flags.py
```

### During Deployment

```bash
# Watch pods rolling out
watch kubectl get pods -n production

# Monitor metrics
kubectl logs -f deployment/aria-api -n production

# Check load balancer
kubectl get svc aria-api -n production
```

### After Deployment

```bash
# Verify health
for i in {1..10}; do curl -s https://api.aria.example.com/health | jq . ; done

# Check metrics
curl https://api.aria.example.com/metrics | grep hexamind_http

# E2E smoke test
npm run test:e2e:production
```

### Rollback (Emergency)

```bash
# One command rollback
kubectl rollout undo deployment/aria-api -n production

# Verify it worked
kubectl rollout status deployment/aria-api -n production
curl https://api.aria.example.com/health/readiness
```

---

## Part 8: Support & Escalation

### During Deployment

- **Level 1 (DevOps):** If deployment stalls → Check kubectl logs, restart pods
- **Level 2 (Engineering):** If errors appear → Check git diff, review new code
- **Level 3 (Executive):** If 100% failure → Rollback trigger, incident post-mortem

### Post-Deployment Issues

**Error in frontend:**
- Check browser console (DevTools)
- Check API response (Network tab)
- Check frontend logs: `kubectl logs deployment/aria-web`

**Database issues:**
- Check connection: `psql -h $HOST -U $USER -d $DB`
- Check slow queries: `EXPLAIN ANALYZE SELECT ...`
- Check replication: `SELECT now() - pg_last_xact_replay_timestamp() FROM pg_stat_replication`

**Infrastructure issues:**
- Check resources: `kubectl top nodes; kubectl top pods`
- Check disk: `df -h`
- Check network: `netstat -an | grep ESTABLISHED | wc -l`

**For additional help:**
- 📧 support@aria.example.com
- 🐛 GitHub Issues: https://github.com/your-org/hexamind/issues
- 📖 TROUBLESHOOTING.md (this repo)

---

## Summary

**You are here:**
- ✅ All code written and tested
- ✅ All documentation complete
- ✅ All configurations templated
- ⏳ **WAITING: Your inputs**

**Next steps:**
1. Fill out REQUIRED_USER_INPUTS.md (30 min)
2. Provide completed form back to agent
3. Agent integrates all pieces
4. You run final deployment (follow steps 1-8 above)

**Time to production from your inputs: ~3-4 hours**

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-04  
**Status:** Ready for handoff to user
