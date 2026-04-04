# Required User Inputs for ARIA UX Rollout Plan — 100% Completion

**Instructions:** Gather all items from this list while the agent works autonomously. Return all items at the end so they can be integrated into the final system.

---

## A. Design & Branding (Phase 1)

**Required for:** UI shell polish, visual consistency

- [ ] **Primary Color Hex** (e.g., `#3B82F6`): For buttons, links, accents
- [ ] **Secondary Color Hex** (e.g., `#10B981`): For success states, highlights
- [ ] **Danger Color Hex** (e.g., `#EF4444`): For errors, destructive actions
- [ ] **Logo File** (SVG or PNG): For navbar/header
- [ ] **Logo Text/Brand Name**: If different from "ARIA"
- [ ] **Default Avatar/Icon Set Preference**: Heroicons, Lucide, Feather, or custom?
- [ ] **Font Preferences**: 
  - [ ] Display Font (headings) — Suggestion: Inter, Poppins?
  - [ ] Body Font — Suggestion: Inter, Plus Jakarta Sans?
- [ ] **Typography Scale** (optional; will use Tailwind defaults if not provided):
  - [ ] H1, H2, H3 sizes
  - [ ] Body, small, xsmall sizes

---

## B. Authentication & Security (Phase 4)

**Required for:** Auth module setup

- [ ] **JWT Secret Key**: 32+ character random string (generate via `openssl rand -hex 32`)
  - *Or approval to auto-generate during setup?*
- [ ] **Auth Configuration**:
  - [ ] Access Token Expiry (minutes): Suggested 30
  - [ ] Refresh Token Expiry (days): Suggested 7
  - [ ] Password Hashing Algorithm Confirmation: pbkdf2_sha256 or bcrypt?
  - [ ] Min Password Length: Suggested 8
- [ ] **Email Verification Required?** (True/False)
  - [ ] If yes: Email service credentials (SendGrid, Mailgun, AWS SES)
  - [ ] If yes: Email verification template/content
- [ ] **2FA/MFA Required?** (True/False)
  - [ ] If yes: TOTP or SMS-based?
- [ ] **CORS Allowed Origins** (list of domains for production):
  - [ ] Example: `["https://yourapp.com", "https://app.yourapp.com"]`
- [ ] **API Rate Limiting**: 
  - [ ] Requests per minute per user (Suggested: 100)
  - [ ] Requests per minute per IP (Suggested: 500)

---

## C. Database Configuration (Phase 3)

**Required for:** Database initialization

- [ ] **PostgreSQL Connection Details** (for production):
  - [ ] Host: (e.g., `db.example.com`)
  - [ ] Port: (default 5432)
  - [ ] Username: (e.g., `aria_user`)
  - [ ] Password: (secure password)
  - [ ] Database Name: (e.g., `aria_prod`)
- [ ] **For Development**: Confirm SQLite in-memory for tests? Or separate test DB?
- [ ] **Backup Strategy**:
  - [ ] Daily backup retention (days): Suggested 30
  - [ ] Backup location: S3 bucket, local, cloud provider?
- [ ] **Data Retention Policies**:
  - [ ] Soft-delete or hard-delete for archived cases? (Suggested: soft-delete)
  - [ ] Audit log retention (days): Suggested 90
  - [ ] Session data retention (days): Suggested 30
- [ ] **Database Encryption at Rest?** (True/False)

---

## D. Monitoring & Observability (Phase 5)

**Required for:** Production metrics and alerting

- [ ] **Prometheus Configuration**:
  - [ ] Scrape interval (seconds): Suggested 15
  - [ ] Retention period (days): Suggested 30
- [ ] **Alerting Service**:
  - [ ] Provider: Alertmanager, PagerDuty, Datadog, New Relic?
  - [ ] [Provider]  API key/credentials (if applicable)
  - [ ] Alert Slack channel (if using Slack)
  - [ ] Alert email address(es)
- [ ] **Alert Thresholds**:
  - [ ] Error rate threshold (%): Suggested 2%
  - [ ] API latency P95 threshold (ms): Suggested 5000
  - [ ] Database query latency threshold (ms): Suggested 500
  - [ ] Memory usage threshold (%): Suggested 80%
- [ ] **Grafana Dashboard**:
  - [ ] Host/URL: (e.g., `https://grafana.example.com`)
  - [ ] Admin username/password (auto-generate or provide)
- [ ] **Logging**:
  - [ ] Centralized logging provider: ELK, CloudWatch, Datadog, Loki?
  - [ ] [Provider] credentials/configuration
  - [ ] Log retention (days): Suggested 30

---

## E. Feature Flags & Rollout (Phase 5)

**Required for:** Gradual rollout control

- [ ] **Feature Flag Service**:
  - [ ] Provider: LaunchDarkly, Unleash, Custom Redis-based?
  - [ ] [Provider] API key/credentials (if applicable)
- [ ] **Initial Feature Flags to Create**:
  - [ ] `enable_new_ui` (default: False during rollout)
  - [ ] `enable_database_persistence` (default: False during verification)
  - [ ] `enable_advanced_compare` (default: False)
  - [ ] Any others specific to your needs?

---

## F. Cloud & Infrastructure (Phase 3+)

**Required for:** Docker, deployment, storage

- [ ] **Docker Registry**:
  - [ ] Provider: Docker Hub, ECR, GCR, GitLab Registry?
  - [ ] Registry URL (e.g., `docker.io/yourname`)
  - [ ] Registry credentials (username/token)
- [ ] **Storage Service** (for DOCX exports, artifacts):
  - [ ] Provider: S3, GCS, Azure Blob, local filesystem?
  - [ ] Bucket name (S3) or path
  - [ ] Credentials/API keys
  - [ ] Retention policy (days): Suggested 90
- [ ] **Redis Configuration** (Phase 5, optional):
  - [ ] Host: (e.g., `redis.example.com`)
  - [ ] Port: (default 6379)
  - [ ] Password: (if auth required)
  - [ ] TTL for cached sessions (seconds): Suggested 300
- [ ] **Deployment Target**:
  - [ ] Kubernetes, Docker Compose, Cloud Run, EC2, Heroku?
  - [ ] [Target] deployment credentials/access
  - [ ] Production domain: (e.g., `aria.example.com`)
  - [ ] SSL certificate (auto via Let's Encrypt or provide)?

---

## G. Email & Notifications (Phase 4+)

**Required for:** User communications

- [ ] **Email Service Setup** (if Phase 4 includes email verification):
  - [ ] Provider: SendGrid, Mailgun, AWS SES, custom SMTP?
  - [ ] API key or SMTP credentials
  - [ ] "From" email address (e.g., `noreply@aria.example.com`)
- [ ] **Email Templates**:
  - [ ] Welcome email (HTML template)
  - [ ] Password reset email (HTML template)
  - [ ] Verification email (HTML template)
- [ ] **Notification Preferences**:
  - [ ] Send notifications for: pipeline completion, quality alerts, team invitations?
  - [ ] Default notification channels: Email, in-app, both?

---

## H. Analytics & Tracking (Optional, Post-Phase 5)

**Required for:** Understanding user behavior (not blocking rollout)

- [ ] **Analytics Provider**:
  - [ ] Google Analytics, Mixpanel, Amplitude, custom?
  - [ ] [Provider] tracking ID or API key
- [ ] **Error Tracking**:
  - [ ] Sentry, Rollbar, Honeybadger, or internal logging?
  - [ ] [Provider] DSN or credentials

---

## I. Compliance & Security (Phase 4+)

**Required for:** Production readiness

- [ ] **Compliance Requirements**:
  - [ ] HIPAA? (Yes/No)
  - [ ] GDPR? (Yes/No)
  - [ ] SOC2? (Yes/No)
  - [ ] Other?
- [ ] **Data Privacy Policy**: URL or approved text
- [ ] **Terms of Service**: URL or approved text
- [ ] **Privacy Notice**: URL or approved text
- [ ] **Security Contact Email**: (e.g., `security@example.com`)
- [ ] **Encryption at Rest**: Required? (Suggested: Yes for prod)
- [ ] **Encryption in Transit**: TLS 1.3+? (Suggested: Yes)
- [ ] **IP Allowlist** (if restricting access during beta):
  - [ ] List of allowed IPs/CIDR ranges

---

## J. Third-Party Integrations (Phase 2+)

**Required for:** Pipeline capabilities

- [ ] **Tavily API Key** (web research):
  - [ ] API key: (get from https://tavily.com)
- [ ] **Model Providers** (beyond Ollama local):
  - [ ] Google Gemini API key? (Yes/No + key if yes)
  - [ ] OpenRouter API key? (Yes/No + key if yes)
  - [ ] Other model providers?
- [ ] **Sarvam Integration** (language transform/export):
  - [ ] Sarvam API endpoint: (provided or custom?)
  - [ ] Sarvam API key: (if required)

---

## K. Testing & Load Goals (Phase 5)

**Required for:** Load testing and performance validation

- [ ] **Load Test Parameters**:
  - [ ] Target concurrent users: Suggested 100
  - [ ] Target duration: Suggested 10 minutes
  - [ ] Expected P95 latency threshold (ms): Suggested 5000
  - [ ] Expected error rate threshold (%): Suggested <1%
- [ ] **Peak Traffic Expectations**:
  - [ ] Estimated monthly active users: 
  - [ ] Estimated concurrent users at peak: 
  - [ ] Expected requests/second at peak: 
- [ ] **Scaling Strategy**:
  - [ ] Auto-scale based on: CPU, memory, request count?
  - [ ] Min replicas: Suggested 2
  - [ ] Max replicas: Suggested 10

---

## L. Internal Team & Runbooks (Phase 5)

**Required for:** Operational readiness

- [ ] **On-Call Rotation**: 
  - [ ] Primary contact: (name, email, phone)
  - [ ] Secondary contact: (name, email, phone)
- [ ] **Incident Response**:
  - [ ] Incident response channel (Slack, Teams, email?)
  - [ ] Who can authorize rollbacks?
  - [ ] Escalation path for P0 issues
- [ ] **Rollback Authority**:
  - [ ] Who can trigger feature flag disables?
  - [ ] Who can trigger DB rollbacks?
  - [ ] Who can trigger full redeployment?

---

## M. Documentation & Approvals (All Phases)

**Required for:** Final sign-off

- [ ] **Architecture Review**: 
  - [ ] Approved by: (name, date)
  - [ ] Any concerns or special requirements?
- [ ] **Security Review**:
  - [ ] Approved by: (name, date)
  - [ ] Any required security hardening?
- [ ] **Product Sign-Off**:
  - [ ] Approved by: (name, date)
  - [ ] Any UX refinements requested?
- [ ] **Business/Legal Sign-Off**:
  - [ ] Approved by: (name, date)
  - [ ] Any compliance exceptions granted?

---

## N. Personalization (Optional but Recommended)

**Required for:** Customizing the experience

- [ ] **Organization Name**: (e.g., "Acme Research Corp")
- [ ] **Support Email**: (e.g., `support@example.com`)
- [ ] **Support Portal URL** (if exists): (e.g., `https://support.example.com`)
- [ ] **Documentation URL**: (e.g., `https://docs.aria.example.com`)

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

**Status:** Ready for user input | **Last Updated:** 2026-04-04
