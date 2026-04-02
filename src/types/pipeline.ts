// ─────────────────────────────────────────────────────────────────────────────
// Shared pipeline types — used across store, nodes, hooks, and backend stubs
// ─────────────────────────────────────────────────────────────────────────────

export type NodeStatus = "idle" | "active" | "done" | "error";

export interface AgentOutput {
  agentId: string;
  status: NodeStatus;
  content: string;       // full text accumulated so far
  startedAt?: number;    // timestamp
  completedAt?: number;
}

export interface PipelineSession {
  id: string;
  query: string;
  createdAt: number;
  status: "idle" | "running" | "complete" | "error";
  outputs: Record<string, AgentOutput>;  // keyed by agentId
  finalAnswer: string;
}

// Backend SSE event shape — matches what the FastAPI backend will emit
export interface PipelineEvent {
  type: "agent_start" | "agent_chunk" | "agent_done" | "pipeline_done" | "error";
  agentId: string;
  chunk?: string;
  fullContent?: string;
  error?: string;
}
