export enum PipelineEventType {
  AGENT_START = "agent_start",
  AGENT_CHUNK = "agent_chunk",
  AGENT_DONE = "agent_done",
  PIPELINE_DONE = "pipeline_done",
  ERROR = "error",
}

export interface PipelineEvent {
  type: PipelineEventType;
  agentId: string;
  chunk?: string;
  fullContent?: string;
  error?: string;
}

export interface StartPipelineRequest {
  query: string;
  reportLength?: "brief" | "moderate" | "huge";
}

export interface StartPipelineResponse {
  sessionId: string;
}
