import { describe, expect, it, vi } from "vitest";
import { startPipelineRun } from "../../src/lib/pipelineClient";

class FakeEventSource {
  static instances: FakeEventSource[] = [];

  url: string;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  private listeners: Map<string, Array<(event: MessageEvent) => void>> = new Map();
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: EventListener) {
    const handlers = this.listeners.get(type) ?? [];
    handlers.push(listener as (event: MessageEvent) => void);
    this.listeners.set(type, handlers);
  }

  close() {
    this.closed = true;
  }

  emit(type: string, payload: object) {
    const event = { data: JSON.stringify(payload) } as MessageEvent;
    this.onmessage?.(event);
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }
}

describe("startPipelineRun", () => {
  it("starts the pipeline and wires SSE events into the handlers", async () => {
    FakeEventSource.instances = [];

    const startPipeline = vi.fn();
    const setBackendSessionId = vi.fn();
    const setNodeStatus = vi.fn();
    const setPipelineError = vi.fn();
    const appendChunk = vi.fn();
    const setFinalAnswer = vi.fn();
    const setQualityLoading = vi.fn();
    const setQualityReport = vi.fn();
    const setQualityError = vi.fn();

    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue({ sessionId: "session_test" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue({
          sessionId: "session_test",
          status: "ready",
          overallScore: 82.5,
          passing: true,
          regenerated: false,
          metrics: {
            citationCount: 4,
            sourceCount: 6,
            uniqueDomains: 4,
            averageCredibility: 0.71,
            contradictionCount: 1,
            hasClaimToCitationMap: true,
            hasUncertaintyDisclosure: true,
          },
          contradictionFindings: [],
          notes: [],
        }),
      });

    await startPipelineRun(
      "How should we ship the MVP?",
      {
        startPipeline,
        setBackendSessionId,
        setNodeStatus,
        setPipelineError,
        appendChunk,
        setFinalAnswer,
        setQualityLoading,
        setQualityReport,
        setQualityError,
      },
      {
        apiBaseUrl: "http://127.0.0.1:8000",
        fetchImpl: fetchImpl as typeof fetch,
        eventSourceImpl: FakeEventSource as unknown as new (url: string) => EventSource,
      }
    );

    expect(startPipeline).toHaveBeenCalledWith("How should we ship the MVP?");
    expect(setBackendSessionId).toHaveBeenCalledWith("session_test");
    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/pipeline/start",
      expect.objectContaining({
        method: "POST",
      })
    );
    expect(FakeEventSource.instances).toHaveLength(1);
    expect(FakeEventSource.instances[0]?.url).toBe(
      "http://127.0.0.1:8000/api/pipeline/session_test/stream"
    );

    const source = FakeEventSource.instances[0];
    source.emit("agent_start", { type: "agent_start", agentId: "advocate" });
    source.emit("agent_chunk", {
      type: "agent_chunk",
      agentId: "advocate",
      chunk: "Hello ",
    });
    source.emit("agent_done", {
      type: "agent_done",
      agentId: "advocate",
    });
    source.emit("pipeline_done", {
      type: "pipeline_done",
      agentId: "output",
      fullContent: "Final answer",
    });

    expect(setNodeStatus).toHaveBeenCalledWith("advocate", "active");
    expect(appendChunk).toHaveBeenCalledWith("advocate", "Hello ");
    expect(setNodeStatus).toHaveBeenCalledWith("advocate", "done");
    expect(setNodeStatus).toHaveBeenCalledWith("output", "active");
    expect(setFinalAnswer).toHaveBeenCalledWith("Final answer");
    expect(setQualityLoading).toHaveBeenCalled();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/pipeline/session_test/quality"
    );
    expect(setQualityReport).toHaveBeenCalled();
    expect(source.closed).toBe(true);
  });

  it("marks the output node errored when the backend start request fails", async () => {
    const startPipeline = vi.fn();
    const setBackendSessionId = vi.fn();
    const setNodeStatus = vi.fn();
    const setPipelineError = vi.fn();

    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: vi.fn(),
    });

    const source = await startPipelineRun(
      "Broken pipeline",
      {
        startPipeline,
        setBackendSessionId,
        setNodeStatus,
        setPipelineError,
        appendChunk: vi.fn(),
        setFinalAnswer: vi.fn(),
        setQualityLoading: vi.fn(),
        setQualityReport: vi.fn(),
        setQualityError: vi.fn(),
      },
      {
        apiBaseUrl: "http://127.0.0.1:8000",
        fetchImpl: fetchImpl as typeof fetch,
        eventSourceImpl: FakeEventSource as unknown as new (url: string) => EventSource,
      }
    );

    expect(source).toBeNull();
    expect(setNodeStatus).toHaveBeenCalledWith("output", "error");
  });
});