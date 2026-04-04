import type { PipelineEvent } from "@/types/pipeline";

export function parsePipelineEvent(raw: string): PipelineEvent | null {
  try {
    return JSON.parse(raw) as PipelineEvent;
  } catch {
    return null;
  }
}
