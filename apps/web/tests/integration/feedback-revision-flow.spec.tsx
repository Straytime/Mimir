import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { ResearchPageClient } from "@/features/research/components/research-page-client";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import type { ResearchSessionState } from "@/features/research/store/research-session-store.types";
import type { TaskApiClient } from "@/lib/api/task-api-client";
import type { EventEnvelope } from "@/lib/contracts";
import type {
  TaskEventSource,
  TaskEventSourceConnectArgs,
} from "@/lib/sse/task-event-source";
import {
  makeDeliverySummary,
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

describe("Stage 7 feedback UI is disabled on the frontend", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("keeps feedback UI hidden even when the snapshot is awaiting_feedback", async () => {
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
      await flushAsyncWork();
    });

    expect(screen.getByText("旧报告正文。")).toBeInTheDocument();
    expect(
      screen.queryByRole("textbox", { name: "反馈意见" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "提交反馈" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("正在处理反馈并准备新一轮研究..."),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "下载 Markdown Zip" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "下载 PDF" })).toBeEnabled();
  });

  test("safely degrades when feedback-related state already exists in the store", async () => {
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createAwaitingFeedbackStore();

    store.setState((state) => ({
      ...state,
      ui: {
        ...state.ui,
        feedbackDraft: "保留但不显示的反馈草稿",
        feedbackFieldError: "不会显示",
        feedbackSubmitError: "不会显示",
        revisionTransition: {
          status: "waiting_next_revision",
          pendingRevisionId: "rev_stage1",
          pendingRevisionNumber: 2,
        },
      },
    }));

    render(
      <ResearchPageClient
        runtime={createMockRuntime(taskEventSource, {})}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      await flushAsyncWork();
    });

    expect(screen.getByText("旧报告正文。")).toBeInTheDocument();
    expect(
      screen.queryByRole("textbox", { name: "反馈意见" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "提交反馈" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Revision")).not.toBeInTheDocument();
    expect(screen.queryByText(/等待第 2 轮/)).not.toBeInTheDocument();
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
    "keeps feedback UI hidden and disables downloads after $name",
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
      expect(
        screen.queryByRole("textbox", { name: "反馈意见" }),
      ).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "下载 Markdown Zip" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "下载 PDF" })).toBeDisabled();
    },
  );
});
