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
  backendSessionId?: string;
  status: "idle" | "running" | "complete" | "error";
  outputs: Record<string, AgentOutput>;  // keyed by agentId
  finalAnswer: string;
  qualityStatus?: "idle" | "loading" | "ready" | "error";
  qualityReport?: PipelineQualityReport;
}

export interface PipelineQualityMetrics {
  citationCount: number;
  sourceCount: number;
  uniqueDomains: number;
  averageCredibility: number;
  contradictionCount: number;
  hasClaimToCitationMap: boolean;
  hasUncertaintyDisclosure: boolean;
}

export interface PipelineContradictionFinding {
  sourceA: string;
  sourceB: string;
  reason: string;
}

export interface PipelineQualityReport {
  sessionId: string;
  status: "pending" | "ready";
  overallScore: number;
  passing: boolean;
  regenerated?: boolean;
  metrics: PipelineQualityMetrics;
  contradictionFindings: PipelineContradictionFinding[];
  notes: string[];
}

// Backend SSE event shape — matches what the FastAPI backend will emit
export interface PipelineEvent {
  type: "agent_start" | "agent_chunk" | "agent_done" | "pipeline_done" | "error";
  agentId: string;
  chunk?: string;
  fullContent?: string;
  error?: string;
}
