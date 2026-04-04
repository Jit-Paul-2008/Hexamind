"use client";

import { useCallback, useRef, useState } from "react";
import type { NodeStatus, PipelineQualityReport } from "@/types/pipeline";
import { runPipelineStream } from "@/lib/api/pipeline";

type PipelineState = {
  isRunning: boolean;
  sessionId: string;
  finalAnswer: string;
  liveOutput: string;
  qualityReport: PipelineQualityReport | null;
  qualityLoading: boolean;
  error: string;
  nodeStatus: Record<string, NodeStatus>;
};

const initialState: PipelineState = {
  isRunning: false,
  sessionId: "",
  finalAnswer: "",
  liveOutput: "",
  qualityReport: null,
  qualityLoading: false,
  error: "",
  nodeStatus: {},
};

export function usePipeline() {
  const [state, setState] = useState<PipelineState>(initialState);
  const sourceRef = useRef<EventSource | null>(null);

  const cleanup = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
  }, []);

  const run = useCallback(
    async (query: string) => {
      cleanup();
      setState({ ...initialState, isRunning: true });

      const source = await runPipelineStream(query, {
        onStart: () => {
          setState((prev) => ({ ...prev, isRunning: true, error: "" }));
        },
        onSession: (sessionId) => {
          setState((prev) => ({ ...prev, sessionId }));
        },
        onNodeStatus: (agentId, status) => {
          setState((prev) => ({
            ...prev,
            nodeStatus: {
              ...prev.nodeStatus,
              [agentId]: status,
            },
          }));
        },
        onChunk: (_agentId, chunk) => {
          setState((prev) => ({ ...prev, liveOutput: `${prev.liveOutput}${chunk}` }));
        },
        onDone: (finalAnswer) => {
          setState((prev) => ({ ...prev, finalAnswer, isRunning: false }));
        },
        onQualityLoading: () => {
          setState((prev) => ({ ...prev, qualityLoading: true }));
        },
        onQualityReady: (qualityReport) => {
          setState((prev) => ({ ...prev, qualityReport, qualityLoading: false }));
        },
        onQualityError: () => {
          setState((prev) => ({
            ...prev,
            qualityLoading: false,
            error: prev.error || "Quality report fetch failed.",
          }));
        },
        onError: (message) => {
          setState((prev) => ({
            ...prev,
            isRunning: false,
            qualityLoading: false,
            error: message || "Pipeline failed.",
          }));
        },
      });

      if (!source) {
        setState((prev) => ({
          ...prev,
          isRunning: false,
          error: "Pipeline failed to start.",
        }));
        return;
      }

      sourceRef.current = source;
    },
    [cleanup]
  );

  return {
    ...state,
    run,
    cleanup,
  };
}
