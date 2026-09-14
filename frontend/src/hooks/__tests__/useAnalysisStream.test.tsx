import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { useAnalysisStream } from "../useAnalysisStream";

const { getAnalysis } = vi.hoisted(() => ({ getAnalysis: vi.fn() }));
vi.mock("@/lib/api", () => ({ getAnalysis }));

class Socket {
  static instances: Socket[] = [];
  onopen: (() => void) | null = null; onclose: (() => void) | null = null;
  onerror: (() => void) | null = null; onmessage: ((event: MessageEvent) => void) | null = null;
  closed = false;
  constructor(public url: string) { Socket.instances.push(this); }
  close() { this.closed = true; } open() { this.onopen?.(); }
  message(data: unknown) { this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent); }
  closeFromServer() { this.onclose?.(); }
}

const run = { id: "run-1", ticker: "AAPL", analysis_date: "2025-01-01", asset_type: "stock", analysts: ["market"], llm_provider: "openai", research_depth: 1, status: "queued", signal: null, created_at: "2025-01-01T00:00:00Z", started_at: null, completed_at: null, quick_think_llm: "quick", deep_think_llm: "deep", reports: {}, agent_statuses: {}, error_message: null, final_state: null, last_event_seq: 0 } as const;

beforeEach(() => { Socket.instances = []; getAnalysis.mockReset().mockResolvedValue(run); vi.stubGlobal("WebSocket", Socket); });

test("seeds from REST, applies events once, and caps activity to 100 newest records", async () => {
  const { result } = renderHook(() => useAnalysisStream("run-1"));
  await waitFor(() => expect(Socket.instances).toHaveLength(1));
  const socket = Socket.instances[0]; act(() => socket.open());
  expect(socket.url).toContain("/ws/analysis/run-1?after=0");
  act(() => {
    for (let seq = 1; seq <= 101; seq++) socket.message({ run_id: "run-1", seq, emitted_at: "2025-01-01T00:00:00Z", type: "message", data: { messageId: String(seq), category: "Agent", content: String(seq) } });
    socket.message({ run_id: "run-1", seq: 101, emitted_at: "2025-01-01T00:00:00Z", type: "message", data: { messageId: "duplicate", category: "Agent", content: "duplicate" } });
  });
  expect(result.current.messages).toHaveLength(100);
  expect(result.current.messages[0].content).toBe("2");
});

test("reconnects with a cursor and stops reconnecting after a terminal event", async () => {
  vi.useFakeTimers();
  const { unmount } = renderHook(() => useAnalysisStream("run-1"));
  await vi.waitFor(() => expect(Socket.instances).toHaveLength(1));
  const first = Socket.instances[0];
  act(() => { first.open(); first.message({ run_id: "run-1", seq: 1, emitted_at: "2025-01-01T00:00:00Z", type: "status", data: { status: "running" } }); first.closeFromServer(); vi.advanceTimersByTime(500); });
  expect(Socket.instances).toHaveLength(2);
  expect(Socket.instances[1].url).toContain("after=1");
  act(() => { Socket.instances[1].message({ run_id: "run-1", seq: 2, emitted_at: "2025-01-01T00:00:00Z", type: "complete", data: { run } }); Socket.instances[1].closeFromServer(); vi.advanceTimersByTime(30000); });
  expect(Socket.instances).toHaveLength(2);
  unmount(); expect(Socket.instances[1].closed).toBe(true); vi.useRealTimers();
});

test("unmount cancels a pending reconnect and closes the active socket", async () => {
  vi.useFakeTimers();
  const { unmount } = renderHook(() => useAnalysisStream("run-1"));
  await vi.waitFor(() => expect(Socket.instances).toHaveLength(1));
  const socket = Socket.instances[0];
  act(() => {
    socket.open();
    socket.closeFromServer();
  });

  unmount();
  act(() => vi.advanceTimersByTime(30000));

  expect(socket.closed).toBe(true);
  expect(Socket.instances).toHaveLength(1);
  vi.useRealTimers();
});

test.each([
  ["completed", null],
  ["failed", "Analysis failed: RuntimeError"],
] as const)(
  "does not open a websocket when REST already reports %s",
  async (status, errorMessage) => {
    getAnalysis.mockResolvedValueOnce({
      ...run,
      status,
      error_message: errorMessage,
      last_event_seq: 4,
    });

    const { result } = renderHook(() => useAnalysisStream("run-1"));
    await waitFor(() => expect(result.current.run?.status).toBe(status));

    expect(Socket.instances).toHaveLength(0);
    expect(result.current.connection).toBe("closed");
    expect(result.current.error).toBe(errorMessage);
  },
);

test("applies the atomic failed run snapshot carried by a terminal error", async () => {
  vi.useFakeTimers();
  const { result, unmount } = renderHook(() => useAnalysisStream("run-1"));
  await vi.waitFor(() => expect(Socket.instances).toHaveLength(1));
  const socket = Socket.instances[0];
  act(() => {
    socket.open();
    socket.message({
      run_id: "run-1",
      seq: 1,
      emitted_at: "2025-01-01T00:00:00Z",
      type: "error",
      data: {
        code: "ANALYSIS_FAILED",
        message: "Analysis failed: RuntimeError",
        retryable: false,
        run: {
          ...run,
          status: "failed",
          error_message: "Analysis failed: RuntimeError",
          last_event_seq: 1,
        },
      },
    });
    socket.closeFromServer();
    vi.advanceTimersByTime(30000);
  });

  expect(result.current.run?.status).toBe("failed");
  expect(result.current.connection).toBe("closed");
  expect(result.current.error).toBe("Analysis failed: RuntimeError");
  expect(Socket.instances).toHaveLength(1);
  unmount();
  expect(socket.closed).toBe(true);
  vi.useRealTimers();
});
