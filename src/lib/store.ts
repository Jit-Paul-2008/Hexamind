// ─────────────────────────────────────────────────────────────────────────────
// Zustand store — single source of truth for the processing pipeline
// ─────────────────────────────────────────────────────────────────────────────

import { create } from "zustand";
import type {
  NodeStatus,
  PipelineQualityReport,
  PipelineSession,
} from "@/types/pipeline";
import { AGENTS } from "@/lib/agents";

interface PipelineStore {
  session: PipelineSession | null;
  nodeStatuses: Record<string, NodeStatus>;

  // Actions
  startPipeline: (query: string) => void;
  setBackendSessionId: (sessionId: string) => void;
  setNodeStatus: (agentId: string, status: NodeStatus) => void;
  appendChunk: (agentId: string, chunk: string) => void;
  setFinalAnswer: (answer: string) => void;
  setQualityLoading: () => void;
  setQualityReport: (report: PipelineQualityReport) => void;
  setQualityError: () => void;
  setPipelineError: (message: string) => void;
  resetPipeline: () => void;
}

const initialStatuses = (): Record<string, NodeStatus> => {
  const s: Record<string, NodeStatus> = { input: "idle", output: "idle" };
  AGENTS.forEach((a) => (s[a.id] = "idle"));
  return s;
};

export const usePipelineStore = create<PipelineStore>((set) => ({
  session: null,
  nodeStatuses: initialStatuses(),

  startPipeline: (query: string) => {
    const session: PipelineSession = {
      id: `session_${Date.now()}`,
      query,
      createdAt: Date.now(),
      status: "running",
      errorMessage: undefined,
      outputs: {},
      finalAnswer: "",
      qualityStatus: "idle",
    };
    AGENTS.forEach((a) => {
      session.outputs[a.id] = { agentId: a.id, status: "idle", content: "" };
    });
    set({
      session,
      nodeStatuses: { ...initialStatuses(), input: "done" },
    });
  },

  setBackendSessionId: (backendSessionId) =>
    set((state) => ({
      session: state.session ? { ...state.session, backendSessionId } : null,
    })),

  setNodeStatus: (agentId, status) =>
    set((state) => ({
      nodeStatuses: { ...state.nodeStatuses, [agentId]: status },
      session: state.session
        ? {
            ...state.session,
            outputs: {
              ...state.session.outputs,
              [agentId]: {
                ...state.session.outputs[agentId],
                status,
                ...(status === "active" ? { startedAt: Date.now() } : {}),
                ...(status === "done" ? { completedAt: Date.now() } : {}),
              },
            },
          }
        : null,
    })),

  appendChunk: (agentId, chunk) =>
    set((state) => ({
      session: state.session
        ? {
            ...state.session,
            outputs: {
              ...state.session.outputs,
              [agentId]: {
                ...state.session.outputs[agentId],
                content: (state.session.outputs[agentId]?.content || "") + chunk,
              },
            },
          }
        : null,
    })),

  setFinalAnswer: (answer) =>
    set((state) => ({
      session: state.session
        ? {
            ...state.session,
            status: "complete",
            finalAnswer: answer,
            qualityStatus: "loading",
          }
        : null,
      nodeStatuses: { ...state.nodeStatuses, output: "done" },
    })),

  setQualityLoading: () =>
    set((state) => ({
      session: state.session
        ? { ...state.session, qualityStatus: "loading" }
        : null,
    })),

  setQualityReport: (qualityReport) =>
    set((state) => ({
      session: state.session
        ? {
            ...state.session,
            qualityReport,
            qualityStatus: "ready",
          }
        : null,
    })),

  setQualityError: () =>
    set((state) => ({
      session: state.session
        ? {
            ...state.session,
            qualityStatus: "error",
          }
        : null,
    })),

  setPipelineError: (message) =>
    set((state) => ({
      session: state.session
        ? {
            ...state.session,
            status: "error",
            errorMessage: message,
            qualityStatus: state.session.qualityStatus === "loading" ? "error" : state.session.qualityStatus,
          }
        : null,
      nodeStatuses: { ...state.nodeStatuses, output: "error" },
    })),

  resetPipeline: () =>
    set({ session: null, nodeStatuses: initialStatuses() }),
}));
