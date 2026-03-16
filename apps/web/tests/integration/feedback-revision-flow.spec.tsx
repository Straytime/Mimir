import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";

import { ResearchPageClient } from "@/features/research/components/research-page-client";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import type { ResearchSessionState } from "@/features/research/store/research-session-store.types";
import {
  TaskApiClientError,
  type TaskApiClient,
} from "@/lib/api/task-api-client";
import type { EventEnvelope } from "@/lib/contracts";
import type {
  TaskEventSource,
  TaskEventSourceConnectArgs,
} from "@/lib/sse/task-event-source";
import {
  makeAnalysisCompletedEvent,
  makeAnalysisDeltaEvent,
  makeDeliverySummary,
  makeFeedbackAcceptedResponse,
  makePhaseChangedEvent,
  makeResearchOutline,
  makeResearchSessionState,
  makeRevisionSummary,
  makeTaskExpiredEvent,
  makeTaskFailedEvent,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";

class ControlledTaskEventSource<TEvent = unknown>
  implements TaskEventSource<TEvent>
{
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

function createMockRuntime(
  taskEventSource: TaskEventSource<EventEnvelope>,
  taskApiClientOverrides: Partial<TaskApiClient>,
) {
  return {
    taskApiClient: {
      createTask: vi.fn(),
      getTaskDetail: vi.fn(),
      submitClarification: vi.fn(),
      submitFeedback: vi.fn(),
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

function createAwaitingFeedbackStore(
  overrides: {
    session?: Partial<ResearchSessionState["session"]>;
    remote?: Partial<ResearchSessionState["remote"]>;
    stream?: Partial<ResearchSessionState["stream"]>;
    ui?: Partial<ResearchSessionState["ui"]>;
    deliveryUi?: Partial<ResearchSessionState["deliveryUi"]>;
  } = {},
) {
  return createResearchSessionStore(
    makeResearchSessionState({
      ...overrides,
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
        traceId: "trc_stage0",
        requestId: "req_stage0",
        eventsUrl: "/api/v1/tasks/tsk_stage0/events",
        heartbeatUrl: "/api/v1/tasks/tsk_stage0/heartbeat",
        disconnectUrl: "/api/v1/tasks/tsk_stage0/disconnect",
        connectDeadlineAt: "2026-03-16T00:10:00+08:00",
        sseState: "connecting",
        lastHeartbeatAt: null,
        ...overrides.session,
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "delivered",
          status: "awaiting_feedback",
          available_actions: [
            "submit_feedback",
            "download_markdown",
            "download_pdf",
          ],
        }),
        currentRevision: makeRevisionSummary({
          revision_id: "rev_stage0",
          revision_number: 1,
          requirement_detail: {
            research_goal: "旧版研究目标",
            domain: "互联网",
            requirement_details: "旧版需求摘要",
            output_format: "business_report",
            freshness_requirement: "high",
            language: "zh-CN",
          },
        }),
        delivery: makeDeliverySummary({
          artifact_count: 0,
          artifacts: [],
        }),
        ...overrides.remote,
      },
      stream: {
        analysisText: "旧分析缓冲",
        reportMarkdown: "# 第一轮报告\n\n旧报告正文。",
        outlineReady: true,
        outline: makeResearchOutline(),
        artifacts: [],
        ...overrides.stream,
      },
    }),
  );
}

async function flushAsyncWork() {
  await Promise.resolve();
  await Promise.resolve();
}

describe("Stage 7 feedback and revision transition flow", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("submits feedback, keeps the old report during waiting, then switches to the next revision on the first new SSE event", async () => {
    const user = userEvent.setup();
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    let resolveFeedbackRequest: (
      value: ReturnType<typeof makeFeedbackAcceptedResponse>,
    ) => void;
    const feedbackRequestPromise = new Promise<
      ReturnType<typeof makeFeedbackAcceptedResponse>
    >((resolve) => {
      resolveFeedbackRequest = resolve;
    });
    const submitFeedback = vi.fn().mockImplementation(() => feedbackRequestPromise);
    const store = createAwaitingFeedbackStore();

    render(
      <ResearchPageClient
        runtime={createMockRuntime(taskEventSource, {
          submitFeedback,
        })}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      await flushAsyncWork();
    });

    expect(screen.getByText("旧报告正文。")).toBeInTheDocument();
    expect(screen.queryByText("正在处理反馈并准备新一轮研究...")).not.toBeInTheDocument();

    await user.type(
      screen.getByRole("textbox", { name: "反馈意见" }),
      "请加强竞品对比，并补充商业化路径分析。",
    );
    await user.click(screen.getByRole("button", { name: "提交反馈" }));

    expect(store.getState().ui.pendingAction).toBe("submitting_feedback");
    expect(submitFeedback).toHaveBeenCalledWith({
      taskId: "tsk_stage0",
      token: "secret_stage0",
      request: {
        feedback_text: "请加强竞品对比，并补充商业化路径分析。",
      },
    });

    await act(async () => {
      resolveFeedbackRequest!(
        makeFeedbackAcceptedResponse({
          revision_id: "rev_stage1",
          revision_number: 2,
        }),
      );
      await flushAsyncWork();
    });

    await waitFor(() => {
      expect(store.getState().ui.pendingAction).toBeNull();
    });

    expect(store.getState().ui.revisionTransition).toEqual({
      status: "waiting_next_revision",
      pendingRevisionId: "rev_stage1",
      pendingRevisionNumber: 2,
    });
    expect(screen.getByText("正在处理反馈并准备新一轮研究...")).toBeInTheDocument();
    expect(screen.getByText("旧报告正文。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "下载 Markdown Zip" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "下载 PDF" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "提交反馈" })).toBeDisabled();

    await act(async () => {
      taskEventSource.emit(
        makePhaseChangedEvent({
          seq: 90,
          revision_id: "rev_stage1",
          phase: "processing_feedback",
          timestamp: "2026-03-16T00:01:10+08:00",
          payload: {
            from_phase: "delivered",
            to_phase: "processing_feedback",
            status: "running",
          },
        }),
      );
      await flushAsyncWork();
    });

    expect(store.getState().ui.revisionTransition.status).toBe("switching");
    expect(store.getState().stream.analysisText).toBe("");
    expect(store.getState().stream.reportMarkdown).toBe("");
    expect(store.getState().stream.outline).toBeNull();
    expect(store.getState().stream.artifacts).toEqual([]);
    expect(store.getState().remote.delivery).toBeNull();
    expect(screen.queryByText("旧报告正文。")).not.toBeInTheDocument();
    expect(screen.getByText("第 2 轮研究开始")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "会话状态" })).getByText(
        "正在处理反馈",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "时间线" })).getByText(
        "正在处理反馈",
      ),
    ).toBeInTheDocument();

    await act(async () => {
      taskEventSource.emit(
        makeAnalysisDeltaEvent({
          seq: 91,
          revision_id: "rev_stage1",
          phase: "processing_feedback",
          timestamp: "2026-03-16T00:01:12+08:00",
          payload: {
            delta: "正在根据反馈重写研究范围与竞品比较重点。",
          },
        }),
      );
      await flushAsyncWork();
    });

    expect(
      screen.getByText(/正在根据反馈重写研究范围与竞品比较重点。/),
    ).toBeInTheDocument();

    await act(async () => {
      taskEventSource.emit(
        makeAnalysisCompletedEvent({
          seq: 92,
          revision_id: "rev_stage1",
          phase: "processing_feedback",
          timestamp: "2026-03-16T00:01:18+08:00",
          payload: {
            requirement_detail: {
              research_goal: "补强竞品对比与商业化路径",
              domain: "互联网 / AI 产品",
              requirement_details: "重点分析竞品差异、用户价值与商业化机会。",
              output_format: "business_report",
              freshness_requirement: "high",
              language: "zh-CN",
            },
          },
        }),
      );
      await flushAsyncWork();
    });

    expect(store.getState().remote.currentRevision).toMatchObject({
      revision_id: "rev_stage1",
      revision_number: 2,
      requirement_detail: {
        research_goal: "补强竞品对比与商业化路径",
      },
    });

    await act(async () => {
      taskEventSource.emit(
        makePhaseChangedEvent({
          seq: 93,
          revision_id: "rev_stage1",
          phase: "planning_collection",
          timestamp: "2026-03-16T00:01:20+08:00",
          payload: {
            from_phase: "processing_feedback",
            to_phase: "planning_collection",
            status: "running",
          },
        }),
      );
      await flushAsyncWork();
    });

    await waitFor(() => {
      expect(store.getState().ui.revisionTransition.status).toBe("idle");
    });

    expect(
      screen.queryByText("正在处理反馈并准备新一轮研究..."),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "时间线" })).getByText(
        "新一轮研究已进入规划阶段",
      ),
    ).toBeInTheDocument();
  });

  test("shows validation errors in place and keeps the feedback draft on 422 validation_error", async () => {
    const user = userEvent.setup();
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const submitFeedback = vi.fn().mockRejectedValue(
      new TaskApiClientError({
        status: 422,
        code: "validation_error",
        message: "请求参数不合法。",
        detail: {
          errors: [
            {
              loc: ["body", "feedback_text"],
              msg: "反馈内容不能为空。",
              type: "value_error",
            },
          ],
        },
        requestId: "req_feedback_validation",
        traceId: null,
        retryAfterSeconds: null,
      }),
    );
    const store = createAwaitingFeedbackStore();

    render(
      <ResearchPageClient
        runtime={createMockRuntime(taskEventSource, {
          submitFeedback,
        })}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      await flushAsyncWork();
    });

    const textarea = screen.getByRole("textbox", { name: "反馈意见" });

    await user.type(textarea, "请补充更清晰的竞品商业化比较。");
    await user.click(screen.getByRole("button", { name: "提交反馈" }));

    await waitFor(() => {
      expect(store.getState().ui.pendingAction).toBeNull();
    });

    expect(screen.getByRole("alert")).toHaveTextContent("反馈内容不能为空。");
    expect(textarea).toHaveValue("请补充更清晰的竞品商业化比较。");
    expect(store.getState().ui.revisionTransition.status).toBe("idle");
    expect(
      screen.queryByText("正在处理反馈并准备新一轮研究..."),
    ).not.toBeInTheDocument();
  });

  test.each([
    {
      name: "task.failed",
      event: makeTaskFailedEvent({
        seq: 94,
        phase: "delivered",
      }),
      bannerText: "任务已失败，旧任务操作已禁用。",
    },
    {
      name: "task.expired",
      event: makeTaskExpiredEvent({
        seq: 95,
        phase: "delivered",
      }),
      bannerText: "任务已过期，旧任务操作已禁用。",
    },
  ])(
    "disables feedback and delivery actions after $name",
    async ({ event, bannerText }) => {
      const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
      const store = createAwaitingFeedbackStore();

      render(
        <ResearchPageClient
          runtime={createMockRuntime(taskEventSource, {})}
          store={store}
        />,
      );

      await act(async () => {
        taskEventSource.open();
        taskEventSource.emit(event);
        await flushAsyncWork();
      });

      expect(screen.getByText(bannerText)).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: "提交反馈" }),
      ).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "下载 Markdown Zip" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "下载 PDF" })).toBeDisabled();
    },
  );
});
