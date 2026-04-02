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
    const setNodeStatus = vi.fn();
    const appendChunk = vi.fn();
    const setFinalAnswer = vi.fn();

    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue({ sessionId: "session_test" }),
    });

    await startPipelineRun(
      "How should we ship the MVP?",
      {
        startPipeline,
        setNodeStatus,
        appendChunk,
        setFinalAnswer,
      },
      {
        apiBaseUrl: "http://127.0.0.1:8000",
        fetchImpl: fetchImpl as typeof fetch,
        eventSourceImpl: FakeEventSource as unknown as new (url: string) => EventSource,
      }
    );

    expect(startPipeline).toHaveBeenCalledWith("How should we ship the MVP?");
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
    expect(source.closed).toBe(true);
  });

  it("marks the output node errored when the backend start request fails", async () => {
    const startPipeline = vi.fn();
    const setNodeStatus = vi.fn();

    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: vi.fn(),
    });

    const source = await startPipelineRun(
      "Broken pipeline",
      {
        startPipeline,
        setNodeStatus,
        appendChunk: vi.fn(),
        setFinalAnswer: vi.fn(),
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