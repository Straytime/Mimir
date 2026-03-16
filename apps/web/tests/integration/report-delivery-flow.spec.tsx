import { act, render, screen, waitFor, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, test } from "vitest";

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
  makeArtifactReadyEvent,
  makeDeliverySummary,
  makeOutlineCompletedEvent,
  makePhaseChangedEvent,
  makeReportCompletedEvent,
  makeResearchSessionState,
  makeRevisionSummary,
  makeTaskAwaitingFeedbackEvent,
  makeTaskSnapshot,
  makeWriterDeltaEvent,
  makeWriterReasoningDeltaEvent,
  makeWriterToolCallCompletedEvent,
  makeWriterToolCallRequestedEvent,
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

function createRuntime(taskEventSource: TaskEventSource<EventEnvelope>) {
  return {
    taskApiClient: createFetchTaskApiClient({
      baseUrl: window.location.origin,
      fetchImpl: window.fetch.bind(window),
    }),
    taskEventSource,
  };
}

function createStage6Store(
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
        connectDeadlineAt: "2026-03-16T00:00:30+08:00",
        sseState: "connecting",
        lastHeartbeatAt: null,
        ...overrides.session,
      },
      remote: {
        snapshot: makeTaskSnapshot({
          task_id: "tsk_stage0",
          phase: "preparing_outline",
          status: "running",
          available_actions: [],
        }),
        currentRevision: null,
        delivery: null,
        ...overrides.remote,
      },
    }),
  );
}

async function flushAsyncWork() {
  await Promise.resolve();
  await Promise.resolve();
}

describe("Stage 6 report canvas and delivery flow", () => {
  test("renders outline, report body, writer tool-call states, and refreshes artifact delivery after access_token_invalid", async () => {
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createStage6Store();
    const staleArtifactUrl =
      "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=stale";
    const freshArtifactUrl =
      "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=fresh";
    const staleDelivery = makeDeliverySummary({
      artifacts: [
        {
          artifact_id: "art_stage0_chart",
          filename: "chart_market_share.png",
          mime_type: "image/png",
          url: staleArtifactUrl,
          access_expires_at: "2026-03-16T00:10:00+08:00",
        },
      ],
      markdown_zip_url:
        "/api/v1/tasks/tsk_stage0/downloads/markdown.zip?access_token=zip_stale",
      pdf_url: "/api/v1/tasks/tsk_stage0/downloads/report.pdf?access_token=pdf_stale",
    });
    const refreshedDetail = {
      task_id: "tsk_stage0",
      snapshot: makeTaskSnapshot({
        task_id: "tsk_stage0",
        phase: "delivered",
        status: "running",
        available_actions: [],
      }),
      current_revision: makeRevisionSummary(),
      delivery: makeDeliverySummary({
        artifacts: [
          {
            artifact_id: "art_stage0_chart",
            filename: "chart_market_share.png",
            mime_type: "image/png",
            url: freshArtifactUrl,
            access_expires_at: "2026-03-16T00:20:00+08:00",
          },
        ],
        markdown_zip_url:
          "/api/v1/tasks/tsk_stage0/downloads/markdown.zip?access_token=zip_fresh",
        pdf_url:
          "/api/v1/tasks/tsk_stage0/downloads/report.pdf?access_token=pdf_fresh",
      }),
    };
    let staleArtifactCalls = 0;
    let freshArtifactCalls = 0;
    let taskDetailCalls = 0;

    mswServer.use(
      http.get("*/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart", ({ request }) => {
        const accessToken = new URL(request.url).searchParams.get("access_token");

        if (accessToken === "fresh") {
          freshArtifactCalls += 1;
          return new HttpResponse(new Uint8Array([137, 80, 78, 71]), {
            status: 200,
            headers: {
              "Content-Type": "image/png",
            },
          });
        }

        staleArtifactCalls += 1;
        return HttpResponse.json(
          {
            error: {
              code: "access_token_invalid",
              message: "图片链接已失效。",
              detail: {},
              request_id: "req_artifact_stale",
              trace_id: null,
            },
          },
          { status: 401 },
        );
      }),
      http.get(
        new URL("/api/v1/tasks/tsk_stage0", window.location.origin).toString(),
        () => {
          taskDetailCalls += 1;
          return HttpResponse.json(refreshedDetail, {
            status: 200,
            headers: {
              "x-request-id": "req_stage6_detail",
              "x-trace-id": "trc_stage6_detail",
            },
          });
        },
      ),
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
        makeOutlineCompletedEvent({
          seq: 50,
        }),
      );
      taskEventSource.emit(
        makePhaseChangedEvent({
          seq: 51,
          payload: {
            from_phase: "preparing_outline",
            to_phase: "writing_report",
            status: "running",
          },
        }),
      );
      taskEventSource.emit(
        makeWriterReasoningDeltaEvent({
          seq: 52,
        }),
      );
      taskEventSource.emit(
        makeWriterToolCallRequestedEvent({
          seq: 53,
        }),
      );
      taskEventSource.emit(
        makeWriterDeltaEvent({
          seq: 54,
          payload: {
            delta: "# 执行摘要\n\n报告正文第一段。",
          },
        }),
      );
      taskEventSource.emit(
        makeArtifactReadyEvent({
          seq: 55,
          payload: {
            artifact: staleDelivery.artifacts[0]!,
          },
        }),
      );
      taskEventSource.emit(
        makeWriterToolCallCompletedEvent({
          seq: 56,
        }),
      );
      taskEventSource.emit(
        makeReportCompletedEvent({
          seq: 57,
          payload: {
            delivery: staleDelivery,
          },
        }),
      );
      await flushAsyncWork();
    });

    const reportCanvas = screen.getByRole("region", { name: "报告画布" });
    const timelinePanel = screen.getByRole("region", { name: "时间线" });
    const deliveryPanel = screen.getByRole("region", { name: "交付操作" });

    expect(
      within(reportCanvas).getByText("中国 AI 搜索产品竞争格局研究"),
    ).toBeInTheDocument();
    expect(
      within(reportCanvas).getByRole("heading", { level: 1, name: "执行摘要" }),
    ).toBeInTheDocument();
    expect(within(reportCanvas).getByText("报告正文第一段。")).toBeInTheDocument();
    expect(
      within(reportCanvas).queryByText("先完成市场格局章节，再决定是否需要图表支撑。"),
    ).not.toBeInTheDocument();
    expect(
      within(timelinePanel).getByText("先完成市场格局章节，再决定是否需要图表支撑。"),
    ).toBeInTheDocument();
    expect(within(timelinePanel).getByText("正在生成配图")).toBeInTheDocument();
    expect(within(timelinePanel).getAllByText("已完成").length).toBeGreaterThan(0);
    expect(within(deliveryPanel).getByText("6800 字")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "下载 Markdown Zip" }),
    ).toBeDisabled();
    expect(screen.queryByRole("button", { name: "提交反馈" })).not.toBeInTheDocument();

    await waitFor(() => {
      expect(taskDetailCalls).toBe(1);
      expect(freshArtifactCalls).toBe(1);
    });

    expect(staleArtifactCalls).toBeGreaterThan(0);
    expect(
      await screen.findByAltText("chart_market_share.png"),
    ).toBeInTheDocument();
    expect(store.getState().remote.delivery?.artifacts[0]?.url).toBe(freshArtifactUrl);

    await act(async () => {
      taskEventSource.emit(
        makeTaskAwaitingFeedbackEvent({
          seq: 58,
        }),
      );
      await flushAsyncWork();
    });

    expect(
      screen.getByRole("button", { name: "下载 Markdown Zip" }),
    ).toBeEnabled();
    expect(screen.getByRole("button", { name: "下载 PDF" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "提交反馈" })).not.toBeInTheDocument();
  });
});
