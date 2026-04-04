import type { PipelineQualityReport } from "@/types/pipeline";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchQualityReport(sessionId: string): Promise<PipelineQualityReport> {
  const response = await fetch(`${API_BASE_URL}/api/pipeline/${sessionId}/quality`);
  if (!response.ok) {
    throw new Error(`Failed to load quality report (${response.status})`);
  }
  return (await response.json()) as PipelineQualityReport;
}
