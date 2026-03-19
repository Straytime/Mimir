import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

// Mock the providers module before importing the hook
const mockSendHeartbeat = vi.fn().mockResolvedValue({ requestId: null, traceId: null });
const mockSetTerminalState = vi.fn();

let mockStoreValues: Record<string, unknown> = {};

vi.mock("@/features/research/providers/research-workspace-providers", () => ({
  useResearchRuntime: () => ({
    taskApiClient: {
      sendHeartbeat: mockSendHeartbeat,
    },
  }),
  useResearchSessionStore: (selector: (state: unknown) => unknown) => {
    const state = {
      remote: { snapshot: { status: mockStoreValues.snapshotStatus ?? null } },
      session: {
        heartbeatUrl: mockStoreValues.heartbeatUrl ?? null,
        taskToken: mockStoreValues.taskToken ?? null,
        sseState: mockStoreValues.sseState ?? null,
      },
      setTerminalState: mockSetTerminalState,
    };
    return selector(state);
  },
}));

// Must import after mocks are set up
import { renderHook } from "@testing-library/react";
import { useHeartbeatLoop } from "@/features/research/hooks/use-heartbeat-loop";

describe("useHeartbeatLoop", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockSendHeartbeat.mockClear();
    mockSetTerminalState.mockClear();
    mockStoreValues = {
      snapshotStatus: "running",
      heartbeatUrl: "/api/v1/tasks/tsk_1/heartbeat",
      taskToken: "token_1",
      sseState: "open",
    };
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("sends heartbeat immediately on effect start, before interval", () => {
    renderHook(() => useHeartbeatLoop());

    // Immediate send on mount, no timer advancement needed
    expect(mockSendHeartbeat).toHaveBeenCalledTimes(1);
    expect(mockSendHeartbeat).toHaveBeenCalledWith(
      expect.objectContaining({
        url: "/api/v1/tasks/tsk_1/heartbeat",
        token: "token_1",
      }),
    );
  });

  test("sends heartbeat again after interval", async () => {
    renderHook(() => useHeartbeatLoop());

    expect(mockSendHeartbeat).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(20_000);
    expect(mockSendHeartbeat).toHaveBeenCalledTimes(2);

    vi.advanceTimersByTime(20_000);
    expect(mockSendHeartbeat).toHaveBeenCalledTimes(3);
  });

  test("sends immediate heartbeat again when snapshotStatus changes (effect re-runs)", () => {
    const { rerender } = renderHook(() => useHeartbeatLoop());

    expect(mockSendHeartbeat).toHaveBeenCalledTimes(1);

    // Simulate snapshotStatus change causing effect to re-run
    mockStoreValues.snapshotStatus = "awaiting_user_input";
    rerender();

    // Should have sent another immediate heartbeat
    expect(mockSendHeartbeat).toHaveBeenCalledTimes(2);
  });

  test("does not send heartbeat for terminal status", () => {
    mockStoreValues.snapshotStatus = "failed";
    renderHook(() => useHeartbeatLoop());

    expect(mockSendHeartbeat).not.toHaveBeenCalled();
  });

  test("does not send heartbeat when SSE is not open", () => {
    mockStoreValues.sseState = "closed";
    renderHook(() => useHeartbeatLoop());

    expect(mockSendHeartbeat).not.toHaveBeenCalled();
  });
});
