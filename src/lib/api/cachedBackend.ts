import { publicApiBaseUrl } from "@/lib/publicApiBaseUrl";

/** Dedupes overlapping /health polls (StatusIndicator + TelemetryPanel). */
const HEALTH_TTL_MS = 8_000;

/** Competitive benchmark JSON changes rarely; avoid hammering on every telemetry tick. */
const COMPETITIVE_TTL_MS = 120_000;

type HealthResult = { data: Record<string, unknown> | null; ok: boolean };

let healthEntry: { at: number; value: HealthResult } | null = null;
let healthInflight: Promise<HealthResult> | null = null;

let competitiveEntry: { at: number; value: Record<string, unknown> | null } | null = null;
let competitiveInflight: Promise<Record<string, unknown> | null> | null = null;

/** Clears caches so the next fetch hits the network (e.g. Telemetry "Refresh"). */
export function invalidateBackendFetchCaches(): void {
  healthEntry = null;
  healthInflight = null;
  competitiveEntry = null;
  competitiveInflight = null;
}

export async function fetchHealthCached(): Promise<HealthResult> {
  const now = Date.now();
  if (healthEntry && now - healthEntry.at < HEALTH_TTL_MS) {
    return healthEntry.value;
  }
  if (healthInflight) {
    return healthInflight;
  }
  healthInflight = (async () => {
    try {
      const res = await fetch(`${publicApiBaseUrl}/health`);
      const ok = res.ok;
      const data = ok ? ((await res.json()) as Record<string, unknown>) : null;
      const value: HealthResult = { data, ok };
      healthEntry = { at: Date.now(), value };
      return value;
    } catch {
      const value: HealthResult = { data: null, ok: false };
      healthEntry = { at: Date.now(), value };
      return value;
    } finally {
      healthInflight = null;
    }
  })();
  return healthInflight;
}

export async function fetchCompetitiveBenchmarkCached(): Promise<Record<string, unknown> | null> {
  const now = Date.now();
  if (competitiveEntry && now - competitiveEntry.at < COMPETITIVE_TTL_MS) {
    return competitiveEntry.value;
  }
  if (competitiveInflight) {
    return competitiveInflight;
  }
  competitiveInflight = (async () => {
    try {
      const res = await fetch(`${publicApiBaseUrl}/api/benchmark/competitive`);
      const value = res.ok ? ((await res.json()) as Record<string, unknown>) : null;
      competitiveEntry = { at: Date.now(), value };
      return value;
    } catch {
      competitiveEntry = { at: Date.now(), value: null };
      return null;
    } finally {
      competitiveInflight = null;
    }
  })();
  return competitiveInflight;
}
