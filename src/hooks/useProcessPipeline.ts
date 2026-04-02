import { useCallback } from "react";
import { usePipelineStore } from "@/lib/store";
import { startPipelineRun } from "@/lib/pipelineClient";

export function useProcessPipeline() {
  const { startPipeline, setNodeStatus, appendChunk, setFinalAnswer } =
    usePipelineStore();

  const runPipeline = useCallback(
    async (query: string) => {
      void startPipelineRun(query, {
        startPipeline,
        setNodeStatus,
        appendChunk,
        setFinalAnswer,
      });
    },
    [startPipeline, setNodeStatus, appendChunk, setFinalAnswer]
  );

  return { runPipeline };
}
