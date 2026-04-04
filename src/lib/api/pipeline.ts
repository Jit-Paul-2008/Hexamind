import { startPipelineRun } from "@/lib/pipelineClient";
import type { NodeStatus, PipelineQualityReport } from "@/types/pipeline";

export type PipelineStreamHandlers = {
  onStart: (query: string) => void;
  onSession: (sessionId: string) => void;
  onNodeStatus: (agentId: string, status: NodeStatus) => void;
  onChunk: (agentId: string, chunk: string) => void;
  onDone: (finalAnswer: string) => void;
  onQualityLoading: () => void;
  onQualityReady: (report: PipelineQualityReport) => void;
  onQualityError: () => void;
};

export async function runPipelineStream(
  query: string,
  handlers: PipelineStreamHandlers
): Promise<EventSource | null> {
  return startPipelineRun(query, {
    startPipeline: handlers.onStart,
    setBackendSessionId: handlers.onSession,
    setNodeStatus: handlers.onNodeStatus,
    appendChunk: handlers.onChunk,
    setFinalAnswer: handlers.onDone,
    setQualityLoading: handlers.onQualityLoading,
    setQualityReport: handlers.onQualityReady,
    setQualityError: handlers.onQualityError,
  });
}
