# Hexamind v1/v2 Framework Plan

## Goal
Ship fast with a token-efficient product (v1), then monetize a premium high-power mode (v2).

## v1 (Default, Live Now)
- Framework: single-pass efficient analysis plus final synthesis.
- Objective: stable free-tier testing with minimal token burn.
- Intended users: early adopters, public demo traffic, onboarding users.
- Env setting:
  - `HEXAMIND_FRAMEWORK_VERSION=v1`

### Why v1 first
- Lower API cost per request.
- Fewer bottlenecks and failure points.
- Better throughput for free-tier and early customer acquisition.

## v2 (Premium, Later)
- Framework: robust multi-agent flow (advocate, skeptic, oracle, verifier, synthesiser).
- Objective: highest analytical rigor for paid plans and enterprise workflows.
- Intended users: paid tiers needing deep adversarial research quality.
- Env setting:
  - `HEXAMIND_FRAMEWORK_VERSION=v2`

### v2 readiness criteria
- Paid API budget is secured.
- Tiered pricing is live.
- Rate and reliability SLOs are met.
- Evaluation benchmarks show v2 quality gain over v1 on hard prompts.

## SaaS Packaging Recommendation
- Free Tier: v1 only, strict quotas, fair-use limits.
- Pro Tier: v2 access with higher limits and better SLAs.
- Team/Enterprise: v2 by default, optional policy/governance add-ons.

## Token Protection Policy (Now)
- Keep all public traffic on v1.
- Keep strict provider mode enabled.
- Avoid auto-regeneration loops by default.
- Reserve benchmark-heavy runs for controlled internal testing.

## Operational Toggle
Use one env var to switch behavior without code changes:
- `HEXAMIND_FRAMEWORK_VERSION=v1` for efficient mode.
- `HEXAMIND_FRAMEWORK_VERSION=v2` for robust multi-agent mode.

## Current Status
- v1 is active by default in local env and deployment config.
- v2 path exists in code but is disabled unless explicitly enabled.
