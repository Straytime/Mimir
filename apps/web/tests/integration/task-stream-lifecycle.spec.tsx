import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ResearchPageClient } from "@/features/research/components/research-page-client";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import type { ResearchSessionState } from "@/features/research/store/research-session-store.types";
import { createFetchTaskApiClient } from "@/lib/api/task-api-client";
import type { EventEnvelope } from "@/lib/contracts";
import type {
  TaskEventSource,
  TaskEventSourceConnectArgs,
} from "@/lib/sse/task-event-source";
import {
  makeCollectorFetchCompletedEvent,
  makeCollectorFetchStartedEvent,
  makeCollectorSearchCompletedEvent,
  makeCollectorSearchStartedEvent,
  makeClarificationDeltaEvent,
  makePhaseChangedEvent,
  makeResearchSessionState,
  makeTaskCreatedEvent,
  makeTaskExpiredEvent,
  makeTaskFailedEvent,
  makeTaskSnapshot,
  makeTaskTerminatedEvent,
} from "@/tests/fixtures/builders";
import { mswServer } from "@/tests/fixtures/msw-server";

class ControlledTaskEventSource<TEvent = unknown> implements TaskEventSource<TEvent> {
  connectCalls: TaskEventSourceConnectArgs<TEvent>[] = [];
  private activeArgs: TaskEventSourceConnectArgs<TEvent> | null = null;

  connect(args: TaskEventSourceConnectArgs<TEvent>) {
    this.connectCalls.push(args);
    this.activeArgs = args;

    return () => {
      if (this.activeArgs === args) {
        this.activeArgs = null;
      }
    };
  }

  open() {
    this.activeArgs?.onOpen();
  }

  openAt(index: number) {
    this.connectCalls[index]?.onOpen();
  }

  emit(event: TEvent) {
    this.activeArgs?.onEvent(event);
  }

  emitAt(index: number, event: TEvent) {
    this.connectCalls[index]?.onEvent(event);
  }

  error(error: unknown = new Error("stream interrupted")) {
    this.activeArgs?.onError(error);
  }

  errorAt(index: number, error: unknown = new Error("stream interrupted")) {
    this.connectCalls[index]?.onError(error);
  }

  close() {
    this.activeArgs?.onClose();
  }

  closeAt(index: number) {
    this.connectCalls[index]?.onClose();
  }
}

const HEARTBEAT_API_URL = new URL(
  "/api/v1/tasks/tsk_stage0/heartbeat",
  window.location.origin,
).toString();
const DISCONNECT_API_URL = new URL(
  "/api/v1/tasks/tsk_stage0/disconnect",
  window.location.origin,
).toString();

function createLifecycleRuntime(taskEventSource: TaskEventSource<EventEnvelope>) {
  return {
    taskApiClient: createFetchTaskApiClient({
      baseUrl: window.location.origin,
      fetchImpl: window.fetch.bind(window),
    }),
    taskEventSource,
  };
}

type ActiveStateOverrides = {
  session?: Partial<ResearchSessionState["session"]>;
  remote?: Partial<ResearchSessionState["remote"]>;
  stream?: Partial<ResearchSessionState["stream"]>;
  ui?: Partial<ResearchSessionState["ui"]>;
  deliveryUi?: Partial<ResearchSessionState["deliveryUi"]>;
};

function createActiveStore(
  overrides: ActiveStateOverrides = {},
  snapshotOverrides: Parameters<typeof makeTaskSnapshot>[0] = {},
) {
  const state = makeResearchSessionState({
    ...overrides,
    session: {
      taskId: "tsk_stage0",
      taskToken: "secret_stage0",
      traceId: "trc_stage0",
      requestId: "req_stage0",
      eventsUrl: "/api/v1/tasks/tsk_stage0/events",
      heartbeatUrl: "/api/v1/tasks/tsk_stage0/heartbeat",
      disconnectUrl: "/api/v1/tasks/tsk_stage0/disconnect",
      connectDeadlineAt: "2026-03-16T00:00:10+08:00",
      sseState: "connecting",
      lastHeartbeatAt: null,
      ...overrides.session,
    },
    remote: {
      snapshot: makeTaskSnapshot({
        task_id: "tsk_stage0",
        status: "running",
        phase: "clarifying",
        updated_at: "2026-03-16T00:00:00+08:00",
        available_actions: ["submit_feedback", "download_markdown"],
        ...snapshotOverrides,
      }),
      currentRevision: null,
      delivery: null,
      ...overrides.remote,
    },
  });

  return createResearchSessionStore(state);
}

async function flushAsyncWork() {
  await Promise.resolve();
  await Promise.resolve();
}

describe("Stage 3 task stream lifecycle", () => {
  beforeEach(() => {
    mswServer.use(
      http.post(HEARTBEAT_API_URL, () => {
        return new HttpResponse(null, { status: 204 });
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("replaces the bootstrap snapshot when the first task.created event arrives", async () => {
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createActiveStore();
    const authoritativeSnapshot = makeTaskSnapshot({
      task_id: "tsk_stage0",
      status: "awaiting_user_input",
      phase: "clarifying",
      updated_at: "2026-03-15T23:59:55+08:00",
      available_actions: ["submit_clarification"],
    });

    render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(taskEventSource)}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      taskEventSource.emit(
        makeTaskCreatedEvent({
          payload: {
            snapshot: authoritativeSnapshot,
          },
        }),
      );
      await flushAsyncWork();
    });

    expect(store.getState().remote.snapshot).toEqual(authoritativeSnapshot);
    expect(store.getState().session.sseState).toBe("open");
  });

  test("retries in-page after connect_deadline without locally terminating the task", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-16T00:00:00+08:00"));
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createActiveStore();

    render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(taskEventSource)}
        store={store}
      />,
    );

    expect(taskEventSource.connectCalls).toHaveLength(1);

    await act(async () => {
      vi.advanceTimersByTime(10_000);
      await flushAsyncWork();
    });

    expect(store.getState().ui.terminalReason).toBeNull();
    expect(store.getState().session.sseState).toBe("failed");
    expect(store.getState().remote.snapshot).toMatchObject({
      status: "running",
    });

    await act(async () => {
      vi.advanceTimersByTime(1_000);
      await flushAsyncWork();
    });

    expect(taskEventSource.connectCalls).toHaveLength(2);
    expect(store.getState().session.sseState).toBe("connecting");
  });

  test("starts the heartbeat loop only when the task is open and in a heartbeat-eligible status", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-16T00:00:00+08:00"));
    let heartbeatCalls = 0;

    mswServer.use(
      http.post(HEARTBEAT_API_URL, () => {
        heartbeatCalls += 1;
        return new HttpResponse(null, { status: 204 });
      }),
    );

    const openStore = createActiveStore({
      session: {
        sseState: "open",
      },
    });
    const { unmount } = render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(new ControlledTaskEventSource<EventEnvelope>())}
        store={openStore}
      />,
    );

    await act(async () => {
      vi.advanceTimersByTime(20_000);
      await flushAsyncWork();
    });

    expect(heartbeatCalls).toBe(2);

    unmount();
    heartbeatCalls = 0;

    const closedStore = createActiveStore(
      {
        session: {
          sseState: "connecting",
        },
      },
      {
        status: "terminated",
      },
    );

    render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(new ControlledTaskEventSource<EventEnvelope>())}
        store={closedStore}
      />,
    );

    await act(async () => {
      vi.advanceTimersByTime(40_000);
      await flushAsyncWork();
    });

    expect(heartbeatCalls).toBe(0);
  });

  test.each([409, 404])(
    "stops heartbeat polling and enters a terminal state when heartbeat returns %s",
    async (statusCode) => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date("2026-03-16T00:00:00+08:00"));
      let heartbeatCalls = 0;

      mswServer.use(
        http.post(HEARTBEAT_API_URL, () => {
          heartbeatCalls += 1;

          return HttpResponse.json(
            {
              error: {
                code: statusCode === 409 ? "invalid_task_state" : "task_not_found",
                message:
                  statusCode === 409
                    ? "当前任务状态不接受 heartbeat。"
                    : "任务不存在。",
                detail: {},
                request_id: "req_stage3",
                trace_id: "trc_stage3",
              },
            },
            { status: statusCode },
          );
        }),
      );

      const store = createActiveStore({
        session: {
          sseState: "open",
        },
      });

      render(
        <ResearchPageClient
          runtime={createLifecycleRuntime(new ControlledTaskEventSource<EventEnvelope>())}
          store={store}
        />,
      );

      await act(async () => {
        vi.advanceTimersByTime(20_000);
        await flushAsyncWork();
      });

      expect(store.getState().ui.terminalReason).toBe("terminated");

      await act(async () => {
        vi.advanceTimersByTime(40_000);
        await flushAsyncWork();
      });

      expect(heartbeatCalls).toBe(2);
      expect(store.getState().remote.snapshot).toMatchObject({
        status: "terminated",
        available_actions: [],
      });
    },
  );

  test("keeps sending heartbeat across clarification handoff and long collecting phase churn", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-16T00:00:00+08:00"));
    let heartbeatCalls = 0;
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();

    mswServer.use(
      http.post(HEARTBEAT_API_URL, () => {
        heartbeatCalls += 1;
        return new HttpResponse(null, { status: 204 });
      }),
    );

    const store = createActiveStore(
      {},
      {
        status: "awaiting_user_input",
        phase: "clarifying",
        available_actions: ["submit_clarification"],
      },
    );

    render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(taskEventSource)}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      await flushAsyncWork();
    });

    await act(async () => {
      vi.advanceTimersByTime(20_000);
      await flushAsyncWork();
    });

    expect(heartbeatCalls).toBe(2);

    await act(async () => {
      taskEventSource.emit(
        makePhaseChangedEvent({
          seq: 10,
          phase: "analyzing_requirement",
          timestamp: "2026-03-16T00:00:20+08:00",
          payload: {
            from_phase: "clarifying",
            to_phase: "analyzing_requirement",
            status: "running",
          },
        }),
      );
      await flushAsyncWork();
    });

    await act(async () => {
      vi.advanceTimersByTime(15_000);
      taskEventSource.emit(
        makePhaseChangedEvent({
          seq: 11,
          phase: "planning_collection",
          timestamp: "2026-03-16T00:00:35+08:00",
          payload: {
            from_phase: "analyzing_requirement",
            to_phase: "planning_collection",
            status: "running",
          },
        }),
      );
      await flushAsyncWork();
    });

    await act(async () => {
      vi.advanceTimersByTime(15_000);
      taskEventSource.emit(
        makePhaseChangedEvent({
          seq: 12,
          phase: "collecting",
          timestamp: "2026-03-16T00:00:50+08:00",
          payload: {
            from_phase: "planning_collection",
            to_phase: "collecting",
            status: "running",
          },
        }),
      );
      taskEventSource.emit(
        makeCollectorSearchStartedEvent({
          seq: 13,
          timestamp: "2026-03-16T00:00:50+08:00",
        }),
      );
      taskEventSource.emit(
        makeCollectorSearchCompletedEvent({
          seq: 14,
          timestamp: "2026-03-16T00:00:51+08:00",
        }),
      );
      await flushAsyncWork();
    });

    await act(async () => {
      vi.advanceTimersByTime(5_000);
      taskEventSource.emit(
        makeCollectorFetchStartedEvent({
          seq: 15,
          timestamp: "2026-03-16T00:00:55+08:00",
        }),
      );
      taskEventSource.emit(
        makeCollectorFetchCompletedEvent({
          seq: 16,
          timestamp: "2026-03-16T00:00:56+08:00",
        }),
      );
      await flushAsyncWork();
    });

    await act(async () => {
      vi.advanceTimersByTime(15_000);
      await flushAsyncWork();
    });

    expect(heartbeatCalls).toBe(5);
    expect(store.getState().remote.snapshot).toMatchObject({
      status: "running",
      phase: "collecting",
    });
    expect(store.getState().session.sseState).toBe("open");
  });

  test("reconnects in-page after SSE error, de-dupes replayed events, and keeps consuming later events", async () => {
    vi.useFakeTimers();
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createActiveStore();

    render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(taskEventSource)}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.openAt(0);
      taskEventSource.emitAt(
        0,
        makeClarificationDeltaEvent({
          seq: 2,
          payload: {
            delta: "第一段",
          },
        }),
      );
      taskEventSource.errorAt(0, new Error("network_lost"));
      await flushAsyncWork();
    });

    expect(store.getState().ui.terminalReason).toBeNull();
    expect(taskEventSource.connectCalls).toHaveLength(1);
    expect(store.getState().session.sseState).toBe("failed");

    await act(async () => {
      vi.advanceTimersByTime(1_000);
      await flushAsyncWork();
    });

    expect(taskEventSource.connectCalls).toHaveLength(2);
    expect(store.getState().session.sseState).toBe("connecting");

    await act(async () => {
      taskEventSource.openAt(1);
      taskEventSource.emitAt(
        1,
        makeClarificationDeltaEvent({
          seq: 2,
          payload: {
            delta: "第一段",
          },
        }),
      );
      taskEventSource.emitAt(
        1,
        makeClarificationDeltaEvent({
          seq: 3,
          payload: {
            delta: "第二段",
          },
        }),
      );
      await flushAsyncWork();
    });

    expect(store.getState().session.sseState).toBe("open");
    expect(store.getState().stream.clarificationText).toBe("第一段第二段");
    expect(store.getState().stream.lastEventSeq).toBe(3);
  });

  test("reconnects in-page after SSE close and continues observing later events", async () => {
    vi.useFakeTimers();
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createActiveStore();

    render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(taskEventSource)}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.openAt(0);
      taskEventSource.closeAt(0);
      await flushAsyncWork();
    });

    expect(store.getState().ui.terminalReason).toBeNull();
    expect(taskEventSource.connectCalls).toHaveLength(1);
    expect(store.getState().session.sseState).toBe("closed");
    expect(store.getState().remote.snapshot).toMatchObject({
      status: "running",
    });

    await act(async () => {
      vi.advanceTimersByTime(1_000);
      await flushAsyncWork();
    });

    expect(taskEventSource.connectCalls).toHaveLength(2);

    await act(async () => {
      taskEventSource.openAt(1);
      taskEventSource.emitAt(
        1,
        makePhaseChangedEvent({
          seq: 20,
          payload: {
            from_phase: "clarifying",
            to_phase: "analyzing_requirement",
            status: "running",
          },
        }),
      );
      await flushAsyncWork();
    });

    expect(store.getState().session.sseState).toBe("open");
    expect(store.getState().remote.snapshot).toMatchObject({
      phase: "analyzing_requirement",
    });
  });

  test("does not terminate or disconnect when the page only becomes hidden", async () => {
    const sendBeacon = vi.fn(() => true);
    Object.defineProperty(window.navigator, "sendBeacon", {
      configurable: true,
      writable: true,
      value: sendBeacon,
    });
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "hidden",
    });

    const store = createActiveStore({
      session: {
        sseState: "open",
      },
    });

    render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(new ControlledTaskEventSource<EventEnvelope>())}
        store={store}
      />,
    );

    document.dispatchEvent(new Event("visibilitychange"));

    expect(sendBeacon).not.toHaveBeenCalled();
    expect(store.getState().ui.terminalReason).toBeNull();
    expect(store.getState().remote.snapshot).toMatchObject({
      status: "running",
    });
  });

  test("does not reconnect after a terminal event closes the stream", async () => {
    vi.useFakeTimers();
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createActiveStore();

    render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(taskEventSource)}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.openAt(0);
      taskEventSource.emitAt(0, makeTaskFailedEvent());
      taskEventSource.closeAt(0);
      await flushAsyncWork();
    });

    await act(async () => {
      vi.advanceTimersByTime(5_000);
      await flushAsyncWork();
    });

    expect(taskEventSource.connectCalls).toHaveLength(1);
    expect(store.getState().ui.terminalReason).toBe("failed");
  });

  test("does not reconnect after explicit abort has been requested", async () => {
    vi.useFakeTimers();
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createActiveStore();

    render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(taskEventSource)}
        store={store}
      />,
    );

    act(() => {
      store.getState().setSessionContext({
        explicitAbortRequested: true,
      });
      store.getState().setPendingAction("disconnecting");
    });

    await act(async () => {
      taskEventSource.openAt(0);
      taskEventSource.errorAt(0, new Error("network_lost"));
      await flushAsyncWork();
    });

    await act(async () => {
      vi.advanceTimersByTime(5_000);
      await flushAsyncWork();
    });

    expect(taskEventSource.connectCalls).toHaveLength(1);
  });

  test("does not reconnect after the workspace unmounts", async () => {
    vi.useFakeTimers();
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createActiveStore();

    const { unmount } = render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(taskEventSource)}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.openAt(0);
      taskEventSource.errorAt(0, new Error("network_lost"));
      await flushAsyncWork();
    });

    unmount();

    await act(async () => {
      vi.advanceTimersByTime(5_000);
      await flushAsyncWork();
    });

    expect(taskEventSource.connectCalls).toHaveLength(1);
  });

  test("registers beforeunload for active tasks and removes it after a terminal event", async () => {
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createActiveStore();

    render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(taskEventSource)}
        store={store}
      />,
    );

    const activeBeforeUnloadEvent = new Event("beforeunload", {
      cancelable: true,
    });
    Object.defineProperty(activeBeforeUnloadEvent, "returnValue", {
      configurable: true,
      writable: true,
      value: undefined,
    });

    window.dispatchEvent(activeBeforeUnloadEvent);
    expect(activeBeforeUnloadEvent.defaultPrevented).toBe(true);

    await act(async () => {
      taskEventSource.open();
      taskEventSource.emit(makeTaskFailedEvent());
      await flushAsyncWork();
    });

    await screen.findByText("任务已失败，旧任务操作已禁用。");

    const terminalBeforeUnloadEvent = new Event("beforeunload", {
      cancelable: true,
    });
    Object.defineProperty(terminalBeforeUnloadEvent, "returnValue", {
      configurable: true,
      writable: true,
      value: undefined,
    });

    window.dispatchEvent(terminalBeforeUnloadEvent);
    expect(terminalBeforeUnloadEvent.defaultPrevented).toBe(false);
  });

  test("sends a disconnect beacon on pagehide with task_token in the request body", async () => {
    const sendBeacon = vi.fn(() => true);
    Object.defineProperty(window.navigator, "sendBeacon", {
      configurable: true,
      writable: true,
      value: sendBeacon,
    });

    const store = createActiveStore({
      session: {
        sseState: "open",
      },
    });

    render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(new ControlledTaskEventSource<EventEnvelope>())}
        store={store}
      />,
    );

    act(() => {
      window.dispatchEvent(new Event("pagehide"));
    });

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    const [url, body] = sendBeacon.mock.calls[0] as unknown as [string, Blob];

    expect(url).toBe("/api/v1/tasks/tsk_stage0/disconnect");
    await expect(new Response(body).text()).resolves.toBe(
      JSON.stringify({
        reason: "pagehide",
        task_token: "secret_stage0",
      }),
    );
  });

  test("posts a manual disconnect with Authorization header and clears disconnecting pendingAction", async () => {
    const user = userEvent.setup();
    const store = createActiveStore({
      session: {
        sseState: "open",
      },
    });
    let capturedAuthorization: string | null = null;
    let capturedBody: unknown = null;
    let resolveRequest!: () => void;
    const requestGate = new Promise<void>((resolve) => {
      resolveRequest = resolve;
    });

    mswServer.use(
      http.post(DISCONNECT_API_URL, async ({ request }) => {
        capturedAuthorization = request.headers.get("authorization");
        capturedBody = await request.json();
        await requestGate;

        return HttpResponse.json({ accepted: true }, { status: 202 });
      }),
    );

    render(
      <ResearchPageClient
        runtime={createLifecycleRuntime(new ControlledTaskEventSource<EventEnvelope>())}
        store={store}
      />,
    );

    await user.click(screen.getByRole("button", { name: "终止任务" }));

    expect(store.getState().ui.pendingAction).toBe("disconnecting");
    expect(screen.getByRole("button", { name: "正在终止..." })).toBeDisabled();
    expect(capturedAuthorization).toBe("Bearer secret_stage0");
    expect(capturedBody).toEqual({
      reason: "client_manual_abort",
    });

    resolveRequest();

    await waitFor(() => {
      expect(store.getState().ui.pendingAction).toBeNull();
    });
  });

  test.each([
    {
      name: "task.failed",
      event: makeTaskFailedEvent(),
      banner: "任务已失败，旧任务操作已禁用。",
    },
    {
      name: "task.terminated",
      event: makeTaskTerminatedEvent(),
      banner: "任务已终止，旧任务操作已禁用。",
    },
    {
      name: "task.expired",
      event: makeTaskExpiredEvent(),
      banner: "任务已过期，旧任务操作已禁用。",
    },
  ])(
    "disables old operations when %s arrives",
    async ({ event, banner }) => {
      const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
      const store = createActiveStore();

      render(
        <ResearchPageClient
          runtime={createLifecycleRuntime(taskEventSource)}
          store={store}
        />,
      );

      await act(async () => {
        taskEventSource.open();
        taskEventSource.emit(event);
        await flushAsyncWork();
      });

      await screen.findByText(banner);

      expect(screen.getByRole("button", { name: "终止任务" })).toBeDisabled();
      expect(store.getState().remote.snapshot?.available_actions).toEqual([]);
    },
  );
});
