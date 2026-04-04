import type { PipelineQualityReport } from "@/types/pipeline";

import { publicApiBaseUrl } from "@/lib/publicApiBaseUrl";

const API_BASE_URL = publicApiBaseUrl;

export async function fetchQualityReport(sessionId: string): Promise<PipelineQualityReport> {
  const response = await fetch(`${API_BASE_URL}/api/pipeline/${sessionId}/quality`);
  if (!response.ok) {
    throw new Error(`Failed to load quality report (${response.status})`);
  }
  return (await response.json()) as PipelineQualityReport;
}
