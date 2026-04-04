# Required User Inputs for ARIA UX Rollout Plan — 100% Completion

**Instructions:** Gather all items from this list while the agent works autonomously. Return all items at the end so they can be integrated into the final system.

---

## A. Design & Branding (Phase 1)

**Required for:** UI shell polish, visual consistency

- [x] **Primary Color Hex**: `#FF9A56` (warm orange — warm, inviting tone)
- [x] **Secondary Color Hex**: `#FFB84D` (warm golden amber)
- [x] **Danger Color Hex**: `#EF4444` (red — standard for errors)
- [x] **Logo File**: N/A — will use text-only "ARIA" for MVP
- [x] **Logo Text/Brand Name**: ARIA
- [x] **Default Avatar/Icon Set Preference**: Lucide (modern, open-source)
- [x] **Font Preferences**: 
  - [x] Display Font (headings): Inter
  - [x] Body Font: Inter
- [x] **Typography Scale**: Using Tailwind defaults (H1-H3, body, small, xsmall)

---

## B. Authentication & Security (Phase 4)

**Required for:** Auth module setup

- [x] **JWT Secret Key**: `***AUTO-GENERATE***` (32-char random string via `openssl rand -hex 32` at setup time)
- [x] **Auth Configuration**:
  - [x] Access Token Expiry: 30 minutes
  - [x] Refresh Token Expiry: 7 days
  - [x] Password Hashing Algorithm: bcrypt (industry standard, secure)
  - [x] Min Password Length: 8 characters
- [x] **Email Verification Required?**: False (skip for MVP)
- [x] **2FA/MFA Required?**: False (skip for MVP)
- [x] **CORS Allowed Origins**: `["http://localhost:3000", "http://localhost:3001"]` (dev); add production domains later
- [x] **API Rate Limiting**: 
  - [x] Requests per minute per user: 100
  - [x] Requests per minute per IP: 500

---

## C. Database Configuration (Phase 3)

**Required for:** Database initialization

- [x] **PostgreSQL Connection Details** (for production):
  - [x] Host: `postgres.example.com` (TBD — update at deployment)
  - [x] Port: 5432
  - [x] Username: `aria_user` (change in production)
  - [x] Password: `***SET-AT-DEPLOY-TIME***` (secure, 16+ chars)
  - [x] Database Name: `aria_prod`
- [x] **For Development**: SQLite in-memory for tests, local PostgreSQL optional
- [x] **Backup Strategy**:
  - [x] Daily backup retention: 30 days
  - [x] Backup location: Local filesystem initially, migrate to S3 for production
- [x] **Data Retention Policies**:
  - [x] Soft-delete for archived cases
  - [x] Audit log retention: 90 days
  - [x] Session data retention: 30 days
- [x] **Database Encryption at Rest?**: No for dev; Yes for production

---

## D. Monitoring & Observability (Phase 5)

**Required for:** Production metrics and alerting

- [x] **Prometheus Configuration**:
  - [x] Scrape interval: 15 seconds
  - [x] Retention period: 30 days
- [x] **Alerting Service**: Defer to Phase 5 (MVP uses logging only)
- [x] **Alert Thresholds** (when implemented):
  - [x] Error rate threshold: 2%
  - [x] API latency P95: 5000 ms
  - [x] Database query latency: 500 ms
  - [x] Memory usage: 80%
- [x] **Grafana Dashboard**: Defer to Phase 5
- [x] **Logging**: Console logging (stdout) for MVP; centralized logging (ELK/Loki) in production

---

## E. Feature Flags & Rollout (Phase 5)

**Required for:** Gradual rollout control

- [x] **Feature Flag Service**: In-memory/Redis-based (simple custom implementation for MVP)
- [x] **Initial Feature Flags to Create**:
  - [x] `enable_new_ui` → False (until Phase 1 complete)
  - [x] `enable_database_persistence` → False (until Phase 3 complete)
  - [x] `enable_advanced_compare` → True (available immediately)
  - [x] `enable_tavily_research` → True (if API key available)

---

## F. Cloud & Infrastructure (Phase 3+)

**Required for:** Docker, deployment, storage

- [x] **Docker Registry**: Docker Hub (optional; skip for local-only dev)
- [x] **Storage Service** (for DOCX exports, artifacts):
  - [x] Provider: Local filesystem (dev); migrate to S3 for production
  - [x] Path: `./artifacts/` (local dev); `s3://aria-artifacts/` (production)
  - [x] Retention policy: 90 days
- [x] **Redis Configuration**: Defer to Phase 5 (use in-memory cache for MVP)
- [x] **Deployment Target**:
  - [x] Docker Compose (MVP)
  - [x] Kubernetes / Cloud Run (production — TBD)
  - [x] Production domain: `aria.example.com` (TBD at deployment)
  - [x] SSL certificate: Let's Encrypt (auto-renewal via Certbot or cloud provider)

---

## G. Email & Notifications (Phase 4+)

**Required for:** User communications — Deferred to Phase 4+

- [x] **Email Service**: Skip for MVP (email verification disabled)
- [x] **Templates**: Will create during Phase 4
- [x] **Notification Preferences**: In-app only for MVP

---

## H. Analytics & Tracking (Optional, Post-Phase 5)

**Required for:** Understanding user behavior — Deferred

- [x] **Analytics Provider**: Defer to post-Phase 5
- [x] **Error Tracking**: Defer to post-Phase 5 (console logs for MVP)

---

## I. Compliance & Security (Phase 4+)

**Required for:** Production readiness

- [x] **Compliance Requirements**:
  - [x] HIPAA? No (not required for MVP)
  - [x] GDPR? Not currently (but design for export/deletion if EU users added)
  - [x] SOC2? No (not required for MVP)
- [x] **Data Privacy Policy**: TBD (will provide during Phase 4)
- [x] **Terms of Service**: TBD (will provide during Phase 4)
- [x] **Privacy Notice**: TBD (will provide during Phase 4)
- [x] **Security Contact Email**: `security@aria.local` (change for production)
- [x] **Encryption at Rest**: No for dev; Yes for production
- [x] **Encryption in Transit**: TLS 1.2+ (upgrade to 1.3 for production)
- [x] **IP Allowlist**: Not enabled (defer to beta phase if needed)

---

## J. Third-Party Integrations (Phase 2+)

**Required for:** Pipeline capabilities

- [x] **Tavily API Key** (web research — low cost, quality search):
  - [x] Status: TBD (register at https://tavily.com; ~$10/month for MVP tier)
  - [x] API key: To be added to `.env` at setup
- [x] **Model Providers** (beyond Ollama local):
  - [x] Google Gemini API: No (skip for MVP — use Ollama only)
  - [x] OpenRouter API: No (skip for MVP)
  - [x] Other: None planned
- [x] **Sarvam Integration** (export/transform): Defer to Phase 4

---

## K. Testing & Load Goals (Phase 5)

**Required for:** Load testing and performance validation

- [x] **Load Test Parameters**:
  - [x] Target concurrent users: 100
  - [x] Target duration: 10 minutes
  - [x] Expected P95 latency: 5000 ms
  - [x] Expected error rate: <1%
- [x] **Peak Traffic Expectations** (TBD):
  - [x] Estimated monthly active users: TBD
  - [x] Estimated concurrent users at peak: TBD
  - [x] Requests/second at peak: TBD
- [x] **Scaling Strategy** (defer to Phase 5):
  - [x] Docker Compose: manual scaling
  - [x] Kubernetes: auto-scale on CPU (80%)

---

## L. Internal Team & Runbooks (Phase 5)

**Required for:** Operational readiness — Defer to Phase 5

- [x] **On-Call Rotation**: TBD (will establish during production rollout)  
- [x] **Incident Response**: TBD (email/Slack to be configured)
- [x] **Rollback Authority**: TBD (product/tech lead)

---

## M. Documentation & Approvals (All Phases)

**Required for:** Final sign-off — Will gather during rollout

- [x] **Architecture Review**: Pending Phase 1 completion
- [x] **Security Review**: Pending Phase 4 completion
- [x] **Product Sign-Off**: Pending Phase 1+ UI completion
- [x] **Business/Legal Sign-Off**: Pending deployment planning

---

## N. Personalization (Optional but Recommended)

**Required for:** Customizing the experience

- [x] **Organization Name**: ARIA Team
- [x] **Support Email**: `support@aria.local` (change for production)
- [x] **Support Portal URL**: N/A (MVP)
- [x] **Documentation URL**: `https://docs.aria.local` (TBD)

---

## Summary Checklist

**To complete this form:**

1. Go through each section (A–N)
2. Save your answers in a text file, document, or reply directly
3. For sensitive items (passwords, keys, tokens):
   - Mark as `***REDACTED***` if sharing with team
   - Plan to provide securely (1Password, LastPass, secure share link) at final integration
4. For items marked "Suggested", confirm or provide your preference
5. For optional items, mark as "N/A" or "Will add later"

---

## Delivery Format (at end of autonomous work)

Please provide your filled-out version of this form as:
- Markdown file (paste into workspace)
- Text file
- Structured reply to the agent

All will be integrated into:
- `.env.production` (secrets management)
- `docker-compose.override.yml` (local overrides)
- `src/config/constants.ts` (frontend config)
- `ai-service/config.py` (backend config)
- Prometheus alert rules
- Feature flag seeding script

---

**Status:** ✅ FILLED WITH MVP DEFAULTS | **Last Updated:** 2026-04-04

---

## QUICK REFERENCE: What Still Needs User Input

### Required Now (Before Phase 1):
1. **Tavily API Key** (optional but recommended; ~$10/month) — https://tavily.com
2. Confirm warm color palette (`#FF9A56`, `#FFB84D`, `#EF4444`) — or provide alternatives

### Required Before Production:
1. **Database Password** — set at deployment time
2. **JWT Secret** — auto-generated at setup
3. **Production Domain** — (e.g., `aria.example.com`)
4. **SSL Certificate** — Let's Encrypt or provided
5. **Legal Docs** (Privacy Policy, ToS) — for Phase 4

### Optional (Post-MVP):
- On-call contacts
- Observability integrations (ELK, Datadog, etc.)
- Advanced integrations (Gemini API, Sarvam, etc.)
