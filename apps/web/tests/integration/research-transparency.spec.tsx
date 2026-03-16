import { act, render, screen, within } from "@testing-library/react";
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
  makeAnalysisCompletedEvent,
  makeAnalysisDeltaEvent,
  makeCollectorCompletedEvent,
  makeCollectorFetchCompletedEvent,
  makeCollectorFetchStartedEvent,
  makeCollectorReasoningDeltaEvent,
  makeCollectorSearchStartedEvent,
  makePlannerReasoningDeltaEvent,
  makePlannerToolCallRequestedEvent,
  makePhaseChangedEvent,
  makeResearchSessionState,
  makeSourcesMergedEvent,
  makeSummaryCompletedEvent,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";

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

function createMockRuntime(taskEventSource: TaskEventSource<EventEnvelope>) {
  const taskApiClient: TaskApiClient = {
    createTask: vi.fn(),
    getTaskDetail: vi.fn(),
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
  };

  return {
    taskApiClient,
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
      connectDeadlineAt: "2026-03-16T00:00:30+08:00",
      sseState: "connecting",
      lastHeartbeatAt: null,
      ...overrides.session,
    },
    remote: {
      snapshot: makeTaskSnapshot({
        task_id: "tsk_stage0",
        status: "running",
        phase: "analyzing_requirement",
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

describe("Stage 5 timeline and transparency", () => {
  const originalScrollIntoView = Element.prototype.scrollIntoView;

  afterEach(() => {
    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      writable: true,
      value: originalScrollIntoView,
    });
    vi.restoreAllMocks();
  });

  test("renders analysis status copy and requirement summary after analysis.completed", async () => {
    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createActiveStore();

    render(
      <ResearchPageClient
        runtime={createMockRuntime(taskEventSource)}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      taskEventSource.emit(makeAnalysisDeltaEvent());
      taskEventSource.emit(makeAnalysisCompletedEvent());
      await flushAsyncWork();
    });

    expect(screen.getByText("正在分析你的研究需求")).toBeInTheDocument();
    expect(screen.getAllByText("需求摘要已生成")).toHaveLength(2);
    expect(
      screen.getByText("分析中国 AI 搜索产品竞争格局"),
    ).toBeInTheDocument();
    expect(screen.queryByText("等待研究透明度事件进入时间线。")).not.toBeInTheDocument();
  });

  test("renders interleaved collection transparency, auto-scrolls to the bottom, and never leaks raw outline delta", async () => {
    const scrollIntoViewSpy = vi.fn();

    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      writable: true,
      value: scrollIntoViewSpy,
    });

    const taskEventSource = new ControlledTaskEventSource<EventEnvelope>();
    const store = createActiveStore();

    render(
      <ResearchPageClient
        runtime={createMockRuntime(taskEventSource)}
        store={store}
      />,
    );

    await act(async () => {
      taskEventSource.open();
      taskEventSource.emit(
        makePhaseChangedEvent({
          seq: 30,
          payload: {
            from_phase: "analyzing_requirement",
            to_phase: "planning_collection",
            status: "running",
          },
        }),
      );
      taskEventSource.emit(makePlannerReasoningDeltaEvent({ seq: 31 }));
      taskEventSource.emit(
        makePlannerToolCallRequestedEvent({
          seq: 32,
          payload: {
            tool_call_id: "call_ai_search",
            collect_target: "收集 AI 搜索厂商",
            additional_info: "优先官方资料。",
          },
        }),
      );
      taskEventSource.emit(
        makePlannerToolCallRequestedEvent({
          seq: 33,
          payload: {
            tool_call_id: "call_revenue",
            collect_target: "收集商业化与收入线索",
            additional_info: "关注 2025 年财报。",
          },
        }),
      );
      taskEventSource.emit(
        makePhaseChangedEvent({
          seq: 34,
          payload: {
            from_phase: "planning_collection",
            to_phase: "collecting",
            status: "running",
          },
        }),
      );
      taskEventSource.emit(
        makeCollectorReasoningDeltaEvent({
          seq: 35,
          payload: {
            subtask_id: "sub_revenue",
            tool_call_id: "call_revenue",
            delta: "先查财报与业绩会。",
          },
        }),
      );
      taskEventSource.emit(
        makeCollectorSearchStartedEvent({
          seq: 36,
          payload: {
            subtask_id: "sub_ai_search",
            tool_call_id: "call_ai_search",
            search_query: "AI 搜索 厂商 2025",
            search_recency_filter: "noLimit",
          },
        }),
      );
      taskEventSource.emit(
        makeCollectorSearchStartedEvent({
          seq: 37,
          payload: {
            subtask_id: "sub_revenue",
            tool_call_id: "call_revenue",
            search_query: "AI 搜索 商业化 收入 2025",
            search_recency_filter: "noLimit",
          },
        }),
      );
      taskEventSource.emit(
        makeCollectorFetchStartedEvent({
          seq: 38,
          payload: {
            subtask_id: "sub_ai_search",
            tool_call_id: "call_ai_search",
            url: "https://example.com/search-ai",
          },
        }),
      );
      taskEventSource.emit(
        makeCollectorFetchCompletedEvent({
          seq: 39,
          payload: {
            subtask_id: "sub_ai_search",
            tool_call_id: "call_ai_search",
            url: "https://example.com/search-ai",
            success: true,
            title: "AI 搜索厂商观察",
          },
        }),
      );
      taskEventSource.emit(
        makeCollectorCompletedEvent({
          seq: 40,
          payload: {
            subtask_id: "sub_ai_search",
            tool_call_id: "call_ai_search",
            status: "completed",
            item_count: 3,
            search_queries: ["AI 搜索 厂商 2025"],
          },
        }),
      );
      taskEventSource.emit(
        makePhaseChangedEvent({
          seq: 41,
          payload: {
            from_phase: "collecting",
            to_phase: "summarizing_collection",
            status: "running",
          },
        }),
      );
      taskEventSource.emit(
        makeSummaryCompletedEvent({
          seq: 42,
          payload: {
            subtask_id: "sub_ai_search",
            tool_call_id: "call_ai_search",
            collect_target: "收集 AI 搜索厂商",
            status: "completed",
            search_queries: ["AI 搜索 厂商 2025"],
            key_findings_markdown: "- 已识别主要玩家与公开产品路线。",
          },
        }),
      );
      taskEventSource.emit(
        makePhaseChangedEvent({
          seq: 43,
          payload: {
            from_phase: "summarizing_collection",
            to_phase: "merging_sources",
            status: "running",
          },
        }),
      );
      taskEventSource.emit(makeSourcesMergedEvent({ seq: 44 }));
      taskEventSource.emit(
        makePhaseChangedEvent({
          seq: 45,
          payload: {
            from_phase: "merging_sources",
            to_phase: "preparing_outline",
            status: "running",
          },
        }),
      );
      taskEventSource.emit({
        seq: 46,
        event: "outline.delta",
        task_id: "tsk_stage0",
        revision_id: "rev_stage0",
        phase: "preparing_outline",
        timestamp: "2026-03-13T14:33:10+08:00",
        payload: {
          delta: '{ "outline": "raw debug delta" }',
        },
      });
      await flushAsyncWork();
    });

    expect(
      screen.getByRole("heading", { name: "正在构思报告结构" }),
    ).toBeInTheDocument();
    expect(screen.getByText("阶段结论已整理")).toBeInTheDocument();
    expect(screen.getByText("来源已去重并整理引用")).toBeInTheDocument();
    expect(screen.queryByText('{ "outline": "raw debug delta" }')).not.toBeInTheDocument();
    expect(scrollIntoViewSpy).toHaveBeenCalled();

    const collectAiItem = screen
      .getByText(
        (_, node) =>
          node instanceof HTMLElement &&
          node.tagName.toLowerCase() === "p" &&
          node.textContent?.includes("搜索： AI 搜索 厂商 2025") === true,
      )
      .closest("li");
    const collectRevenueItem = screen
      .getByText(
        (_, node) =>
          node instanceof HTMLElement &&
          node.tagName.toLowerCase() === "p" &&
          node.textContent?.includes("搜索： AI 搜索 商业化 收入 2025") === true,
      )
      .closest("li");

    expect(collectAiItem).not.toBeNull();
    expect(collectRevenueItem).not.toBeNull();

    const collectAiScope = within(collectAiItem as HTMLElement);
    const collectRevenueScope = within(collectRevenueItem as HTMLElement);
    const collectAiDetail = collectAiScope.getByText(
      (_, node) =>
        node instanceof HTMLElement &&
        node.tagName.toLowerCase() === "p" &&
        node.textContent?.includes("搜索： AI 搜索 厂商 2025") === true,
    );
    const collectRevenueDetail = collectRevenueScope.getByText(
      (_, node) =>
        node instanceof HTMLElement &&
        node.tagName.toLowerCase() === "p" &&
        node.textContent?.includes("搜索： AI 搜索 商业化 收入 2025") === true,
    );

    expect(collectAiScope.getByText("收集 AI 搜索厂商")).toBeInTheDocument();
    expect(collectAiDetail).toHaveTextContent("搜索： AI 搜索 厂商 2025");
    expect(collectAiDetail).toHaveTextContent("读取完成：AI 搜索厂商观察");
    expect(
      collectAiScope.queryByText("AI 搜索 商业化 收入 2025"),
    ).not.toBeInTheDocument();

    expect(
      collectRevenueScope.getByText("收集商业化与收入线索"),
    ).toBeInTheDocument();
    expect(collectRevenueDetail).toHaveTextContent("先查财报与业绩会。");
    expect(collectRevenueDetail).toHaveTextContent(
      "搜索： AI 搜索 商业化 收入 2025",
    );
    expect(
      collectRevenueScope.queryByText("AI 搜索 厂商 2025"),
    ).not.toBeInTheDocument();
  });
});
