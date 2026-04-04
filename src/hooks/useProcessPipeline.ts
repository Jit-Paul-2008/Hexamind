import { useCallback } from "react";
import { usePipelineStore } from "@/lib/store";
import { startPipelineRun } from "@/lib/pipelineClient";

export function useProcessPipeline() {
  const {
    startPipeline,
    setBackendSessionId,
    setNodeStatus,
    appendChunk,
    setFinalAnswer,
    setQualityLoading,
    setQualityReport,
    setQualityError,
    setPipelineError,
  } = usePipelineStore();

  const runPipeline = useCallback(
    async (query: string) => {
      void startPipelineRun(query, {
        startPipeline,
        setBackendSessionId,
        setNodeStatus,
        appendChunk,
        setFinalAnswer,
        setQualityLoading,
        setQualityReport,
        setQualityError,
        setPipelineError,
      });
    },
    [
      startPipeline,
      setBackendSessionId,
      setNodeStatus,
      appendChunk,
      setFinalAnswer,
      setQualityLoading,
      setQualityReport,
      setQualityError,
      setPipelineError,
    ]
  );

  return { runPipeline };
}
