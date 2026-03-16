import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, test, vi } from "vitest";

import { ResearchPageClient } from "@/features/research/components/research-page-client";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import type { ResearchSessionState } from "@/features/research/store/research-session-store.types";
import { createFetchTaskApiClient, type TaskApiClient } from "@/lib/api/task-api-client";
import type { EventEnvelope } from "@/lib/contracts";
import type {
  TaskEventSource,
  TaskEventSourceConnectArgs,
} from "@/lib/sse/task-event-source";
import {
  makeAnalysisCompletedEvent,
  makeAnalysisDeltaEvent,
  makeClarificationAcceptedResponse,
  makeClarificationCountdownStartedEvent,
  makeClarificationFallbackToNaturalEvent,
  makeClarificationNaturalReadyEvent,
  makeClarificationOptionsReadyEvent,
  makeClarificationValidationErrorResponse,
  makeResearchSessionState,
  makeTaskSnapshot,
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

  emit(event: TEvent) {
    this.activeArgs?.onEvent(event);
  }
}

const CLARIFICATION_API_URL = new URL(
  "/api/v1/tasks/tsk_stage0/clarification",
  window.location.origin,
).toString();

function createRuntime(taskEventSource: TaskEventSource<EventEnvelope>) {
  return {
    taskApiClient: createFetchTaskApiClient({
      baseUrl: window.location.origin,
      fetchImpl: window.fetch.bind(window),
    }),
    taskEventSource,
  };
}

function createMockRuntime(
  taskEventSource: TaskEventSource<EventEnvelope>,
  taskApiClientOverrides: Partial<TaskApiClient>,
) {
  return {
    taskApiClient: {
      createTask: vi.fn(),
      submitClarification: vi.fn(),
      sendHeartbeat: vi.fn().mockResolvedValue({
        requestId: "req_heartbeat",
        traceId: "trc_heartbeat",
      }),
      disconnectTask: vi.fn().mockResolvedValue({
        accepted: true,
        requestId: "req_disconnect",
        traceId: "trc_disconnect",
      }),
      ...taskApiClientOverrides,
    },
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

function createClarifyingStore(
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
      connectDeadlineAt: "2026-03-16T00:00:30+08:00",
      sseState: "connecting",
      lastHeartbeatAt: null,
      ...overrides.session,
    },
    remote: {
      snapshot: makeTaskSnapshot({
        task_id: "tsk_stage0",
        status: "running",
        phase: "clarifying",
        clarification_mode: "natural",
        available_actions: [],
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

describe("Stage 4 clarification flow", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  test("renders clarification.delta and enables natural input after clarification.natural.ready", async () => {
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createClarifyingStore();

    render(
      <ResearchPageClient
        runtime={createRuntime(taskEventSource)}
        store={store}
      />,
    );

    const textarea = screen.getByLabelText("澄清补充说明");
    expect(textarea).toBeDisabled();

    await act(async () => {
      taskEventSource.open();
      taskEventSource.emit({
        ...makeClarificationNaturalReadyEvent(),
        seq: 8,
      });
      taskEventSource.emit({
        seq: 7,
        event: "clarification.delta",
        task_id: "tsk_stage0",
        revision_id: "rev_stage0",
        phase: "clarifying",
        timestamp: "2026-03-13T14:30:34+08:00",
        payload: {
          delta: "请补充希望聚焦的市场范围。",
        },
      });
      await flushAsyncWork();
    });

    expect(textarea).toBeEnabled();
    expect(
      screen.getByText("请补充希望聚焦的市场范围。"),
    ).toBeInTheDocument();
  });

  test("renders option questions, defaults every answer to o_auto, and allows switching", async () => {
    const user = userEvent.setup();
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createClarifyingStore(
      {},
      {
        clarification_mode: "options",
      },
    );

    render(
      <ResearchPageClient
        runtime={createRuntime(taskEventSource)}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      taskEventSource.emit(makeClarificationOptionsReadyEvent());
      await flushAsyncWork();
    });

    expect(
      screen.getByText("这次研究更偏向哪个方向？"),
    ).toBeInTheDocument();
    expect(store.getState().ui.optionAnswers).toEqual({
      q_1: "o_auto",
    });
    expect(screen.getByRole("radio", { name: "自动" })).toBeChecked();

    await user.click(screen.getByRole("radio", { name: "主要参与者与格局" }));

    expect(store.getState().ui.optionAnswers).toEqual({
      q_1: "o_2",
    });
    expect(
      screen.getByRole("radio", { name: "主要参与者与格局" }),
    ).toBeChecked();
  });

  test("starts a 15-second countdown, resets it on option change, and auto submits on timeout", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-16T00:00:00+08:00"));
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createClarifyingStore(
      {},
      {
        clarification_mode: "options",
      },
    );
    const submitClarification = vi.fn().mockResolvedValue(
      makeClarificationAcceptedResponse(),
    );

    render(
      <ResearchPageClient
        runtime={createMockRuntime(taskEventSource, {
          submitClarification,
        })}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      taskEventSource.emit(makeClarificationOptionsReadyEvent());
      taskEventSource.emit(
        makeClarificationCountdownStartedEvent({
          payload: {
            duration_seconds: 15,
            started_at: "2026-03-16T00:00:00+08:00",
          },
        }),
      );
      await flushAsyncWork();
    });

    expect(screen.getByText("剩余 15 秒")).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(5_000);
      await flushAsyncWork();
    });

    expect(screen.getByText("剩余 10 秒")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("radio", { name: "行业现状与趋势" }));

    expect(screen.getByText("剩余 15 秒")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
      await flushAsyncWork();
    });

    expect(submitClarification).toHaveBeenCalledTimes(1);
    expect(submitClarification).toHaveBeenCalledWith({
      taskId: "tsk_stage0",
      token: "secret_stage0",
      request: {
        mode: "options",
        submitted_by_timeout: true,
        answers: [
          {
            question_id: "q_1",
            selected_option_id: "o_1",
            selected_label: "行业现状与趋势",
          },
        ],
      },
    });
  });

  test("manual clarification submit cancels the countdown and clears pendingAction afterwards", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-16T00:00:00+08:00"));
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createClarifyingStore(
      {},
      {
        clarification_mode: "options",
      },
    );
    let resolveRequest!: (response: ReturnType<typeof makeClarificationAcceptedResponse>) => void;
    const requestPromise = new Promise<ReturnType<typeof makeClarificationAcceptedResponse>>(
      (resolve) => {
        resolveRequest = resolve;
      },
    );
    const submitClarification = vi.fn().mockImplementation(() => requestPromise);
    const runtime = createMockRuntime(taskEventSource, {
      submitClarification,
    });

    render(
      <ResearchPageClient
        runtime={runtime}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      taskEventSource.emit(makeClarificationOptionsReadyEvent());
      taskEventSource.emit(
        makeClarificationCountdownStartedEvent({
          payload: {
            duration_seconds: 15,
            started_at: "2026-03-16T00:00:00+08:00",
          },
        }),
      );
      await flushAsyncWork();
    });

    fireEvent.click(screen.getByRole("button", { name: "提交澄清" }));

    expect(store.getState().ui.pendingAction).toBe("submitting_clarification");
    expect(submitClarification).toHaveBeenCalledWith({
      taskId: "tsk_stage0",
      token: "secret_stage0",
      request: {
        mode: "options",
        submitted_by_timeout: false,
        answers: [
          {
            question_id: "q_1",
            selected_option_id: "o_auto",
            selected_label: "自动",
          },
        ],
      },
    });

    await act(async () => {
      resolveRequest(makeClarificationAcceptedResponse());
      await requestPromise;
      await flushAsyncWork();
    });

    expect(store.getState().ui.pendingAction).toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(20_000);
      await flushAsyncWork();
    });

    expect(submitClarification).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/剩余 \d+ 秒/)).not.toBeInTheDocument();
  });

  test("shows inline 422 validation errors for natural clarification and keeps the draft", async () => {
    const user = userEvent.setup();
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createClarifyingStore();

    mswServer.use(
      http.post(CLARIFICATION_API_URL, () => {
        return HttpResponse.json(makeClarificationValidationErrorResponse(), {
          status: 422,
        });
      }),
    );

    render(
      <ResearchPageClient
        runtime={createRuntime(taskEventSource)}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      taskEventSource.emit(makeClarificationNaturalReadyEvent());
      await flushAsyncWork();
    });

    const textarea = screen.getByLabelText("澄清补充说明");

    await user.type(textarea, "保留这段澄清输入");
    await user.click(screen.getByRole("button", { name: "提交澄清" }));

    await screen.findByText("回答内容不能为空。");

    expect(textarea).toHaveValue("保留这段澄清输入");
    expect(textarea).toHaveAttribute("aria-invalid", "true");
    expect(store.getState().ui.pendingAction).toBeNull();
  });

  test("clears option state and switches back to natural mode on clarification.fallback_to_natural", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-16T00:00:00+08:00"));
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const submitClarification = vi.fn().mockResolvedValue(
      makeClarificationAcceptedResponse(),
    );
    const store = createClarifyingStore(
      {},
      {
        clarification_mode: "options",
      },
    );

    render(
      <ResearchPageClient
        runtime={createMockRuntime(taskEventSource, {
          submitClarification,
        })}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      taskEventSource.emit(makeClarificationOptionsReadyEvent());
      taskEventSource.emit(
        makeClarificationCountdownStartedEvent({
          payload: {
            duration_seconds: 15,
            started_at: "2026-03-16T00:00:00+08:00",
          },
        }),
      );
      await flushAsyncWork();
    });

    fireEvent.click(screen.getByRole("radio", { name: "主要参与者与格局" }));

    await act(async () => {
      taskEventSource.emit(makeClarificationFallbackToNaturalEvent());
      taskEventSource.emit(makeClarificationNaturalReadyEvent());
      await flushAsyncWork();
    });

    expect(store.getState().ui.optionAnswers).toEqual({});
    expect(store.getState().ui.clarificationCountdownDeadlineAt).toBeNull();
    expect(store.getState().stream.questionSet).toBeNull();
    expect(
      screen.queryByText("这次研究更偏向哪个方向？"),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("澄清补充说明")).toBeEnabled();
    expect(submitClarification).not.toHaveBeenCalled();
  });

  test("shows lightweight analysis text and stores requirement_detail after analysis.completed", async () => {
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createClarifyingStore(
      {
        stream: {
          clarificationText: "已进入需求分析。",
        },
      },
      {
        phase: "analyzing_requirement",
        status: "running",
      },
    );

    render(
      <ResearchPageClient
        runtime={createRuntime(taskEventSource)}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      taskEventSource.emit(
        makeAnalysisDeltaEvent({
          payload: {
            delta: "正在整理研究范围与输出格式。",
          },
        }),
      );
      await flushAsyncWork();
    });

    expect(
      screen.getByText("正在分析需求：正在整理研究范围与输出格式。"),
    ).toBeInTheDocument();

    const completedEvent = makeAnalysisCompletedEvent();

    await act(async () => {
      taskEventSource.emit(completedEvent);
      await flushAsyncWork();
    });

    await waitFor(() => {
      expect(store.getState().remote.currentRevision?.requirement_detail).toEqual(
        completedEvent.payload.requirement_detail,
      );
    });

    expect(
      screen.getByRole("heading", { name: "分析中国 AI 搜索产品竞争格局" }),
    ).toBeInTheDocument();
    expect(store.getState().stream.analysisText).toBe("");
    expect(
      screen.queryByText("正在分析需求：正在整理研究范围与输出格式。"),
    ).not.toBeInTheDocument();
  });
});
