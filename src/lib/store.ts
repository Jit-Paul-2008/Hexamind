// ─────────────────────────────────────────────────────────────────────────────
// Zustand store — single source of truth for the processing pipeline
// TODO(backend): replace mock flow with real WebSocket/SSE connection
// ─────────────────────────────────────────────────────────────────────────────

import { create } from "zustand";
import type { NodeStatus, PipelineSession, AgentOutput } from "@/types/pipeline";
import { AGENTS } from "@/lib/agents";

interface PipelineStore {
  session: PipelineSession | null;
  nodeStatuses: Record<string, NodeStatus>;

  // Actions
  startPipeline: (query: string) => void;
  setNodeStatus: (agentId: string, status: NodeStatus) => void;
  appendChunk: (agentId: string, chunk: string) => void;
  setFinalAnswer: (answer: string) => void;
  resetPipeline: () => void;
}

const initialStatuses = (): Record<string, NodeStatus> => {
  const s: Record<string, NodeStatus> = { input: "idle", output: "idle" };
  AGENTS.forEach((a) => (s[a.id] = "idle"));
  return s;
};

export const usePipelineStore = create<PipelineStore>((set, get) => ({
  session: null,
  nodeStatuses: initialStatuses(),

  startPipeline: (query: string) => {
    const session: PipelineSession = {
      id: `session_${Date.now()}`,
      query,
      createdAt: Date.now(),
      status: "running",
      outputs: {},
      finalAnswer: "",
    };
    AGENTS.forEach((a) => {
      session.outputs[a.id] = { agentId: a.id, status: "idle", content: "" };
    });
    set({
      session,
      nodeStatuses: { ...initialStatuses(), input: "done" },
    });
  },

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
        ? { ...state.session, status: "complete", finalAnswer: answer }
        : null,
      nodeStatuses: { ...state.nodeStatuses, output: "done" },
    })),

  resetPipeline: () =>
    set({ session: null, nodeStatuses: initialStatuses() }),
}));
